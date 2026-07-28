#!/usr/bin/env bash
# save-results.sh — merge evaluated skills into results.json with correct UTC timestamp
# Usage: save-results.sh RESULTS_JSON <<< "$EVAL_JSON"
#        save-results.sh RESULTS_JSON --prune-missing
#
# stdin format:
#   { "skills": {...}, "mode"?: "full"|"quick", "batch_progress"?: {...} }
#
# Always sets evaluated_at to current UTC time via `date -u`.
# Merges stdin .skills into existing results.json (new entries override old).
# Optionally updates .mode and .batch_progress if present in stdin.
#
# --prune-missing is a standalone mode: it drops entries whose skill file no longer
# exists on disk, reads no stdin, and leaves evaluated_at untouched (pruning is not
# an evaluation — advancing the timestamp would hide real edits from the next scan).
# Deletion is destructive, so this never runs as part of a normal save.

set -euo pipefail

RESULTS_JSON=""
PRUNE_MISSING=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prune-missing) PRUNE_MISSING=true ;;
    -*) echo "Error: unknown option: $1" >&2; exit 1 ;;
    *) RESULTS_JSON="$1" ;;
  esac
  shift
done

if [[ -z "$RESULTS_JSON" ]]; then
  echo "Error: RESULTS_JSON argument required" >&2
  echo "Usage: save-results.sh RESULTS_JSON <<< \"\$EVAL_JSON\"" >&2
  echo "       save-results.sh RESULTS_JSON --prune-missing" >&2
  exit 1
fi

if [[ "$PRUNE_MISSING" == true ]]; then
  if [[ ! -f "$RESULTS_JSON" ]]; then
    echo "Error: RESULTS_JSON not found: $RESULTS_JSON" >&2
    exit 1
  fi

  dropped=$(while IFS=$'\t' read -r name path; do
    [[ -f "${path/#\~/$HOME}" ]] || printf '%s\n' "$name"
  done < <(jq -r '.skills // {} | to_entries[] | "\(.key)\t\(.value.path)"' "$RESULTS_JSON"))

  if [[ -z "$dropped" ]]; then
    echo "No missing entries to prune." >&2
    exit 0
  fi

  drop_json=$(printf '%s\n' "$dropped" | jq -R -s 'split("\n") | map(select(length > 0))')

  tmp=$(mktemp "${RESULTS_JSON}.XXXXXX")
  trap 'rm -f "$tmp"' EXIT

  # Bind .key before indexing: index()'s argument is evaluated against $drop, not
  # against the {key,value} entry, so `index(.key)` would try to index the array.
  jq --argjson drop "$drop_json" \
    '.skills |= with_entries(select(.key as $k | ($drop | index($k)) == null))' \
    "$RESULTS_JSON" > "$tmp"

  mv "$tmp" "$RESULTS_JSON"

  echo "Pruned $(printf '%s\n' "$dropped" | wc -l | tr -d ' ') entries whose files no longer exist:" >&2
  printf '%s\n' "$dropped" | sed 's/^/  /' >&2
  exit 0
fi

EVALUATED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Read eval results from stdin and validate JSON before touching the results file
input_json=$(cat)
if ! echo "$input_json" | jq empty 2>/dev/null; then
  echo "Error: stdin is not valid JSON" >&2
  exit 1
fi

if [[ ! -f "$RESULTS_JSON" ]]; then
  # Bootstrap: create new results.json from stdin JSON + current UTC timestamp
  echo "$input_json" | jq --arg ea "$EVALUATED_AT" \
    '. + { evaluated_at: $ea }' > "$RESULTS_JSON"
  exit 0
fi

# Merge: new .skills override existing ones; old skills not in input_json are kept.
# Optionally update .mode and .batch_progress if provided.
#
# Use mktemp for a collision-safe temp file (concurrent runs on the same RESULTS_JSON
# would race on a predictable ".tmp" suffix; random suffix prevents silent overwrites).
tmp=$(mktemp "${RESULTS_JSON}.XXXXXX")
trap 'rm -f "$tmp"' EXIT

jq -s \
  --arg ea "$EVALUATED_AT" \
  '.[0] as $existing | .[1] as $new |
   $existing |
   .evaluated_at = $ea |
   .skills = ($existing.skills + ($new.skills // {})) |
   if ($new | has("mode")) then .mode = $new.mode else . end |
   if ($new | has("batch_progress")) then .batch_progress = $new.batch_progress else . end' \
  "$RESULTS_JSON" <(echo "$input_json") > "$tmp"

mv "$tmp" "$RESULTS_JSON"
