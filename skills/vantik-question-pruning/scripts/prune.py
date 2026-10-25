"""Deactivate stale, unreliable, or duplicate questions for one Vantik exam.

Runs inside the vantik container (stdin-piped), dry-run unless --apply:

  ssh ugnas 'docker exec -i vantik sh -c "cat > /tmp/prune.py && \
    /app/.venv/bin/python /tmp/prune.py --exam aws-clf-c02 --unreliable --dedupe"' < prune.py

Questions are never deleted: they get active=0 plus a dated note naming the
reason, so the admin UI can restore them. Previously missed questions are kept.
"""

import argparse
import datetime
import json
import re
import sqlite3
from collections import Counter, defaultdict

VOTE_RE = re.compile(r"(?:コミュニティ投票|Community votes): ([^\n]+)")


def parse_votes(text: str) -> list[tuple[str, int]]:
    m = VOTE_RE.search(text)
    return [(a, int(n)) for a, n in re.findall(r"([A-F]+) (\d+)", m.group(1))] if m else []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/app/data/vantik.db")
    ap.add_argument("--exam", required=True, help="exam code, e.g. aws-clf-c02")
    ap.add_argument("--source", default="past_exam", choices=["past_exam", "original", "all"])
    ap.add_argument("--unreliable", action="store_true",
                    help="drop: no ai_generated explanation, top vote != answer, or top vote share < --min-share")
    ap.add_argument("--min-share", type=float, default=0.6)
    ap.add_argument("--stale-terms", help='JSON file {"regex": "reason"}; matched against prompt + correct choices')
    ap.add_argument("--dedupe", action="store_true", help="keep one question per identical correct-answer text")
    ap.add_argument("--max-low-vote", type=int, default=0,
                    help="with --dedupe: also drop never-missed questions whose total votes <= N (0 = off)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--list", action="store_true", help="print every dropped question")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db if args.apply else f"file:{args.db}?mode=ro", uri=not args.apply)
    conn.execute("pragma busy_timeout=10000")
    exam = conn.execute("select id from exams where code=?", (args.exam,)).fetchone()
    if exam is None:
        raise SystemExit(f"unknown exam {args.exam}")
    src_sql = "" if args.source == "all" else "and qv.source_classification = ?"
    params = (exam[0],) if args.source == "all" else (exam[0], args.source)
    rows = conn.execute(f"""
        select q.id, q.source_question_id, qv.id, qv.prompt, q.note, coalesce(d.name, '')
        from questions q join question_versions qv on qv.id = q.current_version_id
        left join domains d on d.id = qv.domain_id
        where q.exam_id = ? and q.active = 1 {src_sql}""", params).fetchall()

    stale = {}
    if args.stale_terms:
        with open(args.stale_terms, encoding="utf-8") as f:
            stale = json.load(f)

    items = []
    for qid, sqid, vid, prompt, note, domain in rows:
        choices = conn.execute("select label, body from choices where question_version_id=?", (vid,)).fetchall()
        correct = sorted(r[0] for r in conn.execute(
            "select c.label from correct_answers a join choices c on c.id=a.choice_id where a.question_version_id=?", (vid,)))
        answer = " / ".join(sorted(b.strip() for l, b in choices if l in correct))
        expl = conn.execute("select source, body from explanations where question_version_id=?", (vid,)).fetchall()
        votes = parse_votes(" ".join(b for _, b in expl))
        wrong = conn.execute("""select count(*) from attempts a join question_versions v on v.id=a.question_version_id
                                where v.question_id=? and a.is_correct=0""", (qid,)).fetchone()[0]
        items.append(dict(id=qid, sq=sqid, note=note, domain=domain, answer=answer, labels="".join(correct),
                          prompt=prompt, has_ai=any(s == "ai_generated" for s, _ in expl),
                          votes=votes, total=sum(n for _, n in votes), wrong=wrong))

    drop: dict[str, tuple[dict, str]] = {}
    for it in items:
        reasons = []
        if args.unreliable:
            if not it["has_ai"]:
                reasons.append("解説不十分: 選択肢別のAI解説なし")
            if it["votes"]:
                top = max(it["votes"], key=lambda v: v[1])
                if top[0] != it["labels"]:
                    reasons.append(f"解説不十分: 投票最多{top[0]}≠表示回答{it['labels']}")
                elif top[1] / it["total"] < args.min_share:
                    reasons.append(f"解説不十分: 投票割れ{top[1]}/{it['total']}")
        for pattern, why in stale.items():
            if re.search(pattern, it["prompt"] + " " + it["answer"]):
                reasons.append(f"古い: {why}")
        if reasons:
            drop[it["id"]] = (it, "; ".join(reasons))

    if args.dedupe:
        groups = defaultdict(list)
        for it in items:
            if it["id"] not in drop:
                groups[it["answer"].lower()].append(it)
        for members in groups.values():
            members.sort(key=lambda x: (x["wrong"] == 0, -x["total"], x["sq"]))
            rep = members[0]
            for it in members[1:]:
                if it["wrong"] == 0:
                    drop[it["id"]] = (it, f"重複: 正答「{rep['answer'][:80]}」は {rep['sq']} で代表")
        if args.max_low_vote:
            for it in items:
                if it["id"] not in drop and it["wrong"] == 0 and it["votes"] and it["total"] <= args.max_low_vote:
                    drop[it["id"]] = (it, f"低優先: 投票{it['total']}票のみ")

    kept = [it for it in items if it["id"] not in drop]
    print(f"{'APPLY' if args.apply else 'DRY-RUN'} exam={args.exam} source={args.source}")
    print(f"before={len(items)} drop={len(drop)} keep={len(kept)} missed_kept={sum(1 for k in kept if k['wrong'])}")
    print("reasons", dict(Counter(r.split(':')[0] for _, r in drop.values())))
    print("domain before", dict(Counter(i["domain"] for i in items)))
    print("domain after ", dict(Counter(k["domain"] for k in kept)))
    if args.list:
        for it, why in sorted(drop.values(), key=lambda x: x[0]["sq"]):
            print(f"  {it['sq']}\t{why}")

    if args.apply:
        tag = f"[{datetime.date.today().isoformat()} 問題絞り込み]"
        for it, why in drop.values():
            note = (it["note"] + "\n" if it["note"] else "") + f"{tag} {why}"
            conn.execute("update questions set active=0, note=? where id=?", (note, it["id"]))
        conn.commit()
        print("applied")


if __name__ == "__main__":
    main()
