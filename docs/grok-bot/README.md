# Grok Bot を司令塔にする — 導入手順書

目的: ChatGPT Dots の代わりに xAI Grok Bot(クラウド常駐)を Dispatcher にし、Grok Bot アプリ(iOS/デスクトップ)を入り口・報告・承認チャネル、GitHub Issue を Mac mini への唯一の指示経路にする。監査の背景は `docs/harness-audit-2026-10-13.md`。

## 0. 前提(2026-10-13 時点の公式情報)

- Grok Bot はアカウントごとに 1 台の共有クラウド PC(ブラウザ・ターミナル・`/workspace`)で動く。**Mac mini 上では動かず、SSH も既定では持たない**。入口は Grok Bot の iOS/Android/デスクトップアプリ、または X でのタグ付け。Slack/Telegram から直接話しかける公式経路はない。
- 連携: GitHub・Notion・Linear(OAuth)、Slack(OAuth。認可画面に "Cursor" と出る報告あり)、Google 系。MCP は公開到達可能なサーバーのみ。
- Grok Build CLI(`grok -p`、SuperGrok / X Premium+ で利用可、2026-05 時点 beta)は同じサブスクを使うコーディングエージェント。bridge では最終手段の route `grok` として扱い、`BRIDGE_GROK_ENABLED=1` で明示的に有効化する(CLI 未導入・フラグ未確認のため既定は無効)。Dispatcher と週次枠を共有する可能性があるので最後尾に置いている。
- 料金: X Premium+ に Grok Bot と SuperGrok が同梱。週次使用量は chat とは別枠で、ブラウザ長時間・多 Bot 会話・曖昧な調査で速く減る。
- 全 Bot が 1 台の PC と認証情報を共有する(トラスト境界は 1 つ)。Mac mini の SSH 鍵や NAS 認証は渡さない。

## 1. 構成

```
iPhone ─ Grok Bot アプリ ─┐
iPhone ─ (任意)Slack #agent-tasks ┤(Slack を使う場合のみ。Bot がルーティンで読む)
                            ▼
              Grok Bot「Dispatcher」(クラウド)
      GitHub connector で <dispatch repo> に Issue 起票(label: agent-task)
                            ▼
   Mac mini: slack-bridge/bridge.py (BRIDGE_TRANSPORT=github, launchd)
      gh で Issue 取得 → worktree 作成 → claude -p / codex exec / agy --print
      → Issue コメント(status / changed files / checks / PR) → close
      Hard Stop なら needs-approval ラベルを付けて open のまま
                            ▼
   Grok Bot ルーティンが Issue コメント・PR・CI を読み #agent-tasks へ要約
```

## 2. ユーザー作業(GUI・OAuth・アカウント操作はすべて人手。Hard Stop)

1. **Bot 機能の確認**: Grok アプリ(iOS)に Bot タブが出ることを確認。出なければ X Premium+ の同梱範囲を再確認。
2. **ディスパッチ用リポジトリ**: `gh repo create maylac/agent-tasks --private` (Issue だけを使う空リポ)。ラベル `agent-task` `needs-approval` `manual` を作成。
3. **Bot 作成**: Grok Bot アプリで「Dispatcher」を作り、`docs/grok-bot/dispatcher-instructions.md` の本文を指示欄に貼る。
4. **Connectors**: GitHub(maylac)。Slack は任意(使うなら `#agent-tasks` を作って Bot を招待)。Notion は必要になってから。
5. **ルーティン**(デスクトップアプリで編集):
   - (Slack を使う場合のみ)`watch-slack` 15 分毎: `#agent-tasks` の未処理メッセージを契約に変換して Issue 起票、スレッドに Issue URL を返信。
   - `collect-results` 15 分毎: `agent-task` で close された Issue と `needs-approval` の Issue を読み、Grok Bot アプリの通知(Slack 利用時は元スレッド)へ 5 行以内で報告。承認が要るものは質問を投げ、返答を Issue コメントに転記。
   - `morning-brief` 毎日 08:00 JST: open Issue / open PR / 直近 24h の CI 失敗 / `https://<vantik host>/health` を 10 行で要約。
6. **bridge 起動**(Mac mini、1 回):

   ```sh
   mkdir -p ~/.config/slack-bridge ~/.local/state/slack-bridge
   cat > ~/.config/slack-bridge/env <<'ENV'
   BRIDGE_TRANSPORT=github
   BRIDGE_GITHUB_REPO=maylac/agent-tasks
   BRIDGE_ALLOWED_SENDERS=maylac
   BRIDGE_ALLOWED_REPOS=$HOME/workspace/maylac/reskilling-os,$HOME/workspace/maylac/agents-setup
   BRIDGE_CODEX_BIN=/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex
   BRIDGE_TASK_TIMEOUT_SECONDS=3600
   ENV
   chmod 600 ~/.config/slack-bridge/env
   sed "s#\$HOME#$HOME#g" ~/workspace/maylac/agents-setup/launchd/com.maylac.slack-bridge.plist.template \
     > ~/Library/LaunchAgents/com.maylac.slack-bridge.plist
   launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.maylac.slack-bridge.plist
   launchctl print "gui/$(id -u)/com.maylac.slack-bridge" | grep state
   ```

   `BRIDGE_ALLOWED_REPOS` の `$HOME` は env ファイルでは展開されないので実パスで書く。
7. **スモーク**: Grok Bot アプリに「agents-setup の README に today の日付を 1 行追記して PR」と書く → Dispatcher が Issue 起票 → bridge が `claude -p` を実行 → Issue コメントと PR → アプリに報告、まで 30 分以内に流れることを確認。
8. **Dots の停止**: 1 週間の並行運用で Dispatcher 側の取りこぼしがなければ、Dots への依頼をやめる。Claude iOS Remote Control から直接触る作業は Issue に `manual` ラベルを付けるか、ディスパッチ対象外のブランチで行う。

## 3. 運用ルール

- 契約の形式と Hard Stop は `~/AGENTS.md` の "Autonomous Operation" と "Autonomy and Hard Stops" に従う。Dispatcher は実装しない。
- 1 Issue = 1 worktree = 1 セッション。長引く作業は分割して再起票する。
- Claude が使えないときは bridge が自動で次の route(`routing.json`)へ回す。全 route が使えない場合のみ `blocked (no route)` で返るので、cooldown 解除後に再起票する。
- bridge・Remote Control ホストの再起動は Hard Stop(走っているエージェントが死ぬ)。

## 4. ロールバック

- bridge 停止: `launchctl bootout "gui/$(id -u)/com.maylac.slack-bridge"`。未処理 Issue は open のまま残る(ラベルを外した後は再実行されないので、再起動後は手で `agent-task` を付け直す)。
- Dispatcher 停止: Grok Bot のルーティンを無効化。Dots に戻す場合は `~/AGENTS.md` の該当節を git で戻す。

## 5. PR の作成

4 本のブランチは 2026-10-14 に origin へ push 済み。`gh pr create` は Remote Control セッションの権限分類で拒否されたため、PR は次のコマンドで作る(stack 順。上から順にマージし、マージ後に次の PR の base を `main` に変える)。この節を直したコミットだけはローカルに残っているので、先に `git -C <worktree> push` する。

```sh
R=maylac/agents-setup
gh pr create -R $R --base main --head snapshot/harness-drift-2026-10 --fill
gh pr create -R $R --base snapshot/harness-drift-2026-10 --head fix/repo-path-and-validate-regex --fill
gh pr create -R $R --base fix/repo-path-and-validate-regex --head docs/harness-audit-2026-10 --fill
gh pr create -R $R --base docs/harness-audit-2026-10 --head feat/slack-bridge-codex --fill
```

GitHub アプリからなら `https://github.com/maylac/agents-setup/pull/new/<branch>` を開けばよい。main checkout をマージ後に追従させる手順は `docs/learnings/2026-10-13-live-config-drift-snapshot.md` の 4。
