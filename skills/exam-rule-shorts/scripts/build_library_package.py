#!/usr/bin/env python3
"""Build the video-library overlay and the Vantik rule-shorts manifest (stdlib + bundled ffmpeg).

usage: python3 tools/build_library_package.py --live-catalog evidence/live-catalog.json
Writes package/dist/{media,posters,captions}/<sha256>.<ext>, package/dist/catalog.json
(live entries kept byte-for-byte as JSON objects, one new collection per exam in front),
package/asset-manifest.json and package/rule-shorts-manifest.json (for vantik-content).
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FFMPEG = os.path.realpath(ROOT / "production/node_modules/ffmpeg-static/ffmpeg")
ORIGIN = os.environ["VIDEO_LIBRARY_ORIGIN"]  # private HTTPS origin of the video library
STAMP = os.environ.get("RULE_SHORTS_STAMP", datetime.now().strftime("%Y%m%d"))
JST = timezone(timedelta(hours=9))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def vtt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def duration(path: Path) -> float:
    out = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True).stderr
    hms = out.split("Duration: ", 1)[1].split(",", 1)[0]
    h, m, s = hms.split(":")
    return round(int(h) * 3600 + int(m) * 60 + float(s), 3)


def place(src: Path, kind: str, ext: str, dist: Path, manifest: list) -> str:
    digest = sha256(src)
    rel = f"{kind}/{digest}.{ext}"
    target = dist / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copyfile(src, target)
    manifest.append({"path": rel, "sha256": digest, "bytes": target.stat().st_size, "source": str(src)})
    return rel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-catalog", type=Path, required=True)
    args = parser.parse_args()
    live_raw = args.live_catalog.read_text(encoding="utf-8")
    live = json.loads(live_raw)
    episodes = json.loads((ROOT / "content/episodes.json").read_text())
    timed = {ep["id"]: ep for ep in json.loads((ROOT / "audio/episodes-timed.json").read_text())}
    package = ROOT / "package"
    shutil.rmtree(package, ignore_errors=True)
    dist = package / "dist"
    assets: list = []
    collections: dict[str, dict] = {}
    videos: list = []
    completed = datetime.now(JST).isoformat(timespec="seconds")
    with tempfile.TemporaryDirectory() as tmp:
        for ep in episodes:
            exam_code, label = ep["exam_code"], ep["exam_label"]
            collection_id = f"{exam_code}-rules-{STAMP}"
            count = sum(1 for e in episodes if e["exam_code"] == exam_code)
            collections.setdefault(collection_id, {
                "id": collection_id, "title": f"{label.removeprefix('AWS ')} 鉄則ショート", "exam": label,
                "completed_at": completed,
                "source_note": f"Vantik資料と公式ドキュメントに基づく鉄則{count}本",
            })
            mp4 = ROOT / "videos" / f"{ep['id']}.mp4"
            total = duration(mp4)
            # Captions: scene offsets + the synthesizer's timed chunks.
            starts, offset = [], 0.0
            cues = ["WEBVTT", ""]
            for scene in timed[ep["id"]]["scenes"]:
                starts.append(offset)
                for chunk in scene.get("caption_chunks", []):
                    cues += [f"{vtt_time(offset + chunk['start'])} --> {vtt_time(offset + chunk['end'])}", chunk["text"], ""]
                offset += scene["duration"]
            vtt = Path(tmp) / f"{ep['id']}.vtt"
            vtt.write_text("\n".join(cues), encoding="utf-8")
            # Poster: the rule scene with its diagram drawn.
            poster = Path(tmp) / f"{ep['id']}.jpg"
            subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{starts[2] + 6:.2f}", "-i", str(mp4), "-frames:v", "1",
                            "-vf", "scale=540:-2", "-q:v", "4", str(poster)], check=True)
            sources, seen = [], set()
            for scene in ep["scenes"]:
                if scene["source_url"] not in seen:
                    seen.add(scene["source_url"])
                    sources.append({"title": "公式ドキュメント", "url": scene["source_url"]})
            videos.append({
                "id": f"rules-{ep['id']}", "collection_id": collection_id, "title": ep["title"],
                "question_number": None, "kind": "clip", "duration_seconds": total,
                "src": place(mp4, "media", "mp4", dist, assets),
                "poster": place(poster, "posters", "jpg", dist, assets),
                "subtitle": place(vtt, "captions", "vtt", dist, assets),
                "notes": [], "sources": sources,
                "chapters": [{"start_seconds": round(start, 3), "title": f"{scene['kicker']}：{scene['title']}"}
                             for start, scene in zip(starts, ep["scenes"])],
                "question_ids": [], "exam_codes": [exam_code],
            })
    new_ids = {v["id"] for v in videos} | set(collections)
    clash = new_ids & ({v["id"] for v in live["videos"]} | {c["id"] for c in live["collections"]})
    if clash:
        raise SystemExit(f"id clash with live catalog: {sorted(clash)[:5]}")
    catalog = {**live, "collections": list(collections.values()) + live["collections"], "videos": videos + live["videos"]}
    (dist / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    (package / "asset-manifest.json").write_text(json.dumps(assets, ensure_ascii=False, indent=1), encoding="utf-8")
    absolute = lambda rel: f"{ORIGIN}/{rel}"
    vantik = {
        "version": 1, "trusted_origin": ORIGIN, "collections": list(collections.values()),
        "videos": [{**v, "src": absolute(v["src"]), "poster": absolute(v["poster"]), "subtitle": absolute(v["subtitle"])} for v in videos],
    }
    (package / "rule-shorts-manifest.json").write_text(json.dumps(vantik, ensure_ascii=False, indent=1), encoding="utf-8")
    receipt = {
        "live_catalog_sha256": hashlib.sha256(live_raw.encode()).hexdigest(),
        "catalog_sha256": sha256(dist / "catalog.json"), "new_collections": len(collections), "new_videos": len(videos),
        "assets": len({a["path"] for a in assets}), "bytes": sum({a["path"]: a["bytes"] for a in assets}.values()),
        "live_entries_preserved": len(live["videos"]),
    }
    (package / "receipt.json").write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
