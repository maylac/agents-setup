#!/usr/bin/env python3
"""Lint exam rule-short episodes before audio and rendering (stdlib only).

usage: python3 tools/lint_content.py content/<exam>.json [more.json ...]
Exits non-zero on any error. Limits keep every title on one line, labels on one line,
and narration inside the 4-scene / ~40 s format of the approved SAP pilot.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets" / "icons"
OFFICIAL = re.compile(r"^https://(docs\.aws\.amazon\.com|aws\.amazon\.com|docs\.anthropic\.com|docs\.claude\.com|www\.anthropic\.com|support\.anthropic\.com)/")
BANNED = re.compile(r"正解は[A-E]|選択肢[A-E]|問題文|消去法|[ㄱ-ㆎ가-힣Ѐ-ӿ]")


VAGUE_EDGES = {"連携", "関係", "実行", "観測", "頼る", "使う", "利用", "対応", "判断", "接続先", "答え", "答える", "思い出す", "選ぶ", "関連", "適用"}


def width(text: str) -> float:
    """Full-width characters count 1, ASCII 0.55 (same rule as the renderer)."""
    return sum(1 if ord(ch) > 0xFF else 0.55 for ch in str(text))


def lint(path: Path) -> list[str]:
    errors: list[str] = []
    episodes = json.loads(path.read_text())
    if not isinstance(episodes, list) or not episodes:
        return [f"{path}: must be a non-empty list"]
    seen_ids, seen_titles = set(), set()
    for ep in episodes:
        eid = ep.get("id", "?")
        err = lambda msg, where=eid: errors.append(f"{path.name}:{where}: {msg}")
        if not re.fullmatch(r"[a-z]{3}-r\d{2}", eid):
            err("id must look like 'dva-r01'")
        if eid in seen_ids:
            err("duplicate id")
        seen_ids.add(eid)
        for key in ("exam_code", "exam_label", "series_label", "title"):
            if not ep.get(key):
                err(f"{key} required")
        if ep.get("series_label") != "鉄則":
            err("series_label must be 鉄則")
        if width(ep.get("title", "")) > 18:
            err("episode title > 18 wide chars")
        if ep.get("title") in seen_titles:
            err("duplicate episode title")
        seen_titles.add(ep.get("title"))
        scenes = ep.get("scenes", [])
        kickers = [s.get("kicker") for s in scenes]
        if len(scenes) != 4 or kickers[0] != "場面" or kickers[3] != "確認" or any(width(k or "") > 6 for k in kickers):
            err("4 scenes: 場面, two middle kickers (usually 罠, 鉄則; <= 6 wide), 確認")
            continue
        diagrams = [tuple(sorted(n.get("label", "") for n in sc.get("nodes", []))) for sc in scenes[:3]]
        if len(set(diagrams)) < 3:
            err("scenes 1-3 must each draw a different diagram (situation, wrong design, correct design)")
        if not any(sc.get("rule") for sc in scenes[1:3]):
            err("scene 2 or 3 must state the rule")
        for index, sc in enumerate(scenes):
            where = f"{eid}/s{index + 1}"
            e = lambda msg: err(msg, where)
            if sc.get("id") != f"s{index + 1}":
                e("scene id must be s1..s4")
            for key in ("title", "body", "caption", "narration", "source_url"):
                if not sc.get(key):
                    e(f"{key} required")
            if width(sc.get("title", "")) > 11:
                e(f"title wider than 11 ({sc.get('title')}) - would wrap")
            lines = str(sc.get("body", "")).split("\n")
            if len(lines) > 2 or any(width(line) > 21 for line in lines):
                e("body must be <= 2 lines of <= 21 wide chars")
            narration = sc.get("narration", "")
            if not 45 <= len(narration) <= 95:
                e(f"narration {len(narration)} chars (45-95)")
            if not narration.endswith("のだ。"):
                e("narration must end with 'のだ。' (ずんだもん)")
            if width(sc.get("caption", "")) > 24:
                e("caption > 24 wide chars")
            if not OFFICIAL.match(sc.get("source_url", "")):
                e("source_url must be an official AWS/Anthropic docs URL")
            for key in ("title", "body", "narration", "rule", "wrong"):
                if BANNED.search(str(sc.get(key, ""))):
                    e(f"{key} has exam-tactic wording or a stray script")
            nodes = sc.get("nodes", [])
            if not 2 <= len(nodes) <= 4:
                e("2-4 nodes")
            for ni, node in enumerate(nodes):
                if width(node.get("label", "")) > 8:
                    e(f"node {ni} label wider than 8 ({node.get('label')})")
                if width(node.get("sub", "")) > 12:
                    e(f"node {ni} sub wider than 12 ({node.get('sub')})")
                icons = node.get("icon")
                if not icons:
                    e(f"node {ni} needs an official icon")
                for name in icons if isinstance(icons, list) else [icons] if icons else []:
                    if not (ICONS / f"{name}.svg").exists():
                        e(f"node {ni} icon not in the official package: {name}")
            pairs = set()
            for edge in sc.get("edges", []):
                a, b = edge.get("from"), edge.get("to")
                if not (isinstance(a, int) and isinstance(b, int) and 0 <= a < len(nodes) and 0 <= b < len(nodes) and a != b):
                    e(f"bad edge {edge}")
                if (b, a) in pairs and edge.get("label"):
                    e("label only one direction of a two-way edge")
                pairs.add((a, b))
                if index < 3 and edge.get("label") in VAGUE_EDGES:
                    e(f"edge label '{edge.get('label')}' says nothing; name what flows or happens")
                if width(edge.get("label", "")) > 6:
                    e(f"edge label wider than 6 ({edge.get('label')})")
            if sc["kicker"] == "罠" and not sc.get("wrong"):
                e("罠 scene needs 'wrong'")
            if sc["kicker"] == "確認" and not sc.get("rule"):
                e(f"{sc['kicker']} scene needs 'rule'")
            for key in ("rule", "wrong"):
                if sc.get(key) and width(sc[key]) > 40:
                    e(f"{key} wider than 40")
    return errors


if __name__ == "__main__":
    problems = [msg for arg in sys.argv[1:] for msg in lint(Path(arg))]
    print("\n".join(problems) if problems else "content ok")
    sys.exit(1 if problems else 0)
