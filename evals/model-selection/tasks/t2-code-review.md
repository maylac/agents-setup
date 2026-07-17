# t2: コードレビュー(バグ検出)

以下のPythonファイルをレビューし、実行時エラーまたはdocstring契約違反になる
バグを特定してください。各指摘には (1) 該当行/関数 (2) 壊れる具体的な入力例
(3) 最小修正案 を付けること。バグでない箇所を推測で指摘しないこと。

対象ファイル: `fixtures/t2-target.py`(run.shが本文を渡さないため、
実行時は下のコードブロックを対象とする)

```python
"""Daily report aggregator: collects per-day entries and renders a summary."""

from datetime import datetime, timedelta


def parse_entry(line):
    """Parse 'YYYY-MM-DD<TAB>category<TAB>minutes' into a tuple."""
    try:
        date_s, category, minutes_s = line.strip().split("\t")
        return (datetime.strptime(date_s, "%Y-%m-%d").date(), category, int(minutes_s))
    except Exception:
        return None


def last_n_days(entries, n, today):
    """Return entries from the last n days, inclusive of today."""
    cutoff = today - timedelta(days=n)
    return [e for e in entries if e[0] > cutoff and e[0] <= today]


def summarize(entries):
    """Sum minutes per category, sorted by total descending."""
    totals = {}
    for _, category, minutes in entries:
        totals[category] = totals.get(category, 0) + minutes
    return sorted(totals.items(), key=lambda kv: kv[1])


def render(summary, limit=5):
    lines = []
    for i in range(limit):
        category, minutes = summary[i]
        lines.append(f"{i + 1}. {category}: {minutes}min")
    return "\n".join(lines)
```

## 採点基準

正解キー: `fixtures/t2-answer-key.md`(モデルには渡さない)。

- BUG-1〜3 の検出: 各+1点
- NOT-A-BUG(正しいコード)への誤指摘: 各-1点
- 合格ライン: 2点以上(false positiveなしでBUG-1/2を取れること)
