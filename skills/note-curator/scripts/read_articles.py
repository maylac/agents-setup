#!/usr/bin/env python3
"""Extract readable text from note.com articles. Usage: read_articles.py <key1> [key2 ...]"""
from __future__ import annotations
import html, json, re, sys, urllib.request
from html.parser import HTMLParser

keys = sys.argv[1:] or ["n541b81e07619"]
headers = {"User-Agent": "Mozilla/5.0 (compatible; myLife-note-curator/1.0)"}

class TextExtractor(HTMLParser):
    block_tags = {"p", "li", "h1", "h2", "h3", "h4", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self.parts = []
        self.buffer = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg", "figure", "iframe"}:
            self.skip += 1
        if tag == "br" and self.skip == 0:
            self.buffer.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg", "figure", "iframe"} and self.skip:
            self.skip -= 1
        if tag in self.block_tags and self.skip == 0:
            text = re.sub(r"\s+", " ", "".join(self.buffer)).strip()
            self.buffer = []
            if text:
                self.parts.append(html.unescape(text))

    def handle_data(self, data):
        if self.skip == 0:
            self.buffer.append(data)

    def close(self):
        super().close()
        text = re.sub(r"\s+", " ", "".join(self.buffer)).strip()
        if text:
            self.parts.append(html.unescape(text))

for key in keys:
    url = f"https://note.com/api/v3/notes/{key}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.load(response)["data"]

    parser = TextExtractor()
    parser.feed(data.get("body") or "")
    parser.close()

    parts = []
    seen = set()
    for part in parser.parts:
        if part in seen or len(part) < 20:
            continue
        if "pic.twitter" in part or "https://t.co" in part:
            continue
        seen.add(part)
        parts.append(part)

    print(f"\n=== {data.get('name')} ===")
    print(f"URL: https://note.com/{data.get('user', {}).get('urlname', '')}/n/{key}")
    print(f"chars={sum(len(part) for part in parts)}")
    for index, part in enumerate(parts[:18], 1):
        print(f"{index:02d}. {part[:240]}")
