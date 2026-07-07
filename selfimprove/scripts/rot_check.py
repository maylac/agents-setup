#!/usr/bin/env python3
"""selfimprove rot check — ハーネス7系統の腐敗検知 + 蒸留元台帳の巡回期限チェック。

決定的に判定できる検査だけを行う(LLM不要・ネットワーク不要・stdlibのみ)。
判断が必要な深掘りは /self-improve スキル経由で harness-audit / skill-stocktake に委譲する。

usage: python3 rot_check.py [--report-dir DIR] [--no-report]
出力: reports/rot-YYYY-MM-DD.md + stdout要約。findingsが1件以上なら exit 1。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import plistlib
import re
import subprocess
import sys

HOME = os.path.expanduser("~")
CANON_SKILLS = os.path.join(HOME, ".agents", "skills")
MIRROR_DIRS = [os.path.join(HOME, ".claude", "skills"), os.path.join(HOME, ".codex", "skills")]
# auto-memoryのプロジェクトdir名はcwdパスの / を - に置換したもの (HOME直下セッションが対象)
MEMORY_DIR = os.path.join(HOME, ".claude", "projects", HOME.replace(os.sep, "-"), "memory")
SETTINGS_JSON = os.path.join(HOME, ".claude", "settings.json")
CLAUDE_JSON = os.path.join(HOME, ".claude.json")
HOOKS_DIR = os.path.join(HOME, ".claude", "hooks")
LAUNCH_AGENTS = os.path.join(HOME, "Library", "LaunchAgents")
AGENTS_SETUP = os.path.join(HOME, "workspace", "agents-setup")
SELFIMPROVE = os.path.join(AGENTS_SETUP, "selfimprove")
SOURCES_LEDGER = os.path.join(SELFIMPROVE, "ledger", "sources.md")
LESSONS_MD = os.path.join(HOME, "tasks", "lessons.md")

LESSONS_LINE_CAP = 50          # 超えたら /self-improve distill で圧縮する
CLAUDE_MD_LINE_CAP = 120       # グローバル/ホームCLAUDE.mdの行数予算
PROJECT_MEMORY_STALE_DAYS = 60  # projectメモリの再点検しきい値

# 監査対象のCLAUDE.md群: (表示名, パス, 相対パス解決の基準dir)
CLAUDE_MD_TARGETS = [
    ("global CLAUDE.md", os.path.join(HOME, ".claude", "CLAUDE.md"),
     os.path.join(AGENTS_SETUP, "claude")),
    ("home CLAUDE.md", os.path.join(HOME, "CLAUDE.md"), HOME),
]


def read(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


class Findings:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []  # (severity, section, message)
        self.info: list[tuple[str, str]] = []        # (section, message)

    def warn(self, section: str, msg: str) -> None:
        self.items.append(("WARN", section, msg))

    def note(self, section: str, msg: str) -> None:
        self.info.append((section, msg))


def check_skills(f: Findings) -> None:
    """①系統1: skill資産 — SKILL.md欠落・description欠落・参照ファイル欠落・ミラー破損"""
    sec = "skills"
    if not os.path.isdir(CANON_SKILLS):
        f.warn(sec, f"正本ディレクトリが無い: {CANON_SKILLS}")
        return
    # 直前が / や $変数 のもの(例: $SI/scripts/x.py)はスキル外参照なので除外
    ref_re = re.compile(r"(?<![\w$/])(scripts|references|assets)/[\w\-./]+\.\w{1,8}\b")
    for name in sorted(os.listdir(CANON_SKILLS)):
        if name.startswith("."):
            continue
        d = os.path.join(CANON_SKILLS, name)
        if not os.path.isdir(d):
            continue
        sk = os.path.join(d, "SKILL.md")
        if not os.path.exists(sk):
            f.warn(sec, f"{name}: SKILL.md が無い")
            continue
        text = read(sk)
        if not re.search(r"^description:", text, re.M):
            f.warn(sec, f"{name}: frontmatter に description が無い")
        for m in sorted({m.group(0) for m in ref_re.finditer(text)}):
            if os.path.exists(os.path.join(d, m)):
                continue
            subdir = m.split("/", 1)[0]
            if os.path.isdir(os.path.join(d, subdir)):
                # スキルが同種のdirを同梱しているのにファイルが無い → 真の欠落
                f.warn(sec, f"{name}: SKILL.md が参照する {m} が実在しない")
            else:
                f.note(sec, f"{name}: {m} への言及あり(対象プロジェクト相対パスの可能性・要目視)")
        if re.search(r"^origin:", text, re.M):
            f.note(sec, f"{name}: 外部pinスキル(origin指定) — 上流diffは台帳巡回で確認")
    for mirror in MIRROR_DIRS:
        if not os.path.isdir(mirror):
            continue
        for name in sorted(os.listdir(mirror)):
            p = os.path.join(mirror, name)
            if os.path.islink(p) and not os.path.exists(p):
                f.warn(sec, f"ミラー {mirror} のリンク切れ: {name}")


def check_memory(f: Findings) -> None:
    """①系統2: auto-memory — 索引と実体の不整合・陳腐化projectメモリ"""
    sec = "memory"
    index = os.path.join(MEMORY_DIR, "MEMORY.md")
    if not os.path.exists(index):
        f.warn(sec, f"MEMORY.md が無い: {index}")
        return
    text = read(index)
    linked = set(re.findall(r"\]\(([\w\-.]+\.md)\)", text))
    actual = {n for n in os.listdir(MEMORY_DIR) if n.endswith(".md") and n != "MEMORY.md"}
    for name in sorted(linked - actual):
        f.warn(sec, f"MEMORY.md が指すファイルが無い: {name}")
    for name in sorted(actual - linked):
        f.warn(sec, f"索引に載っていないメモリ: {name}")
    now = dt.datetime.now().timestamp()
    for name in sorted(actual):
        p = os.path.join(MEMORY_DIR, name)
        if "type: project" not in read(p):
            continue
        age_days = (now - os.path.getmtime(p)) / 86400
        if age_days > PROJECT_MEMORY_STALE_DAYS:
            f.note(sec, f"{name}: projectメモリが{int(age_days)}日未更新 — supersede判定候補")


def _home_paths_in(cmd: str) -> list[str]:
    return re.findall(r"/Users/[\w.-]+/[\w\-./ ]*?\.(?:sh|py|js|rb)\b", cmd)


def check_hooks(f: Findings) -> None:
    """①系統3: hooks — settings.json配線先スクリプトの実在・リンク切れ"""
    sec = "hooks"
    try:
        settings = json.loads(read(SETTINGS_JSON))
    except (OSError, json.JSONDecodeError) as e:
        f.warn(sec, f"settings.json が読めない: {e}")
        return
    for event, matchers in (settings.get("hooks") or {}).items():
        for m in matchers:
            for h in m.get("hooks", []):
                for path in _home_paths_in(h.get("command", "")):
                    if not os.path.exists(path):
                        f.warn(sec, f"{event} フックのスクリプトが無い: {path}")
    if os.path.isdir(HOOKS_DIR):
        for name in sorted(os.listdir(HOOKS_DIR)):
            p = os.path.join(HOOKS_DIR, name)
            if os.path.islink(p) and not os.path.exists(p):
                f.warn(sec, f"~/.claude/hooks のリンク切れ: {name}")


def check_permissions(f: Findings) -> None:
    """①系統4: permissions — 存在しないMCPサーバーを指すルールの残骸"""
    sec = "permissions"
    try:
        settings = json.loads(read(SETTINGS_JSON))
        perms = settings.get("permissions") or {}
    except (OSError, json.JSONDecodeError):
        return
    known: set[str] = set()
    try:
        cj = json.loads(read(CLAUDE_JSON))
        known.update((cj.get("mcpServers") or {}).keys())
        for proj in (cj.get("projects") or {}).values():
            known.update((proj.get("mcpServers") or {}).keys())
    except (OSError, json.JSONDecodeError):
        f.note(sec, "~/.claude.json が読めないため MCP サーバー照合をスキップ")
        return
    for kind in ("allow", "deny", "ask"):
        for rule in perms.get(kind, []):
            m = re.match(r"mcp__([\w-]+)__", rule)
            if m and m.group(1) not in known:
                f.warn(sec, f"{kind} ルールが未登録MCPサーバーを指す: {rule}")
    f.note(sec, "許可プロンプト削減の定例は公式 /fewer-permission-prompts を使う")


def check_claude_md(f: Findings) -> None:
    """①系統5: CLAUDE.md/rules — 参照パスの実在・行数予算"""
    sec = "claude-md"
    token_re = re.compile(r"`([^`\n]+)`")
    for label, path, base in CLAUDE_MD_TARGETS:
        if not os.path.exists(path):
            f.warn(sec, f"{label} が無い: {path}")
            continue
        text = read(path)
        nlines = text.count("\n") + 1
        if nlines > CLAUDE_MD_LINE_CAP:
            f.warn(sec, f"{label}: {nlines}行 (予算{CLAUDE_MD_LINE_CAP}行) — 整理候補")
        for tok in token_re.findall(text):
            cand = tok.strip()
            if not re.fullmatch(r"[\w\-./~]+\.(?:md|sh|py|js|json|toml|yaml)", cand):
                continue
            p = os.path.expanduser(cand)
            if os.path.isabs(p):
                candidates = [p]
            else:
                # 基準dir・repoルート・実体ファイルの隣、いずれかに実在すればOK
                candidates = [os.path.join(b, cand) for b in
                              (base, AGENTS_SETUP, os.path.dirname(os.path.realpath(path)), HOME)]
            if not any(os.path.exists(c) for c in candidates):
                f.warn(sec, f"{label} が参照するパスが実在しない: {cand}")
    if os.path.exists(LESSONS_MD):
        nlines = read(LESSONS_MD).count("\n") + 1
        if nlines > LESSONS_LINE_CAP:
            f.warn(sec, f"lessons.md: {nlines}行 (上限{LESSONS_LINE_CAP}行) — /self-improve distill で圧縮")
    else:
        f.warn(sec, f"lessons.md が無い: {LESSONS_MD}")


def check_launchd(f: Findings) -> None:
    """①系統6: launchd自動化 — plistの指すスクリプト実在・ロード状態"""
    sec = "launchd"
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10).stdout
        loaded = {line.split("\t")[-1].strip() for line in out.splitlines()[1:] if line.strip()}
    except (OSError, subprocess.SubprocessError):
        loaded = set()
        f.note(sec, "launchctl list が実行できずロード状態の照合をスキップ")
    if not os.path.isdir(LAUNCH_AGENTS):
        return
    for name in sorted(os.listdir(LAUNCH_AGENTS)):
        if not name.endswith(".plist"):
            continue
        label = name[: -len(".plist")]
        if not (label.startswith("com.maylac.") or label.startswith("ai.hermes.")):
            continue
        p = os.path.join(LAUNCH_AGENTS, name)
        try:
            with open(p, "rb") as fp:
                plist = plistlib.load(fp)
        except Exception as e:  # noqa: BLE001 — 壊れたplist自体がfinding
            f.warn(sec, f"{name}: plistが読めない ({e})")
            continue
        for arg in plist.get("ProgramArguments", []):
            if arg.startswith("/Users/") and re.search(r"\.(?:sh|py|js|rb)$", arg) and not os.path.exists(arg):
                f.warn(sec, f"{label}: スクリプトが無い: {arg}")
        if loaded and label not in loaded:
            f.note(sec, f"{label}: plistはあるが現在ロードされていない")


def check_sources_ledger(f: Findings) -> list[str]:
    """③: 蒸留元台帳 — 巡回期限が来たソースの列挙"""
    sec = "sources"
    due: list[str] = []
    if not os.path.exists(SOURCES_LEDGER):
        f.warn(sec, f"蒸留元台帳が無い: {SOURCES_LEDGER}")
        return due
    today = dt.date.today()
    for line in read(SOURCES_LEDGER).splitlines():
        if not line.startswith("|") or line.startswith("| id") or set(line) <= {"|", "-", " "}:
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 5:
            f.warn(sec, f"台帳の行が壊れている: {line[:60]}")
            continue
        sid, _url, _kind, cadence, last = cols[:5]
        try:
            cadence_days = int(cadence)
            last_date = dt.date.fromisoformat(last)
        except ValueError:
            f.warn(sec, f"台帳の cadence/last_checked が不正: {sid}")
            continue
        overdue = (today - last_date).days - cadence_days
        if overdue >= 0:
            due.append(f"{sid} (期限{overdue}日超過)")
    return due


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-dir", default=os.path.join(SELFIMPROVE, "reports"))
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args()

    f = Findings()
    check_skills(f)
    check_memory(f)
    check_hooks(f)
    check_permissions(f)
    check_claude_md(f)
    check_launchd(f)
    due = check_sources_ledger(f)

    today = dt.date.today().isoformat()
    lines = [f"# rot check {today}", ""]
    lines.append(f"- findings: {len(f.items)} / due sources: {len(due)}")
    lines.append("")
    if f.items:
        lines.append("## Findings (要対応)")
        for sev, sec, msg in f.items:
            lines.append(f"- [{sev}][{sec}] {msg}")
        lines.append("")
    if due:
        lines.append("## 巡回期限が来た蒸留元 (③ /self-improve sources)")
        for d in due:
            lines.append(f"- {d}")
        lines.append("")
    if f.info:
        lines.append("## Info (参考)")
        for sec, msg in f.info:
            lines.append(f"- [{sec}] {msg}")
        lines.append("")
    report = "\n".join(lines)

    if not args.no_report:
        os.makedirs(args.report_dir, exist_ok=True)
        path = os.path.join(args.report_dir, f"rot-{today}.md")
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(report)
        print(f"report: {path}")
    print(f"rot_check: findings={len(f.items)} due_sources={len(due)}")
    for sev, sec, msg in f.items:
        print(f"  [{sev}][{sec}] {msg}")
    for d in due:
        print(f"  [DUE][sources] {d}")
    return 1 if (f.items or due) else 0


if __name__ == "__main__":
    sys.exit(main())
