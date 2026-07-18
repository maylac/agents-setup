#!/usr/bin/env bash
# Lightweight Stop hook for terminal-hosted agent sessions.
# Emits a terminal bell and a throttled macOS notification without stealing focus.
set -u

# Orca-hosted sessions: Orca's own UI surfaces agent state; skip to avoid double notification.
if [ -n "${ORCA_PANE_KEY:-}" ] || [ "${TERM_PROGRAM:-}" = "Orca" ]; then
  exit 0
fi

agent="${1:-Agent}"
input="$(cat || true)"
cwd=""
transcript=""

if command -v jq >/dev/null 2>&1; then
  cwd="$(printf '%s' "$input" | jq -r '.cwd // .workspace.cwd // .workspace_dir // .project_dir // empty' 2>/dev/null | head -n 1)"
  transcript="$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null | head -n 1)"
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

# 通知粒度: 「タスク完了」のみMac通知する(2026-07-18ユーザー指示)。最後のユーザー入力から
# 短時間で終わったターンは対話応答なのでスキップ(ベルはターミナル内の即時合図として維持)。
# タイムスタンプが取れないときは通知する(無人タスクの完了を逃さない側に倒す)。
MIN_TASK_SECONDS="${NOTIFY_MIN_TASK_SECONDS:-120}"
if [ -n "$transcript" ] && [ -r "$transcript" ] && command -v jq >/dev/null 2>&1; then
  last_user_ts="$(tail -n 400 "$transcript" 2>/dev/null | jq -rs '
    map(
      if .type=="user" then
        (select((.message.content|type)=="string"
          or ([.message.content[]?.type // empty] | index("tool_result") | not))
         | .timestamp)
      elif .type=="event_msg" and (.payload.type // "")=="user_message" then .timestamp
      else empty end)
    | map(select(type=="string")) | last // empty
    | sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601' 2>/dev/null)"
  case "$last_user_ts" in
    ''|*[!0-9]*) : ;;
    *) [ "$((now - last_user_ts))" -lt "$MIN_TASK_SECONDS" ] && exit 0 ;;
  esac
fi

if [ "$((now - last))" -ge 45 ]; then
  if command -v terminal-notifier >/dev/null 2>&1; then
    # 直前のassistantメッセージ抜粋を本文に載せ、何が起きて何を求められているかを通知だけで判別可能にする。
    # Claude transcript(.type=="assistant")とCodex rollout(.type=="response_item")の両形式に対応。
    # 切り詰めはjq内(文字単位)。cut -cはバイト切りでUTF-8を壊す。
    excerpt=""
    if [ -n "$transcript" ] && [ -r "$transcript" ] && command -v jq >/dev/null 2>&1; then
      excerpt="$(tail -n 400 "$transcript" 2>/dev/null | jq -rs '
        map(
          if .type=="response_item"
          then (.payload | select(.type=="message" and .role=="assistant")
            | (.content // [] | map(.text? // empty) | join(" ")))
          elif (.type=="assistant" or .role=="assistant")
          then ((.message.content? // .content? // empty)
            | if type=="array" then (map(.text? // empty)|join(" ")) else tostring end)
          else empty end)
        | map(select(length>0 and . != "null")) | last // empty
        | gsub("\n"; " ") | .[0:180]' 2>/dev/null)"
      [ "$excerpt" = "null" ] && excerpt=""
    fi
    terminal-notifier \
      -title "$agent 応答完了 · $project" \
      -message "${excerpt:-$cwd}$unpushed" \
      -group "agent-terminal-notify-$hash" >/dev/null 2>&1 || true
  fi
  printf '%s\n' "$now" >"$state_file" 2>/dev/null || true
fi

exit 0
