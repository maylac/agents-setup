# 有効化計画

以下の操作とコマンドはすべて未実行の提案です。GitHub resource の作成、Cursor CLI の導入と認証、Mac mini の設定書き込み、launchd 登録を一つの確認可能な bundle にし、実行直前に一度だけまとめて承認を求めます。承認対象・許可 repo・戻し方・現在の診断結果を一つの依頼に示します。そこで承認されていない OAuth scope、human 2FA、別 resource、または共有 daemon の再起動が必要になった場合は止め、差分の操作だけ別に判断を求めます。

## 現在確認できた状態（2026-10-25）

- bridge のソースと routing 設定は存在します。
- ローカル bridge→Codex loopback は一度通り、依頼したマーカーファイルを読み戻せています。実際に指定モデルが処理した証明や cloud からの handoff の証明ではありません。
- bridge の env ファイルと launchd 登録は見つかっていません。
- dispatch 用 GitHub repository は現在の `gh` から解決できません。
- Claude と Codex の認証状態はローカルで確認されています。Claude CLI は利用制限中（14:50 JST まで）と報告されました。認証済み状態だけでは実行可能と判断しません。
- Cursor CLI は未導入です。PATH 上の `agent` は Grok Build TUI であり、Cursor CLI として扱いません。
- Grok Bot の GitHub connector、Issue 起票、Mac mini までの実 handoff は未確認です。

現在値を再確認する提案コマンド:

```sh
python3 slack-bridge/doctor.py
python3 slack-bridge/doctor.py --check-github
```

出力は JSON で、secret 値は表示しません。`end_to_end: unknown` は cloud connector と本物の handoff が未検証であることを示します。

## 承認後に実行するコマンド案

### 1. GitHub dispatch repository とラベル

まず読み取り確認を行います。失敗は「存在しない」と決めつけず、認証・権限エラーと not found を分けます。

```sh
command -v gh
gh repo view maylac/agent-tasks --json nameWithOwner,isPrivate
```

repository が not found と確認できた場合にだけ、以下を実行します。これは private repository の作成です。

```sh
gh repo create maylac/agent-tasks --private --description "Private agent task dispatch queue"
gh repo view maylac/agent-tasks --json nameWithOwner,isPrivate
```

不足しているラベルだけを追加し、最後に3つすべての存在を確認します。

```sh
set -euo pipefail
dispatch_repo="maylac/agent-tasks"
existing_labels="$(gh label list -R "$dispatch_repo" --json name --jq '.[].name')"
for label in agent-task needs-approval manual; do
  if ! printf '%s\n' "$existing_labels" | grep -Fxq "$label"; then
    gh label create "$label" -R "$dispatch_repo"
  fi
done
gh label list -R "$dispatch_repo" --json name --jq '.[].name'
```

### 2. ローカル env 候補

許可 repository は canonical `agents-setup` のみです。Vantik production は含めません。以下は shell の変数で実在する絶対パスを作り、展開済みの値を書き込みます。env ファイル自体には `$HOME` や token を保存しません。

```sh
set -eu
repo_root="$(cd "$HOME/workspace/maylac/agents-setup" && pwd -P)"
codex_bin="$(command -v codex)"
test -d "$repo_root"
test -x "$codex_bin"
config_dir="$HOME/.config/slack-bridge"
mkdir -p "$config_dir"
test ! -e "$config_dir/env"
umask 077
set -C
{
  printf 'BRIDGE_TRANSPORT=github\n'
  printf 'BRIDGE_GITHUB_REPO=maylac/agent-tasks\n'
  printf 'BRIDGE_ALLOWED_SENDERS=maylac\n'
  printf 'BRIDGE_ALLOWED_REPOS=%s\n' "$repo_root"
  printf 'BRIDGE_CODEX_BIN=%s\n' "$codex_bin"
  printf 'BRIDGE_CURSOR_ENABLED=0\n'
  printf 'BRIDGE_GROK_ENABLED=0\n'
  printf 'BRIDGE_TASK_TIMEOUT_SECONDS=3600\n'
} > "$config_dir/env"
chmod 600 "$config_dir/env"
```

この候補に GitHub token、Slack token、Cursor API key、その他の secret は含めません。bridge は既存の `gh` login を利用します。

### 3. Cursor CLI 導入と確認

Cursor はこの統合に必要な読み取り専用レビュー route です。CLI の identity、print/text flags、認証、実際の read-only review が確認できるまで route を無効にします。Grok Build の `agent` を代用しません。

Cursor の公式 CLI install URL は [Cursor CLI installation](https://cursor.com/docs/cli/installation) にある `https://cursor.com/install` です。公式 install command は `curl https://cursor.com/install -fsS | bash` ですが、この計画では未実行です。installer 実行前に次で既存ファイルと現在の `agent` を確認します。

```sh
command -v agent || true
cursor_bin="$HOME/.local/bin/agent"
if [ -e "$cursor_bin" ] || [ -L "$cursor_bin" ]; then
  printf 'STOP: install destination already exists: %s\n' "$cursor_bin"
else
  printf 'Install destination is clear: %s\n' "$cursor_bin"
fi
```

install は衝突が無いことを確認した後にだけ、承認済み bundle の一部として行います。PATH 上の `agent` が別製品でも上書きせず、env では検証済みの Cursor 実行ファイルを絶対パスで指定します。公式 Cursor sign-in はローカル CLI の提供する flow を使い、API key を env や Grok Bot に移しません。新しい OAuth scope や human 2FA が必要と表示されたら操作を止め、その内容だけ別に報告します。

```sh
"$HOME/.local/bin/agent" --help
"$HOME/.local/bin/agent" -p "Read-only review: summarize README structure; do not modify files." --output-format text
```

出力で `Cursor CLI` または `Cursor Agent` identity、`-p`、`--output-format`、`text` が確認でき、作業 tree に変更がなく、レビュー結果が得られた後に限り env の `BRIDGE_CURSOR_ENABLED=1` と検証済み binary path を設定します。

headless mode は [公式説明](https://cursor.com/docs/cli/headless) に従い `-p` を使い、`--force` / `--yolo` を付けません。bridge の実行でもこの print-only command を使います。

### 4. plist の materialize と launchd

canonical repo の template から実ユーザーの home path を埋め込んで plist を生成します。`$HOME` はコマンド実行時に展開され、生成物には絶対パスが入ります。

承認済み PR head を main に取り込んだ後、canonical checkout の revision を照合します。placeholder はレビュー時に記録した commit SHA に置き換えます。

```sh
set -eu
repo_root="$(cd "$HOME/workspace/maylac/agents-setup" && pwd -P)"
reviewed_commit="<reviewed-and-approved-commit-sha>"
current_commit="$(git -C "$repo_root" rev-parse HEAD)"
git -C "$repo_root" merge-base --is-ancestor "$reviewed_commit" "$current_commit"
git -C "$repo_root" rev-parse HEAD
```

source revision が期待したレビュー済み変更を含まなければ先に進みません。merge 方法で ancestry が残らない場合は、PR merge 結果との対応を確認したうえで実際の main commit SHA を新たに記録します。

```sh
set -eu
repo_root="$(cd "$HOME/workspace/maylac/agents-setup" && pwd -P)"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.local/state/slack-bridge"
python3 - "$repo_root/launchd/com.maylac.slack-bridge.plist.template" \
  "$HOME/Library/LaunchAgents/com.maylac.slack-bridge.plist" "$HOME" <<'PY'
import plistlib
import sys

source, destination, home = sys.argv[1:]
with open(source, "rb") as file:
    data = plistlib.load(file)

def expand(value):
    if isinstance(value, str):
        return value.replace("$" + "HOME", home)
    if isinstance(value, list):
        return [expand(item) for item in value]
    if isinstance(value, dict):
        return {key: expand(item) for key, item in value.items()}
    return value

with open(destination, "xb") as file:
    plistlib.dump(expand(data), file)
PY
plutil -lint "$HOME/Library/LaunchAgents/com.maylac.slack-bridge.plist"
```

launchd は既に loaded でない場合にだけ bootstrap します。既に loaded のときは状態を読み、再起動や置換をしません。違う revision/config が動いていたらそこで止めて別途報告します。

```sh
service="gui/$(id -u)/com.maylac.slack-bridge"
if launchctl print "$service" >/dev/null 2>&1; then
  printf 'Already loaded; inspect only.\n'
else
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.maylac.slack-bridge.plist"
fi
```

read-only verification は以下です。

```sh
launchctl print "gui/$(id -u)/com.maylac.slack-bridge" | grep state
python3 slack-bridge/doctor.py --check-github
```

### 5. ingress と成果の確認

GitHub ingress の smoke Issue は Dispatcher だけが起票します。最初に `agents-setup` の読み取り確認を行い、次に限定された harmless な成果物マーカーを作る契約を起票します。Issue コメント、PR がある場合の head と checks、実ファイルを確認します。ローカル bridge→Codex loopback は別の確認で、dispatch repo に Issue を作りません。cloud Grok Bot connector と実 handoff の証拠が得られるまで「接続済み」と報告しません。

## ロールバック案

- bridge に task がないことを launchd と bridge worktree の状態で確認します。実行中の agent があれば停止せず、完了を待ちます。task がない場合のみ次の操作で LaunchAgent を unload します。
- private dispatch repository は未処理 Issue と監査履歴を保持するため削除しません。今回追加したラベルのうち、未処理 Issue が使っていないものだけを選び、必要な場合に削除します。
- env と plist は自動削除・上書きしません。後で再有効化する可能性を残し、状態を診断してから手で扱います。

```sh
launchctl print "gui/$(id -u)/com.maylac.slack-bridge"
find "$HOME/.local/state/slack-bridge/worktrees" -mindepth 1 -maxdepth 1 -type d -print
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.maylac.slack-bridge.plist"
gh issue list -R maylac/agent-tasks --state open
# 追加したラベルだけを対象にする場合の形式:
gh label delete "<new-label>" -R maylac/agent-tasks --yes
```

## 完了・公開の境界

plist template と Python ソースは canonical `agents-setup` のレビュー済み commit が main に入った後、その canonical checkout から参照します。feature worktree から暗黙に設定/daemon を有効化しません。この作業の review 対象は確認済みの commit、PR、または現在の成果物です。未マージの変更を main に反映した、あるいは本番で有効になったとは扱いません。Workspace の運用ルールに従い、main への merge はユーザーの返信を待ちます。root が PR と検証を提示し、その返信を得るまで merge/deploy はしません。
