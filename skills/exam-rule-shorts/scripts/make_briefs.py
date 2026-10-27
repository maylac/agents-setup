#!/usr/bin/env python3
"""Write per-exam briefs for the coverage batch: write / audit / fix / diagram / term-audit."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VC = Path.home() / "workspace/maylac/vantik-content"
OLD = Path.home() / "tasks/rule-shorts-20261026/content/episodes.json"
AWS = "aws-sap-c02 aws-soa-c03 aws-scs-c03 aws-mla-c01 aws-dva-c02 aws-dop-c02 aws-dea-c01 aws-ans-c01 aws-aip-c01".split()
CLAUDE = {  # exam: (label, id prefix, episodes per domain id)
    "ccao-f": ("CCAO-F", "cao", {f"d{i}": 2 for i in range(1, 8)}),
    "ccar-f": ("CCAR-F", "caf", {"d1": 4, "d2": 3, "d3": 3, "d4": 3, "d5": 2}),
    "ccar-p": ("CCAR-P", "cap", {f"d{i}": 2 for i in range(1, 9)}),
    "ccdv-f": ("CCDV-F", "cdv", {f"d{i}": 2 for i in range(1, 9)}),
}
GUIDE_GLOB = {"aws-dva-c02": "dva-c02-*.html", "aws-sap-c02": "aws-sap-c02-*.html"}

old = json.loads(OLD.read_text())


def guides(ex):
    files = sorted((VC / "exam_guides").glob(GUIDE_GLOB.get(ex, f"{ex}-*.html")))
    manual = [f for f in files if f.name.endswith("field-manual.html")]
    return ", ".join(str(f) for f in manual + [f for f in files if f not in manual])


def task_lines(fc):
    return "\n".join(
        f"  - {t['id']} {t['name']}  (domain {d['id']} {d['name']}, weight {d.get('weight')})"
        for d in fc["domains"] for t in d["tasks"]
    )


def main():
    (ROOT / "evidence/existing").mkdir(parents=True, exist_ok=True)
    for ex in AWS + list(CLAUDE):
        fc_path = VC / "flashcards" / f"{ex}.json"
        fc = json.loads(fc_path.read_text())
        g = guides(ex)
        claude = ex in CLAUDE
        mine = [e for e in old if e["exam_code"] == ex]
        if claude:
            label, prefix, quota = CLAUDE[ex]
            start = 1
            count = sum(quota.values())
            plan = "\n".join(f"  - domain {d}: {n} episodes" for d, n in quota.items())
            scope = (
                f"Write {count} episodes that together cover the WHOLE exam scope. Official domains/tasks:\n{task_lines(fc)}\n"
                f"Episodes per domain (exact):\n{plan}\n"
                "Within a domain, pick different high-value decision rules (different skills in the flashcards), never two on the same rule."
            )
            icons = ("Icons: Claude certifications have NO official icon set. Use ONLY neutral general icons listed in assets/GENERAL_ICONS.txt "
                     "whose name does not contain 'AWS' (e.g. Res_User_48_Light, Res_Users_48_Light, Res_Chat_48_Light, Res_Document_48_Light, "
                     "Res_Documents_48_Light, Res_Gear_48_Light, Res_Toolkit_48_Light, Res_Source-Code_48_Light, Res_JSON-Script_48_Light, "
                     "Res_Server_48_Light, Res_Database_48_Light, Res_Magnifying-Glass_48_Light, Res_Shield_48_Light, Res_Logs_48_Light, "
                     "Res_Metrics_48_Light, Res_Question_48_Light, Res_Generic-Application_48_Light). Never an AWS service icon. "
                     "Pick the general icon that best depicts the node (model/agent → Res_Generic-Application_48_Light or Res_Chat_48_Light, tool → Res_Toolkit_48_Light, prompt → Res_Document_48_Light, MCP server → Res_Server_48_Light).")
            names = "speak product and feature names (Claude, Claude Code, MCP, Agent SDK, tool_use …) as written"
        else:
            label = mine[0]["exam_label"]
            prefix = mine[0]["id"].split("-")[0]
            start = max(int(e["id"].split("-r")[1]) for e in mine) + 1
            existing = ROOT / "evidence/existing" / f"{ex}.json"
            existing.write_text(json.dumps([
                {"id": e["id"], "title": e["title"],
                 "rule": next((s.get("rule") for s in e["scenes"] if s.get("kicker") == "鉄則"), None) or e["scenes"][2].get("rule"),
                 "situation": e["scenes"][0]["body"]} for e in mine], ensure_ascii=False, indent=1))
            scope = (
                f"Goal is that the exam's WHOLE scope is covered: every official task below must be the main subject of at least one episode.\n"
                f"Official tasks:\n{task_lines(fc)}\n"
                f"{len(mine)} episodes already exist (published; read-only): {existing} (id, title, rule, situation).\n"
                "Step 1: decide which task each existing episode's main rule belongs to (the task under which that decision is tested). "
                "Step 2: for EVERY task that no existing episode covers, write exactly ONE new episode teaching that task's single most-tested decision rule. "
                "Do not duplicate any existing episode's rule. Do not write episodes for tasks that are already covered.\n"
                "Step 3: write evidence/coverage-" + ex + '.json: {"existing": {"<id>": "<task id>", ...}, "new": {"<id>": "<task id>", ...}} listing ALL existing and new episodes.'
            )
            icons = ("icon: EVERY node needs one official AWS icon name from assets/ICON_INDEX.txt (file name without .svg). Use the specific service icon (Arch_*_64) or resource icon (Res_*_48) only when the node IS that service/resource; "
                     "generic actors/concepts use a general icon from assets/GENERAL_ICONS.txt (Res_Users_48_Light, Res_Question_48_Light, Res_Document_48_Light, Res_Data-Table_48_Light, Res_Gear_48_Light, Res_Metrics_48_Light …).")
            names = "speak AWS service names as written"
        idnote = f' (numbering starts at {prefix}-r{start:02d}; ids must match [a-z]{{3}}-r[0-9]{{2}})'
        owned = f"content/{ex}.json" + ("" if claude else f" and evidence/coverage-{ex}.json")
        write = f"""Goal: write Japanese vertical "鉄則ショート" episodes for certification exam {ex} ({label}) into content/{ex}.json (a JSON list). Each episode teaches ONE exam decision rule (how to choose the right answer for a requirement) in 4 scenes (~40 s, VOICEVOX ずんだもん narration). The user approved the style of content/pilot.json (3 SAP episodes) — copy its structure, tone and density exactly.

You own ONLY {owned}. Other workers concurrently write other files; do not touch anything else.

Sources (read-only; use nothing else for facts):
- Field manual: {g}
- Audited flashcards (with official source_url per card; domains and tasks listed at the top): {fc_path}
Every claim must be stated in those sources; each scene's source_url must be an official URL taken from them (flashcard source_url or a URL cited in the guide) that supports that scene. Do not invent numbers, limits or dates. No copyrighted exam question stems, no answer letters, no exam-taking tactics (消去法 etc.) — knowledge and decision rules only.

Scope:
{scope}

Episode schema (see content/pilot.json):
- id "{prefix}-rNN"{idnote}, exam_code "{ex}", exam_label "{label}", series_label "鉄則", "task": "<official task id it covers>", title (<=18 wide chars).
- scenes s1..s4 with kickers: s1 "場面" (the requirement/condition that triggers the rule), s2 usually "罠" (tempting wrong design; set "wrong" and "wrong_tag":"✕ 罠") or a contrast kicker, s3 usually "鉄則" (correct choice; "rule" + "rule_tag":"✓ 鉄則"), s4 "確認" (one recall question; title is the question, narration asks then answers; "rule" = answer, "rule_tag":"✓ 答え").
- Each scene: title (one line, <= 11 wide chars), body (2 lines joined by "\\n", each <= 21 wide), caption (<= 24), narration (45-95 chars, natural spoken Japanese, ends with "のだ。"; ずんだもん voice, {names}), nodes 2-4 {{label <= 8 wide, sub <= 12 wide, icon}}, edges [{{from,to,label<=6}}] (two-way: label only one direction), source_url.
- Diagrams: s1 the situation, s2 the tempting wrong design itself, s3 the correct flow (3 nodes when 3 components), s4 問い (Res_Question_48_Light) → 答え. s1-s3 must be three different diagrams; edge labels name what flows or happens (never 連携/関係/実行/使う/対応).
- Width rule: full-width char = 1, ASCII = 0.55. Rewrite to fit; never truncate words.
- {icons}
- Japanese terminology: use the vendor's official Japanese documentation terms (AWS account = アカウント, never 口座; キー not 鍵; メトリクス not 指標; しきい値; スタンバイ; 呼び出し). Keep official product/feature names.

Acceptance (run it, fix until it passes): python3 tools/lint_content.py content/{ex}.json  → prints "content ok".
Reply in <= 15 lines: the episode ids with title and task, and any claim you were unsure about (with its source_url)."""
        (ROOT / f"briefs/write-{ex}.txt").write_text(write)
        vendor_icon = ("(3) a node icon that is not a neutral general icon or does not depict the node (Claude exams must not use AWS icons)"
                       if claude else "(3) a node icon that names a different service than its label (icon = official AWS file name), or a service icon on a generic box")
        audit = f"""Read-only fact audit of content/{ex}.json (Japanese exam "rule" short-video scripts for {label}; schema: episodes[].scenes[] with title, body, narration, rule, wrong, nodes[{{label,sub,icon}}], source_url; each episode has "task").
Sources the scripts were required to use: {g} and {fc_path} (each card has an official source_url).
Check every scene for: (1) a factual claim that is wrong or not supported by those sources / its source_url; (2) a "wrong" (罠) that is actually a valid answer, or a "rule" that is not the best answer or drops a boundary condition; {vendor_icon}; (4) misleading simplification a learner would carry into the exam; (5) an episode whose "task" does not match its rule.
Output ONLY a JSON array (no prose) of defects: [{{"where":"<id>/s<n>","field":"narration|rule|wrong|title|body|node<i>|source_url|task","problem":"...","fix":"concrete replacement text or icon name"}}]. Empty array if none. Be strict but do not flag style."""
        (ROOT / f"briefs/audit-{ex}.txt").write_text(audit)
        fix_icons = ("Icons: only neutral general icons from assets/GENERAL_ICONS.txt without 'AWS' in the name; never AWS service icons." if claude else
                     "Icons: a node gets a service/resource icon ONLY when its label/sub names that AWS service or resource (names in assets/ICON_INDEX.txt); generic concepts use a general icon from assets/GENERAL_ICONS.txt. Apply this to the WHOLE file.")
        fix = f"""Goal: fix content/{ex}.json using the independent audit in {{AUDIT}} (JSON list of defects: where "<id>/s<n>", field, problem, fix; node indexes are 0-based).
You own ONLY content/{ex}.json. Sources (only these): {g} and {fc_path}.
Rules:
1. Resolve every defect. Use the suggested fix when the sources support it; otherwise write a correction the sources do support. A "wrong" (罠) must be a design that is actually wrong for the stated condition; a "rule" must be the best answer and keep its boundary conditions.
2. {fix_icons}
3. Keep all ids, "task" fields (unless a defect says the task is wrong), scene count and the style of content/pilot.json; narration still ends 「のだ。」.
Acceptance: python3 tools/lint_content.py content/{ex}.json → "content ok". Reply in <= 10 lines: defects fixed, any defect you rejected and why."""
        (ROOT / f"briefs/fix-{ex}.txt").write_text(fix)
        diag = (ROOT / "briefs/diagram-template.txt").read_text().replace("{EXAM}", ex).replace("{AUDIT}", "")
        if claude:
            diag = diag.replace("- Icons: service/resource icons only for nodes that are that AWS service/resource; generic actors/concepts use general icons from assets/GENERAL_ICONS.txt. Use the most specific official icon (assets/ICON_INDEX.txt).",
                                "- Icons: Claude exams use ONLY neutral general icons from assets/GENERAL_ICONS.txt without 'AWS' in the name; never AWS service icons.")
            diag = diag.replace("(e.g. アプリ → DAX → DynamoDB with \"読み取り\", \"キャッシュミス時\")", "(e.g. アプリ → Claude → ツール with \"tool_use\", \"結果を返す\")")
        (ROOT / f"briefs/diagram-{ex}.txt").write_text(diag)
        if claude:
            term = f"""Read-only Japanese terminology and translation audit of content/{ex}.json (Japanese "鉄則ショート" video scripts for Anthropic certification exam {label}; fields per scene: title, body, caption, narration, rule, wrong, nodes[].label/sub, edges[].label, and episode title).
The learner reads Claude documentation in Japanese. Terms must be the ones Anthropic uses in its official Japanese documentation (platform.claude.com/docs/ja, support.claude.com/ja, code.claude.com/docs/ja) or, where no Japanese term exists, the official English name. Flag:
1. Wrong or invented Japanese renderings (e.g. ツール使用 / ツールの使用, プロンプトキャッシュ, コンテキストウィンドウ, 拡張思考, システムプロンプト, サブエージェント, フック, 権限, 評価 (eval), 構造化出力, バッチ処理, レート制限 — check against the docs).
2. Literal or unnatural machine-like translations a Japanese engineer would not say; mixed styles (読取/読み取り).
3. Product, API and feature names that must stay in official form (Claude, Claude Code, Claude Agent SDK, Model Context Protocol (MCP), tool_use, stop_reason, CLAUDE.md, Projects, Artifacts, Messages API, Batch API …).
4. Inconsistent terms for the same thing within the file.
5. Narration only: words VOICEVOX will likely misread (suggest a reading-friendly rewrite only if needed).
6. Unofficial abbreviations.
Round {{N}}: earlier rounds were applied; report only what is still wrong.
Do not flag facts or style unrelated to terminology. Keep within the width limits when proposing fixes (scene title <= 11 full-width chars, node label <= 10, node sub <= 12, edge label <= 6; ASCII counts 0.55).
Output ONLY a JSON array: [{{"file":"...","where":"<id>/s<n> or <id>","field":"...","current":"exact current text","fix":"replacement text","reason":"official term / why"}}]. Empty array if none."""
        else:
            term = (Path.home() / ".claude/skills/exam-rule-shorts/scripts/term-audit-brief-template.txt").read_text().replace("{FILES}", f"content/{ex}.json").replace("{EXAM}", ex)
        (ROOT / f"briefs/term-audit-{ex}.txt").write_text(term)
        print(ex, label, prefix, f"start r{start:02d}", "guides", g.count(",") + 1)


if __name__ == "__main__":
    main()
