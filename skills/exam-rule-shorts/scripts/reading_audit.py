#!/usr/bin/env python3
"""Ask VOICEVOX how it reads each ASCII token and each 行/値 phrase in the narrations (after PRONUNCIATIONS)."""
import json, re, sys, urllib.parse, urllib.request
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
from synthesize import speech_text
B = "http://127.0.0.1:50021"

def kana(text):
    q = json.loads(urllib.request.urlopen(urllib.request.Request(B + "/audio_query?" + urllib.parse.urlencode({"text": text, "speaker": 3}), data=b""), timeout=60).read())
    return "".join("".join(m["text"] for m in ap["moras"]) + ("、" if ap.get("pause_mora") else "") for ap in q["accent_phrases"])

eps = [e for f in sys.argv[1:] for e in json.load(open(f))]
ascii_tok, phrases = {}, {}
for e in eps:
    for s in e["scenes"]:
        sp = speech_text(s["narration"])
        for t in re.findall(r"[A-Za-z][A-Za-z0-9.\-/+]*", sp):
            ascii_tok.setdefault(t, e["id"])
        for m in re.finditer(r"[^、。？]{0,4}[行値][^、。？]{0,3}", sp):
            phrases.setdefault(m.group(0), e["id"])
for t, i in sorted(ascii_tok.items()):
    print("ASCII", t, "→", kana(t), i)
for t, i in sorted(phrases.items()):
    print("KANJI", t, "→", kana(t), i)
