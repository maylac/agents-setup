#!/usr/bin/env python3
"""Every official task of the exam is the subject of at least one episode (existing + new)."""
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_briefs import CLAUDE, VC  # noqa: E402
ROOT = Path(__file__).resolve().parent.parent
ex = sys.argv[1]
fc = json.loads((VC / "flashcards" / f"{ex}.json").read_text())
tasks = [t["id"] for d in fc["domains"] for t in d["tasks"]]
new = json.loads((ROOT / "content" / f"{ex}.json").read_text())
cov = Counter(e.get("task") for e in new)
bad = [e["id"] for e in new if e.get("task") not in tasks]
if ex not in CLAUDE:
    m = json.loads((ROOT / "evidence" / f"coverage-{ex}.json").read_text())
    cov.update(m.get("existing", {}).values())
    missing_ids = set(m.get("new", {})) ^ {e["id"] for e in new}
    if missing_ids:
        print("coverage file and content disagree:", sorted(missing_ids))
else:
    task_of = {d["id"]: d["tasks"][0]["id"] for d in fc["domains"]}
    want = {task_of[d]: n for d, n in CLAUDE[ex][2].items()}
    short = {t: (cov[t], n) for t, n in want.items() if cov[t] < n}
    if short:
        print("domain quota short (have, want):", short)
missing = [t for t in tasks if not cov[t]]
print(ex, "episodes new", len(new), "tasks", len(tasks), "covered", len(tasks) - len(missing), "missing", missing, "bad task ids", bad)
sys.exit(1 if missing or bad else 0)
