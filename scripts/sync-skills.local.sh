#!/usr/bin/env bash
# sync-skills.sh — 単一正本 (~/.agents/skills) を各エージェントへ symlink でフルミラー。
# 冪等。新規スキル追加 (skill-create / skills add) のあとに再実行すれば常に同期が保たれる。
#
#   usage: bash ~/.agents/sync-skills.sh [--dry-run]
#
# 仕様:
#   - 正本 ~/.agents/skills/<name> (実体dir または dirへのsymlink) を対象。
#   - 各エージェントdirに ../../.agents/skills/<name> への相対symlinkを張る。
#       実体dir → 削除して symlink 化 / 既存symlink → 張り直し / 無し → 新規作成。
#   - 各エージェントdir直下のリンク切れsymlinkは prune。
#   - 名前が "." で始まるエントリ (.system 等) と非dirは無視。
#   - source-command-* は Codex 専用の移植成果物のため Claude 側ミラーからは除外する
#     (対応コマンドが ~/.claude/commands/ に実在し、二重登録になるため)。

set -euo pipefail

CANON="$HOME/.agents/skills"
AGENT_DIRS=("$HOME/.claude/skills" "$HOME/.codex/skills")
HERMES_LOCAL="$HOME/.hermes/skills"
HERMES_SHARED="$HOME/.hermes/shared-skills"
REL_PREFIX="../../.agents/skills"   # <agent>/skills/<name> から見た正本への相対パス
HERMES_REL_PREFIX="../../.agents/skills" # ~/.hermes/shared-skills/<name> から見た正本への相対パス

# Claude 側のみ除外するスキル名パターン (Codex 側には引き続き symlink する)
# chronicle: Codex専用 (2026-07-07 skills監査) — Claudeでは発火不能なのに長い
# descriptionが毎セッション注入されるため、Claudeミラーからは外す。
claude_excluded() {
  case "$1" in
    source-command-*) return 0 ;;
    chronicle) return 0 ;;
    *) return 1 ;;
  esac
}

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

run() { if [ "$DRY_RUN" = 1 ]; then echo "DRY: $*"; else eval "$@"; fi; }

created=0 relinked=0 replaced=0 pruned=0 kept=0

for agent in "${AGENT_DIRS[@]}"; do
  run "mkdir -p \"$agent\""

  # --- 正本の各スキルを symlink でミラー ---
  for path in "$CANON"/*; do
    name="$(basename "$path")"
    case "$name" in .*) continue;; esac      # ドット始まりは無視
    [ -d "$path" ] || continue               # dir (symlink-to-dir含む) のみ
    link="$agent/$name"
    want="$REL_PREFIX/$name"

    if [ "$agent" = "$HOME/.claude/skills" ] && claude_excluded "$name"; then
      if [ -e "$link" ] || [ -L "$link" ]; then
        run "rm -rf \"$link\""; pruned=$((pruned+1))
      fi
      continue
    fi

    if [ -L "$link" ]; then
      cur="$(readlink "$link")"
      if [ "$cur" = "$want" ]; then kept=$((kept+1)); continue; fi
      run "rm -f \"$link\" && ln -s \"$want\" \"$link\""; relinked=$((relinked+1))
    elif [ -e "$link" ]; then                 # 実体dir/ファイル → 置換
      run "rm -rf \"$link\" && ln -s \"$want\" \"$link\""; replaced=$((replaced+1))
    else
      run "ln -s \"$want\" \"$link\""; created=$((created+1))
    fi
  done

  # --- リンク切れ symlink を prune (直下のみ) ---
  while IFS= read -r dead; do
    [ -n "$dead" ] || continue
    run "rm -f \"$dead\""; pruned=$((pruned+1))
  done < <(find "$agent" -maxdepth 1 -type l ! -exec test -e {} \; -print 2>/dev/null)
done

if [ -d "$HOME/.hermes" ]; then
  run "mkdir -p \"$HERMES_SHARED\""

  hermes_local_names_file="$(mktemp)"
  if [ -d "$HERMES_LOCAL" ]; then
    while IFS= read -r skill_md; do
      [ -n "$skill_md" ] || continue
      basename "$(dirname "$skill_md")" >> "$hermes_local_names_file"
    done < <(find "$HERMES_LOCAL" -name SKILL.md -print 2>/dev/null)
  fi
  sort -u "$hermes_local_names_file" -o "$hermes_local_names_file"

  for path in "$CANON"/*; do
    name="$(basename "$path")"
    case "$name" in .*) continue;; esac
    [ -d "$path" ] || continue
    if grep -Fxq "$name" "$hermes_local_names_file"; then
      continue
    fi

    link="$HERMES_SHARED/$name"
    want="$HERMES_REL_PREFIX/$name"
    if [ -L "$link" ]; then
      cur="$(readlink "$link")"
      if [ "$cur" = "$want" ]; then kept=$((kept+1)); continue; fi
      run "rm -f \"$link\" && ln -s \"$want\" \"$link\""; relinked=$((relinked+1))
    elif [ -e "$link" ]; then
      run "rm -rf \"$link\" && ln -s \"$want\" \"$link\""; replaced=$((replaced+1))
    else
      run "ln -s \"$want\" \"$link\""; created=$((created+1))
    fi
  done

  while IFS= read -r dead; do
    [ -n "$dead" ] || continue
    run "rm -f \"$dead\""; pruned=$((pruned+1))
  done < <(find "$HERMES_SHARED" -maxdepth 1 -type l ! -exec test -e {} \; -print 2>/dev/null)

  rm -f "$hermes_local_names_file"
fi

echo "sync done: created=$created relinked=$relinked replaced=$replaced pruned=$pruned kept=$kept (dry_run=$DRY_RUN)"
