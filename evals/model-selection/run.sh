#!/bin/bash
# run.sh — モデル選定evalの最小ランナー。
# 使い方: ./run.sh <model> <task-id>   例: ./run.sh sonnet t2
# 同一タスクを複数モデルで実行し、outputs/ に保存して人間が採点する。
set -euo pipefail

cd "$(dirname "$0")"

model="${1:?usage: ./run.sh <model> <task-id>}"
task_id="${2:?usage: ./run.sh <model> <task-id>}"

task_file=$(ls tasks/"${task_id}"-*.md 2>/dev/null | head -1)
[[ -n "$task_file" ]] || { echo "task not found: tasks/${task_id}-*.md" >&2; exit 1; }

mkdir -p outputs
out="outputs/$(date +%Y%m%d)-${model}-${task_id}.md"

# 採点基準はモデルに見せない(タスク本文のみ渡す)
prompt=$(sed '/^## 採点基準/,$d' "$task_file")

claude -p "$prompt" --model "$model" > "$out"
echo "saved: $out"
echo "採点基準: $task_file の「## 採点基準」を見て results.md に記録する"
