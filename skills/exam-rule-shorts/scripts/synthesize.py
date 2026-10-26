#!/usr/bin/env python3
"""Synthesize episode narration with a local VOICEVOX engine (stdlib only)."""
from __future__ import annotations

import argparse
import array
import copy
import hashlib
import json
import math
import re
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "audio"
BASE_URL = "http://127.0.0.1:50021"
RATE = 48000
FPS = 30
SETTINGS = {"speedScale": 1.14, "pitchScale": 0.0, "intonationScale": 1.0,
            "volumeScale": 1.0, "prePhonemeLength": 0.08, "postPhonemeLength": 0.12}
# Keep these as speech-only substitutions; captions and source narration stay verbatim.
PRONUNCIATIONS = [("aws:SourceVpce", "エーダブリューエス、ソース、ブイピーシーイー"),
                  ("aws:sourceVpce", "エーダブリューエス、ソース、ブイピーシーイー"),
                  ("aws:RequestedRegion", "エーダブリューエス、リクエステッドリージョン"),
                  ("AWS:RequestedRegion", "エーダブリューエス、リクエステッドリージョン"),
                  ("SourceVpce", "ソース、ブイピーシーイー"),
                  ("IAM Identity Center", "アイアム、アイデンティティセンター"),
                  ("AWS Organizations", "エーダブリューエス、オーガニゼーションズ"),
                  ("Transit Gateway", "トランジット、ゲートウェイ"),
                  ("RDS Proxy", "アールディーエス、プロキシ"),
                  ("Route 53", "ルート、フィフティースリー"),
                  ("Route53", "ルート、フィフティースリー"),
                  ("CloudFront", "クラウドフロント"),
                  ("PrivateLink", "プライベートリンク"),
                  ("API Gateway", "エーピーアイ、ゲートウェイ"),
                  ("OAuth", "オーオース"), ("OIDC", "オーアイディーシー"),
                  ("JWT", "ジェイダブリューティー"), ("ECR", "イーシーアール"),
                  ("FSx", "エフエスエックス"), ("NAT", "ナット"),
                  ("Lambda", "ラムダ"), ("ap-northeast-1", "エーピー、ノースイースト、ワン"),
                  ("s3:DataAccessPointArn", "エススリー、データアクセスポイント、エーアールエヌ"),
                  ("S3:DataAccessPointArn", "エススリー、データアクセスポイント、エーアールエヌ"),
                  ("DataAccessPointArn", "データアクセスポイント、エーアールエヌ"),
                  ("AWS", "エーダブリューエス"), ("EC2", "イーシーツー"),
                  ("S3", "エススリー"), ("IAM", "アイアム"), ("DAX", "ダックス"),
                  ("SCP", "エスシーピー"), ("VPC", "ブイピーシー"),
                  ("RDS", "アールディーエス"), ("KMS", "ケーエムエス"),
                  ("EBS", "イービーエス"), ("EFS", "イーエフエス"),
                  ("SQS", "エスキューエス"), ("SNS", "エスエヌエス"),
                  ("API", "エーピーアイ"), ("CLI", "シーエルアイ"),
                  ("AZ", "エーゼット")]


def request(path: str, data: bytes | None = None, content_type: str | None = None):
    headers = {"Content-Type": content_type} if content_type else {}
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def speaker():
    catalog = json.loads(request("/speakers"))
    for character in catalog:
        if character.get("name") == "ずんだもん":
            for style in character.get("styles", []):
                if style.get("name") == "ノーマル":
                    return character, style
    raise RuntimeError("VOICEVOX speaker ずんだもん / ノーマル not found")


def speech_text(text: str) -> str:
    for src, dst in PRONUNCIATIONS:
        text = text.replace(src, dst)
    return text


def make_caption_chunks(text: str, speech_duration: float) -> list[dict]:
    """Split at sentence/comma boundaries, cap length, and estimate times by text length."""
    sentences = [part for part in re.findall(r"[^。！？!?]+[。！？!?]*", text) if part]
    if not sentences and text:
        sentences = [text]
    parts = []
    for sentence in sentences:
        remaining = sentence
        while len(remaining) > 32:
            comma = remaining.rfind("、", 0, 32)
            cut = comma + 1 if comma >= 0 else 32
            parts.append(remaining[:cut])
            remaining = remaining[cut:]
        if remaining:
            parts.append(remaining)
    weights = [max(1, len(part.strip())) for part in parts]
    total = sum(weights) or 1
    chunks = []
    cursor = 0.0
    for index, (part, weight) in enumerate(zip(parts, weights)):
        end = speech_duration if index == len(parts) - 1 else cursor + speech_duration * weight / total
        chunks.append({"text": part, "start": round(cursor, 3), "end": round(end, 3)})
        cursor = end
    return chunks


def wav_data(blob: bytes):
    import io
    with wave.open(io.BytesIO(blob), "rb") as w:
        if w.getsampwidth() != 2 or w.getcomptype() != "NONE":
            raise ValueError("Expected uncompressed 16-bit PCM from VOICEVOX")
        return w.getframerate(), w.getnchannels(), array.array("h", w.readframes(w.getnframes()))


def convert_and_pad(blob: bytes) -> tuple[bytes, float, dict]:
    source_rate, channels, samples = wav_data(blob)
    if channels < 1:
        raise ValueError("VOICEVOX returned audio with no channels")
    frames = len(samples) // channels
    mono = []
    for i in range(frames):
        mono.append(sum(samples[i * channels:(i + 1) * channels]) / channels)
    # Linear resampling is sufficient for voice and avoids third-party dependencies.
    out_frames = max(1, round(frames * RATE / source_rate))
    resampled = []
    for j in range(out_frames):
        pos = j * source_rate / RATE
        lo = min(int(pos), frames - 1)
        hi = min(lo + 1, frames - 1)
        frac = pos - lo
        resampled.append(mono[lo] * (1 - frac) + mono[hi] * frac)
    rms = math.sqrt(sum(x * x for x in resampled) / len(resampled))
    gain = min(0.92 * 32767 / max((abs(x) for x in resampled), default=1),
               (32767 * 10 ** (-20 / 20)) / max(rms, 1))
    normalized = [max(-32768, min(32767, round(x * gain))) for x in resampled]
    # Pad to at least 300 ms and round up to an exact video frame boundary.
    target = math.ceil((out_frames / RATE + 0.30) * FPS) / FPS
    target_frames = math.ceil(target * RATE)
    final = array.array("h")
    for value in normalized:
        final.extend((value, value))
    final.extend([0] * ((target_frames - out_frames) * 2))
    import io
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(final.tobytes())
    actual = target_frames / RATE
    return buffer.getvalue(), actual, {"source_sample_rate": source_rate, "source_channels": channels,
                                        "source_duration_seconds": frames / source_rate,
                                        "rms_dbfs_before_normalization": round(20 * math.log10(max(rms, 1) / 32768), 2),
                                        "normalization_gain": round(gain, 4)}


def main():
    global BASE_URL
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "content" / "episodes.json")
    parser.add_argument("--timed-output", type=Path, default=OUT / "episodes-timed.json",
                        help="write the timing-enriched input here (supports immutable per-batch snapshots)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--episode", help="synthesize one episode id")
    group.add_argument("--all", action="store_true", help="synthesize every episode")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    BASE_URL = args.base_url.rstrip("/")
    if not args.input.exists():
        raise SystemExit(f"Episode input does not exist: {args.input}")
    source = json.loads(args.input.read_text(encoding="utf-8"))
    episodes = source.get("episodes") if isinstance(source, dict) else source
    if not isinstance(episodes, list):
        raise SystemExit("Input must be an episode list or an object with an 'episodes' list")
    char, style = speaker()
    selected = episodes if args.all else [e for e in episodes if e.get("id") == args.episode]
    if not selected:
        raise SystemExit(f"No episode found for id {args.episode!r}")
    OUT.mkdir(parents=True, exist_ok=True)
    prior_path = OUT / "metadata.json"
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else {}
    metadata = prior
    for episode in selected:
        eid = str(episode["id"])
        scene_meta = metadata.get(eid, {})
        for scene in episode.get("scenes", []):
            sid = str(scene["id"])
            original = scene["narration"]
            spoken = speech_text(original)
            digest = hashlib.sha256(original.encode()).hexdigest()
            settings_key = hashlib.sha256(json.dumps({"text": spoken, "original": original, **SETTINGS, "speaker": style["id"]},
                                                      sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            path = OUT / f"{eid}-{sid}.wav"
            cached = scene_meta.get(sid, {})
            if path.exists() and cached.get("settings_hash") == settings_key:
                try:
                    with wave.open(str(path), "rb") as w:
                        if w.getframerate() == RATE and w.getnchannels() == 2 and w.getsampwidth() == 2:
                            duration = w.getnframes() / w.getframerate()
                        else:
                            duration = 0
                except wave.Error:
                    duration = 0
            else:
                duration = 0
            if not duration:
                query = json.loads(request("/audio_query?" + urllib.parse.urlencode(
                    {"text": spoken, "speaker": style["id"]}), data=b"", content_type="application/json"))
                query.update(SETTINGS)
                query_blob = json.dumps(query, ensure_ascii=False).encode()
                pcm = request("/synthesis?" + urllib.parse.urlencode({"speaker": style["id"]}),
                              data=query_blob, content_type="application/json")
                final, duration, levels = convert_and_pad(pcm)
                path.write_bytes(final)
                (OUT / f"{eid}-{sid}.audio_query.json").write_bytes(query_blob)
                scene_meta[sid] = {"audio_path": str(path), "duration_seconds": duration,
                                   "narration_sha256": digest, "settings_hash": settings_key,
                                   "text": original, "spoken_text": spoken, "speaker_name": char["name"],
                                   "speaker_style": style["name"], "speaker_id": style["id"],
                                   "speaker_uuid": char.get("speaker_uuid"), "settings": SETTINGS, **levels}
                print(f"created {path} ({duration:.3f}s)")
            else:
                scene_meta[sid]["duration_seconds"] = duration
                print(f"cached  {path} ({duration:.3f}s)")
            scene["audio_path"] = str(path)
            scene["duration_seconds"] = duration
            scene["duration"] = duration
            speech_duration = scene_meta.get(sid, {}).get("source_duration_seconds", max(0.01, duration - 0.30))
            scene["caption_chunks"] = make_caption_chunks(original, speech_duration)
            scene["caption_timing_basis"] = "estimated_proportional_to_original_text_length_within_voicevox_speech_duration"
        metadata[eid] = scene_meta
    (OUT / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    output = copy.deepcopy(source)
    if isinstance(output, dict):
        output["episodes"] = episodes
    else:
        output = episodes
    args.timed_output.parent.mkdir(parents=True, exist_ok=True)
    args.timed_output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
