# 有効化の経緯と復旧手順

この文書は、2026-10-25 に実施した有効化の記録と、壊れたときに状態を確認・復旧する手順です。下の「実施済み」の項目は再承認の対象ではありません。ただし、ここに無い新しい権限・OAuth scope・resource・課金や、共有 daemon の再起動が必要になった場合は、その操作だけ人の判断を求めます。

## 実施済み（2026-10-25 の観測順）

1. **以前の状態**: bridge→Codex のローカル loopback が一度通っただけで、env、launchd、dispatch repository、Cursor CLI、Grok Bot の handoff は未整備だった。
2. **PR 16 の merge**: bridge の変更が main に入った（`f6885632d346798c9ac1cba1ecbccce88e84b47b`）。canonical checkout は clean。
3. **dispatch repository**: private `maylac/agent-tasks` がある。
4. **env と launchd**: `~/.config/slack-bridge/env`（権限 600、秘密値なし）と LaunchAgent `com.maylac.slack-bridge` が動いている。bridge が実行してよい repository は `agents-setup` だけ。
5. **Cursor CLI**: 公式 CLI を導入しログイン済み。既存の Grok の `agent` alias を消さないよう、決まったパスに入れた。bridge はローカル wrapper（`~/.config/slack-bridge` 内）を呼び、wrapper は本物の git common dir と新しい bridge worktree のパスを確認してから `--mode ask --trust` だけで実行する。`--force`、yolo、全体 trust は使わない。
6. **Grok Bot の接続**: 既存の[コード屋](https://grok.com/bot/df79e1fb-4c03-497f-811b-4ce9ddd45f2e)の GitHub 接続が既存の許可で動いた。connector から他の repository も見えるが、bridge の許可リストで `agents-setup` 以外は実行しない。
7. **end-to-end smoke**: コード屋が [issue 1](https://github.com/maylac/agent-tasks/issues/1)（Codex Luna）、[issue 2](https://github.com/maylac/agent-tasks/issues/2)（Cursor 読み取り）、[issue 3](https://github.com/maylac/agent-tasks/issues/3)（Claude Opus）を起票し、実際の結果と GitHub を読み戻して元の会話へ報告した。3件とも closed。記録はローカルの `~/tasks/grokbot-integration-20261025/activation-final-receipt.json`。

`doctor.py` の `end_to_end` は実装上 `unknown` のままです。一般的な preflight の結果は、上の独立した smoke 結果を打ち消しません。

8. **コード屋の説明欄**: 常設指示を保存し、開き直して全文一致を確認した。内容はプロンプト上の運用ルールで、システムによる権限の強制ではない。
9. **手動 dashboard**: root が [issue 6](https://github.com/maylac/agent-tasks/issues/6)（ラベル `manual` `ops-hub`、本文に `<!-- grokbot-mission-hub:v1 -->`）を作った。実行用 Issue ではない。自動更新や scheduler は無い。
10. **MissionHub collector**: 読み取り専用の `slack-bridge/mission_hub.py` を追加した。現在 bridge テスト44件が通過（うち MissionHub 新規11件）。これは private queue のその時点の読み取り結果で、常時稼働の monitor や scheduler ではない。使い方は [Bot の役割分担](bot-roles.md#missionhub-collector)。

11. **smoke report の独立照合**: [issue 4 の原文コメント](https://github.com/maylac/agent-tasks/issues/4#issuecomment-6394204858)にある UTF-8 原文を Dispatcher が [issue 7](https://github.com/maylac/agent-tasks/issues/7) の本文へ JSON 文字列でそのまま移し、URL・取得時刻・source head・SHA256 を添えた。受領側でも #4 コメントを GitHub API から読み、デコード後3,551 byteの本文とバイト一致、SHA256 `a6206c53faadb3afbfde073094f7772ff83bd35713bd6bd34799eba70f59e239` を確認した。#4/#5/#7 の worktree はすべて source head `f6885632d346798c9ac1cba1ecbccce88e84b47b` で clean。[#7 の最終 report](https://github.com/maylac/agent-tasks/issues/7#issuecomment-6394276470) は closed / transport `done` / verdict **要修正**。原文搬送の照合は成功したが、原文の案内文に修正点がある。

## 未完了

- **追加の3 Bot**（検品係・運用ハブ・Bot設計係）: 規約同意待ち・未作成。Create Bot 画面が追加の利用規約への同意を求め、その場で人の確認が必要。規約同意への返答はまだない。
- **順番に行う smoke**: [issue 4](https://github.com/maylac/agent-tasks/issues/4)（Claude 作成）は closed。[issue 5](https://github.com/maylac/agent-tasks/issues/5) は closed だが、Codex report は Bridge `done` / agent outcome `BLOCKED`（GitHub の原文に直接接続できず、独立照合は未完）。後続の Dispatcher `VERIFIED:` コメントは部分確認を記録するが、Codex report を成功へ変更した扱いにはしない。

  #4 の原文には5件すべての checks と実出力がある。#5 の依頼本文では `checks` が `[5件: ...]` という無効な JSON へ短縮されていたため、輸送時の要約欠落と作成者レポートの不足を分けて扱う。#7 は #4 原文のバイト一致を確認して closed、transport `done` / verdict **要修正**。#4 の案内文自体は200字を超え（バッククォート込み221字、除外213字）、fallback の条件（route 不可判定時のみ、`model:` / `fallback: off` で route 固定）と Grok CLI の `BRIDGE_GROK_ENABLED=1` 条件を省いている。
- **日次 routine**: 未設定。Skill の有無と scheduler の設定は別の状態として扱い、手作業の成功 → Skill → 実行確認 → schedule → 初回結果の確認の順で進める。
- **全体の検証**: `scripts/validate.sh` は終了コード 1。既存の live parity 11 件（worktree と canonical の symlink 先の不一致10件、Claude RTK PreToolUse hook の欠落1件）。詳細ログはローカルの `~/tasks/grokbot-operations-20261025/full-validation.log`。この live-home 差分は今回の変更で修正していない。
- **code の PR**: default branch への merge は人の承認待ち。

この変更は bridge・harness・実行時の認証・launchd に触れていません。Bot の指示を反映するための再起動や source の有効化は不要です。

## 状態の確認

読み取りだけのコマンドです。出力に秘密値は出ません。

```sh
python3 slack-bridge/doctor.py --check-github
launchctl print "gui/$(id -u)/com.maylac.slack-bridge" | grep state
gh repo view maylac/agent-tasks --json nameWithOwner,isPrivate
gh label list -R maylac/agent-tasks --json name --jq '.[].name'
stat -f '%Lp' "$HOME/.config/slack-bridge/env"
git -C "$HOME/workspace/maylac/agents-setup" status --short
```

期待値: LaunchAgent が running、repository が private、ラベル `agent-task` `needs-approval` `manual` `ops-hub` がある、env の権限が `600`、canonical checkout が clean。queue の一覧は `python3 slack-bridge/mission_hub.py --repo maylac/agent-tasks --format markdown` で読めます（読み取りのみ）。

## 復旧

### ラベルが欠けている

不足しているものだけを作ります。

```sh
set -euo pipefail
dispatch_repo="maylac/agent-tasks"
existing_labels="$(gh label list -R "$dispatch_repo" --json name --jq '.[].name')"
for label in agent-task needs-approval manual ops-hub; do
  if ! printf '%s\n' "$existing_labels" | grep -Fxq "$label"; then
    gh label create "$label" -R "$dispatch_repo"
  fi
done
```

### LaunchAgent が止まっている

既に loaded なら状態を読むだけにし、再起動や置換はしません。違う revision や設定で動いていたら止めて報告します。

```sh
service="gui/$(id -u)/com.maylac.slack-bridge"
if launchctl print "$service" >/dev/null 2>&1; then
  printf 'Already loaded; inspect only.\n'
else
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.maylac.slack-bridge.plist"
fi
```

plist は canonical checkout の `launchd/com.maylac.slack-bridge.plist.template` から作られています。作り直しが必要なときは、既存の plist を上書きせず、まず差分を確認して報告します。

### Cursor の review が失敗する

PATH 上の `agent` は Grok Build の場合があるため、代わりに使いません。wrapper と公式 CLI のパスを確認し、`--force` や yolo を足して回避しません。再ログインに新しい OAuth scope や人の 2FA が必要なら止めて報告します。API key を env や Grok Bot に移しません。

### Grok Bot が Issue を作れない

connector の許可を広げたり作り直したりせず、エラー内容と最後に成功した Issue を添えて報告します。権限の変更は人の判断が必要です。

## 停止（ロールバック）

1. bridge に実行中の task が無いことを確認します。実行中なら止めずに完了を待ちます。
2. task が無いときだけ LaunchAgent を unload します。
3. dispatch repository は Issue と監査履歴を残すため削除しません。env と plist も自動で削除・上書きしません。

```sh
launchctl print "gui/$(id -u)/com.maylac.slack-bridge"
find "$HOME/.local/state/slack-bridge/worktrees" -mindepth 1 -maxdepth 1 -type d -print
gh issue list -R maylac/agent-tasks --state open
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.maylac.slack-bridge.plist"
```

## 引き続き人の判断が必要な操作

default branch への merge、本番 deploy、外部への投稿・送信、購入・課金・チャージ・プラン変更、追加の利用規約への同意、認証情報・アカウント・権限の変更、新しい connector や OAuth scope の追加。実際の課金上限や自動チャージの設定は変更しておらず、ベンダー側で上限が強制されているとは扱いません。Bot のメッセージはこれらの承認になりません。
