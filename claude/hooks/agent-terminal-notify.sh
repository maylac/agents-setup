#!/usr/bin/env bash
# Lightweight Stop hook for terminal-hosted agent sessions.
# Emits a terminal bell and a throttled macOS notification without stealing focus.
set -u

agent="${1:-Agent}"
input="$(cat || true)"
cwd=""

if command -v jq >/dev/null 2>&1; then
  cwd="$(printf '%s' "$input" | jq -r '.cwd // .workspace.cwd // .workspace_dir // .project_dir // empty' 2>/dev/null | head -n 1)"
fi

if [ -z "$cwd" ] || [ "$cwd" = "null" ]; then
  cwd="${PWD:-$HOME}"
fi

project="$(basename "$cwd")"
now="$(date +%s)"
hash="$(printf '%s:%s' "$agent" "$cwd" | shasum | awk '{print substr($1, 1, 12)}')"
state_dir="${TMPDIR:-/tmp}/agent-terminal-notify-${USER:-user}"
state_file="$state_dir/$hash"
last="0"
unpushed=""

mkdir -p "$state_dir" 2>/dev/null || true
if [ -r "$state_file" ]; then
  last="$(cat "$state_file" 2>/dev/null || printf '0')"
fi
case "$last" in
  ''|*[!0-9]*) last="0" ;;
esac

tty_path="$(tty 2>/dev/null || true)"
if [ -n "$tty_path" ] && [ "$tty_path" != "not a tty" ]; then
  printf '\a' >"$tty_path" 2>/dev/null || true
fi

if git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  upstream="$(git -C "$cwd" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
  if [ -n "$upstream" ]; then
    ahead="$(git -C "$cwd" rev-list --count "$upstream"..HEAD 2>/dev/null || printf '0')"
    case "$ahead" in
      ''|*[!0-9]*) ahead="0" ;;
    esac
    if [ "$ahead" -gt 0 ]; then
      unpushed="; unpushed commits: $ahead"
    fi
  fi
fi

if [ "$((now - last))" -ge 45 ]; then
  if command -v terminal-notifier >/dev/null 2>&1; then
    terminal-notifier \
      -title "$agent waiting" \
      -subtitle "$project" \
      -message "$cwd$unpushed" \
      -group "agent-terminal-notify-$hash" >/dev/null 2>&1 || true
  fi
  printf '%s\n' "$now" >"$state_file" 2>/dev/null || true
fi

exit 0
