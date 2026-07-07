#!/bin/zsh
# selfimprove 週次rot checkのlaunchdジョブを登録する。
# テンプレートの __HOME__ を実ホームにレンダリングして ~/Library/LaunchAgents へ配置・ロード。
set -eu

SELFIMPROVE="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.maylac.selfimprove-rot"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/.claude/logs"
sed "s|__HOME__|$HOME|g" "$SELFIMPROVE/launchd/$LABEL.plist.template" > "$DEST"
plutil -lint "$DEST"
launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"
launchctl list | grep "$LABEL" && echo "installed: $DEST (毎週月曜08:30)"
