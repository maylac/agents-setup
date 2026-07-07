#!/usr/bin/env python3
"""Scan a note.com creator's catalog metadata. Usage: scan_creator.py <creator_slug>"""
from __future__ import annotations
import html, json, re, sys, time, urllib.request
from collections import Counter

creator = sys.argv[1] if len(sys.argv) > 1 else "yusuke_motoyama"
headers = {"User-Agent": "Mozilla/5.0 (compatible; myLife-note-curator/1.0)"}
rows = []
page = 1

while True:
    url = f"https://note.com/api/v2/creators/{creator}/contents?kind=note&page={page}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.load(response)

    for item in data["data"]["contents"]:
        tags = []
        for tag in item.get("hashtags") or []:
            name = ((tag or {}).get("hashtag") or {}).get("name") or ""
            if name:
                tags.append(name.lstrip("#"))

        body = item.get("body") or item.get("description") or ""
        body = re.sub(r"<[^>]+>", " ", body)
        preview = html.unescape(re.sub(r"\s+", " ", body)).strip()[:180]

        rows.append({
            "title": item.get("name") or "",
            "key": item.get("key") or "",
            "url": item.get("noteUrl") or f"https://note.com/{creator}/n/{item.get('key')}",
            "date": (item.get("publishAt") or "")[:10],
            "like": item.get("likeCount") or 0,
            "comments": item.get("commentCount") or 0,
            "is_limited": bool(item.get("isLimited")),
            "is_membership": bool(item.get("isMembershipConnected")),
            "tags": tags,
            "preview": preview,
        })

    if data["data"].get("isLastPage"):
        break
    page += 1
    time.sleep(0.05)

print("TOTAL", len(rows), "PAGES", page)
if rows:
    dates = [row["date"] for row in rows if row["date"]]
    print("DATE_RANGE", min(dates), max(dates))
    print("LIMITED_COUNTS", Counter(row["is_limited"] for row in rows))
    print("TAG_TOP")
    for tag, count in Counter(tag for row in rows for tag in row["tags"]).most_common(25):
        print(f"- {tag}: {count}")

    print("\nTOP_BY_LIKES")
    for index, row in enumerate(sorted(rows, key=lambda row: row["like"], reverse=True)[:40], 1):
        scope = "limited" if row["is_limited"] else "open"
        print(f"{index:02d}. {row['like']:4d} | {row['date']} | {scope} | {row['title']} | {row['url']} | tags={','.join(row['tags'][:4])}")

    print("\nRECENT")
    for index, row in enumerate(sorted(rows, key=lambda row: row["date"], reverse=True)[:30], 1):
        scope = "limited" if row["is_limited"] else "open"
        print(f"{index:02d}. {row['date']} | {row['like']:4d} | {scope} | {row['title']} | {row['url']} | tags={','.join(row['tags'][:4])}")
