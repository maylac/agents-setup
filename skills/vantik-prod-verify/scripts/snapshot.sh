#!/usr/bin/env bash
# Pull a consistent read-only snapshot of the Vantik production SQLite DB to this machine.
#
# usage: snapshot.sh [--out PATH] [--keep] [--integrity SCRIPT]
#   --out PATH        local destination (default /tmp/vantik-snapshot-<UTC ts>.db)
#   --keep            use the app's `vantik backup` so a dated copy also stays in /app/backups
#   --integrity PATH  additionally run reskilling-os scripts/vantik_integrity_check.py on the copy
# env: VANTIK_SSH (default ugnas; may be user@host), VANTIK_SSH_OPTS (extra ssh options, e.g. -o HostKeyAlias=...),
#      VANTIK_CONTAINER (default vantik), VANTIK_DB_PATH (default /app/data/vantik.db)
set -euo pipefail

SSH_HOST="${VANTIK_SSH:-ugnas}"
SSH_OPTS="${VANTIK_SSH_OPTS:-}"
CONTAINER="${VANTIK_CONTAINER:-vantik}"
DB_PATH="${VANTIK_DB_PATH:-/app/data/vantik.db}"
OUT=""; KEEP=0; INTEGRITY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    --integrity) INTEGRITY="$2"; shift 2 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$OUT" ] || OUT="/tmp/vantik-snapshot-$(date -u +%Y%m%dT%H%M%SZ).db"

if ! ssh -o BatchMode=yes -o ConnectTimeout=15 $SSH_OPTS "$SSH_HOST" true 2>/dev/null; then
  echo "ssh $SSH_HOST unreachable. The mDNS alias only works on the home LAN; off-LAN set VANTIK_SSH=user@<tailnet-name> and VANTIK_SSH_OPTS='-o HostKeyAlias=<original host>' (values live in auto-memory, not here)." >&2
  exit 3
fi

if [ "$KEEP" = 1 ]; then
  REMOTE="$(ssh $SSH_OPTS "$SSH_HOST" "docker exec $CONTAINER sh -c 'cd /app && .venv/bin/vantik backup'" | tail -n 1)"
  case "$REMOTE" in /app/backups/*.db) ;; *) echo "unexpected backup output: $REMOTE" >&2; exit 4 ;; esac
  ssh $SSH_OPTS "$SSH_HOST" "docker exec $CONTAINER cat '$REMOTE'" > "$OUT"
  echo "retained backup in container: $REMOTE" >&2
else
  REMOTE="/tmp/vantik-snapshot-$$.db"
  ssh $SSH_OPTS "$SSH_HOST" "docker exec -i $CONTAINER /app/.venv/bin/python - '$DB_PATH' '$REMOTE'" <<'PY' >/dev/null
import sqlite3, sys
src_path, dst_path = sys.argv[1], sys.argv[2]
src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
dst = sqlite3.connect(dst_path)
src.backup(dst)
dst.close(); src.close()
print(dst_path)
PY
  ssh $SSH_OPTS "$SSH_HOST" "docker exec $CONTAINER sh -c 'cat $REMOTE && rm -f $REMOTE'" > "$OUT"
fi

python3 - "$OUT" <<'PY'
import json, sqlite3, sys
path = sys.argv[1]
# The copy inherits journal_mode=wal from the live DB; without a -shm file a mode=ro open fails,
# so switch the local copy to a rollback journal once. Nothing else writes to this file.
con = sqlite3.connect(path)
con.execute("pragma journal_mode=delete")
con.commit(); con.close()
con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
rep = {"path": path}
rep["quick_check"] = con.execute("pragma quick_check").fetchone()[0]
rep["foreign_key_violations"] = con.execute("select count(*) from pragma_foreign_key_check").fetchone()[0]
rep["journal_mode"] = con.execute("pragma journal_mode").fetchone()[0]
for table in ("questions", "attempts", "study_sessions", "choices"):
    try:
        rep[table] = con.execute(f"select count(*) from {table}").fetchone()[0]
    except sqlite3.Error as exc:
        rep[table] = f"error: {exc}"
print(json.dumps(rep, ensure_ascii=False))
ok = rep["quick_check"] == "ok" and rep["foreign_key_violations"] == 0
sys.exit(0 if ok else 5)
PY

rm -f "$OUT-shm" "$OUT-wal"

if [ -n "$INTEGRITY" ]; then
  python3 "$INTEGRITY" "$OUT"
fi
