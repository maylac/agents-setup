#!/usr/bin/env python3
"""Mirror of reskilling-os server/services/reviewVideoCatalog.ts checks: any failure makes Vantik reject the WHOLE catalog."""
import collections, json, re, sys
m = json.load(open(sys.argv[1]))
origin = m["trusted_origin"].rstrip("/") + "/"
errs = []
cids = [c["id"] for c in m["collections"]]
errs += [f"duplicate collection {k}" for k, n in collections.Counter(cids).items() if n > 1]
errs += [f"collection without title {c['id']}" for c in m["collections"] if not c.get("title")]
errs += [f"duplicate video {k}" for k, n in collections.Counter(v["id"] for v in m["videos"]).items() if n > 1]
for v in m["videos"]:
    w = v.get("id")
    if v.get("collection_id") not in cids or not v.get("title"): errs.append(f"{w}: collection/title")
    if v.get("kind") not in ("clip", "full") or not (isinstance(v.get("duration_seconds"), (int, float)) and v["duration_seconds"] > 0): errs.append(f"{w}: kind/duration")
    for k in ("src", "poster") + (("subtitle",) if v.get("subtitle") is not None else ()):
        u = v.get(k, "")
        if not u.startswith(origin) or re.search(r"[\s%\\?#]", u): errs.append(f"{w}: {k} {u}")
    for s in v.get("sources", []):
        if not s.get("title") or not s.get("url", "").startswith("https://") or re.search(r"[\s\x00-\x1f]", s["url"]): errs.append(f"{w}: source {s}")
    for c in v.get("chapters", []):
        if not c.get("title") or not isinstance(c.get("start_seconds"), (int, float)) or c["start_seconds"] < 0: errs.append(f"{w}: chapter")
    for k in ("question_ids", "exam_codes"):
        if not all(isinstance(x, str) and x for x in v.get(k, [])): errs.append(f"{w}: {k}")
print("\n".join(errs) if errs else f"manifest ok ({len(m['videos'])} videos)")
sys.exit(1 if errs else 0)
