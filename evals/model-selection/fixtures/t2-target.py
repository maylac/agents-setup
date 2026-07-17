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
