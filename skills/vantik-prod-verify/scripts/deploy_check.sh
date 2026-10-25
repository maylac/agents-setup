#!/usr/bin/env bash
# Confirm which reskilling-os revision is live in the Vantik container and whether it matches master.
#
# usage: deploy_check.sh [--repo PATH] [--expect SHA] [--wait MINUTES]
#   --repo PATH     reskilling-os checkout; expected SHA = origin/master after a fetch
#   --expect SHA    expected revision (overrides --repo)
#   --wait MINUTES  poll every 60 s until the live revision matches (max MINUTES)
# env: VANTIK_SSH (default ugnas; may be user@host), VANTIK_SSH_OPTS (extra ssh options), VANTIK_CONTAINER (default vantik),
#      VANTIK_GH_REPO (default maylac/reskilling-os)
set -euo pipefail

SSH_HOST="${VANTIK_SSH:-ugnas}"
SSH_OPTS="${VANTIK_SSH_OPTS:-}"
CONTAINER="${VANTIK_CONTAINER:-vantik}"
GH_REPO="${VANTIK_GH_REPO:-maylac/reskilling-os}"
REPO=""; EXPECT=""; WAIT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --expect) EXPECT="$2"; shift 2 ;;
    --wait) WAIT="$2"; shift 2 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$EXPECT" ] && [ -n "$REPO" ]; then
  git -C "$REPO" fetch -q origin master
  EXPECT="$(git -C "$REPO" rev-parse origin/master)"
fi

live() {
  ssh -o BatchMode=yes -o ConnectTimeout=15 $SSH_OPTS "$SSH_HOST" \
    "docker inspect --format '{{.State.Health.Status}} {{.Config.Image}} {{index .Config.Labels \"org.opencontainers.image.revision\"}}' $CONTAINER; docker exec $CONTAINER curl -sf http://localhost:8000/health"
}

if command -v gh >/dev/null 2>&1; then
  echo "== recent workflow runs ($GH_REPO) =="
  gh run list -R "$GH_REPO" --limit 6 \
    --json workflowName,status,conclusion,headSha,createdAt \
    --jq '.[] | "\(.createdAt)  \(.workflowName)\t\(.status)\t\(.conclusion)\t\(.headSha[0:7])"' || true
fi

deadline=$(( $(date +%s) + WAIT * 60 ))
while :; do
  out="$(live)" || { echo "cannot reach container $CONTAINER via $SSH_HOST" >&2; exit 3; }
  health_line="$(printf '%s\n' "$out" | sed -n 1p)"
  json="$(printf '%s\n' "$out" | sed -n 2p)"
  rev="$(printf '%s' "$json" | sed -E 's/.*"revision":"([^"]*)".*/\1/')"
  echo "== live =="
  echo "container: $health_line"
  echo "health:    $json"
  if [ -z "$EXPECT" ]; then exit 0; fi
  if [ "$rev" = "$EXPECT" ]; then
    echo "MATCH: live revision == expected ${EXPECT:0:7}"
    exit 0
  fi
  echo "MISMATCH: live ${rev:0:7} != expected ${EXPECT:0:7}"
  if [ "$(date +%s)" -ge "$deadline" ]; then exit 1; fi
  sleep 60
done
