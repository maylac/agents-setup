#!/usr/bin/env bash
# Mobile notification hook for Claude/Codex: notify-mobile.sh <approval|done|idle> <Agent>
# Reads the hook JSON on stdin. Sends through the first configured transport in
# ~/.config/agents-notify/env (owner-only): NOTIFY_NTFY_URL, or
# NOTIFY_SLACK_BOT_TOKEN + NOTIFY_SLACK_CHANNEL. With none configured it only logs.
# Always exits 0 so a missing transport never blocks the agent.
set -u

kind="${1:-done}"
agent="${2:-Agent}"
input="$(cat 2>/dev/null || true)"
env_file="${AGENTS_NOTIFY_ENV:-$HOME/.config/agents-notify/env}"
log_dir="$HOME/.local/state/agents-notify"
mkdir -p "$log_dir" 2>/dev/null || true
log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >>"$log_dir/notify.log" 2>/dev/null || true; }

# shellcheck disable=SC1090
[ -f "$env_file" ] && . "$env_file"

field() { command -v jq >/dev/null 2>&1 && printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null | head -n 1; }
cwd="$(field '.cwd')"
project="$(basename "${cwd:-${PWD:-$HOME}}")"
case "$kind" in
  approval)
    tool="$(field '.tool_name')"
    cmd="$(field '.tool_input.command' | cut -c1-120)"
    message="$agent が承認待ち: ${tool:-tool}${cmd:+ — $cmd}" ;;
  idle) message="$agent が入力待ち" ;;
  *) message="$agent が完了" ;;
esac
message="[$project] $message"

if [ -n "${NOTIFY_NTFY_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  if curl -fsS -m 5 -H "Title: $agent" -d "$message" "$NOTIFY_NTFY_URL" >/dev/null 2>&1; then
    log "sent ntfy kind=$kind"; exit 0
  fi
  log "ntfy failed kind=$kind"
fi

if [ -n "${NOTIFY_SLACK_BOT_TOKEN:-}" ] && [ -n "${NOTIFY_SLACK_CHANNEL:-}" ] && command -v curl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
  body="$(jq -n --arg c "$NOTIFY_SLACK_CHANNEL" --arg t "$message" '{channel:$c,text:$t}')"
  if curl -fsS -m 5 -H "Authorization: Bearer $NOTIFY_SLACK_BOT_TOKEN" -H 'Content-Type: application/json; charset=utf-8' \
      -d "$body" https://slack.com/api/chat.postMessage 2>/dev/null | jq -e '.ok' >/dev/null 2>&1; then
    log "sent slack kind=$kind"; exit 0
  fi
  log "slack failed kind=$kind"
fi

log "not sent (no transport configured) kind=$kind: $message"
exit 0
