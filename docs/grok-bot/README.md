# Grok Bot を Dispatcher にする構成

Grok Bot アプリを依頼の入口と報告窓口にし、private の GitHub Issue キュー（`maylac/agent-tasks`）を Mac mini への指示経路にします。Bot ごとの役割は [Bot の役割分担](bot-roles.md) にまとめています。

## 使い方

1. Grok Bot の「コード屋」に、やりたいことを普通の文章で送る。
2. コード屋が Issue を作り、Mac mini の bridge が Claude / Codex / Cursor に処理させる。
3. コード屋が GitHub と成果物を開き直して確認し、元の会話に5行以内で報告する。

正常に終わったものは短い完了報告だけが届きます（Grok や GitHub の通知設定は変えていません）。返事が必要なのは、人の判断待ちとエラーのときだけです。Bot のメッセージは承認になりません。merge・本番 deploy・外部への投稿・購入や課金・認証情報の変更は、あなたの返信が必要です。

## 確認済みの経緯（2026-10-25）

1. PR 16 が main に merge された（`f6885632d346798c9ac1cba1ecbccce88e84b47b`）。canonical checkout は clean。
2. private の `maylac/agent-tasks` があり、bridge の env（権限 600）と launchd の `com.maylac.slack-bridge` が動いている。
3. Cursor 公式 CLI を導入しログインした。既存の Grok の `agent` alias は消さずに、決まったパスへ入れた。bridge からは `~/.config/slack-bridge` のローカル wrapper 経由で呼び、本物の git common dir と新しい bridge worktree のパスを確認し、`--mode ask --trust` だけで実行する（`--force` / yolo / 全体 trust は使わない）。
4. 既存の[コード屋](https://grok.com/bot/df79e1fb-4c03-497f-811b-4ce9ddd45f2e)の GitHub 接続は既存の許可で動く。connector からは他の repository も見えるが、bridge が実行してよいのは `agents-setup` だけ。
5. コード屋が [issue 1](https://github.com/maylac/agent-tasks/issues/1)（Codex Luna）、[issue 2](https://github.com/maylac/agent-tasks/issues/2)（Cursor 読み取り）、[issue 3](https://github.com/maylac/agent-tasks/issues/3)（Claude Opus）を起票し、実際の結果と GitHub を読み戻して元の会話へ報告した。3件とも closed。記録はローカルの `~/tasks/grokbot-integration-20261025/activation-final-receipt.json`。

`python3 slack-bridge/doctor.py` は実装上 `end_to_end: unknown` のままです。この表示は上の独立した smoke 結果を否定しません。

6. コード屋の説明欄に常設指示を保存し、開き直して全文一致を確認した（プロンプト上の運用ルールで、システムによる権限の強制ではない）。
7. root が手動 dashboard [issue 6](https://github.com/maylac/agent-tasks/issues/6)（`manual` `ops-hub`）を作った。実行用 Issue ではない。2026-10-25 に root が UI を開き直し、本文が最新の手動 snapshot、ラベルが `manual` と `ops-hub` であることを確認した。
8. 読み取り専用の collector `python3 slack-bridge/mission_hub.py --repo maylac/agent-tasks --format markdown`（または `--format json`）を追加した。

9. [issue 4 の最終コメント](https://github.com/maylac/agent-tasks/issues/4#issuecomment-6394204858)には Claude の全5 checks と各出力がある。引き継ぎ後の [issue 5 本文](https://github.com/maylac/agent-tasks/issues/5)では checks が `[5件: ...]` に縮められ、JSONとして読めない。これは転送時の情報欠落で、Claude の原文に checks が無かったわけではない。Claude の下書きは約190字という見出しに反して、バッククォート込み221字（除外213字）で、200字を超える。また fallback が route 不可時だけ動く条件、`model:` / `fallback: off` による固定、Grok の `BRIDGE_GROK_ENABLED=1` 条件を省いているため、内容は要修正。
10. issue 5 は closed だが、Codex の最終 report は `done` / agent outcome `BLOCKED`（GitHub 上の独立照合未完）。後の Dispatcher `VERIFIED:` comment は一部確認の記録であり、Codex の report を成功へ変更した扱いにはしない。[issue 7](https://github.com/maylac/agent-tasks/issues/7) の本文には issue 4 の原文を JSON 文字列でそのまま運び、UTF-8 SHA256 `a6206c53faadb3afbfde073094f7772ff83bd35713bd6bd34799eba70f59e239` と source head `f6885632d346798c9ac1cba1ecbccce88e84b47b` を添えた。独立照合で #4 の原文とバイト一致し、#4/#5/#7 の worktree はすべて同じ source head で clean。[issue 7 の最終 report](https://github.com/maylac/agent-tasks/issues/7#issuecomment-6394276470) は closed / transport `done` / verdict `要修正`。本文の raw artifact 搬送は確認済みだが、案内文の修正は必要。

未完了: 検品係・運用ハブ・Bot設計係は追加規約への同意待ちで未作成です。コード屋の status-only Skill は保存・readback が報告され、実行効果を別途確認済みです。日次 routine「Maylac 開発運用点検」は登録・有効化され、issue 6 の本文だけを更新する設定です。root が Runs を開いた時点では実行履歴がなく、初回 scheduled callback は未確認です。初回 scheduled callback の一回限りの確認も予約済みです。issue 5 は closed / agent BLOCKED、issue 7 は closed / 要修正で、下書き案に指摘された不足が残っています。料金上限・自動チャージも変更していません。詳細は [Bot の役割分担](bot-roles.md) を見てください。

## 役割

| 役割 | 担当 |
|---|---|
| コード屋 / Dispatcher | 依頼を Issue 契約にし、結果を実物で確認して報告する。自分で実装しない。新しい `agent-task` Issue を作れるのはこの Bot だけ。 |
| Claude Code | 通常の実装・修正・調査。model を省略すると Opus → Sonnet → Codex Luna の順に切り替わる。Grok CLI は無効なので除外される。 |
| Codex | Claude が使えないときの実装、または読み取り専用のレビュー（`gpt-6-luna` 固定）。 |
| Cursor CLI | 明示的に指定したときだけの読み取り専用レビュー。編集は頼まない。 |

大事な成果物は、作った harness とは別の harness がレビューします。自己採点はしません。最終統合は root が行います。root や手動のダッシュボードは実行タスクではありません。

## 契約例

本文の先頭は機械判読できるヘッダーです。行末コメントを付けず、空行の後に依頼本文を置きます。

```text
agent: claude
repo: /Users/<user>/workspace/maylac/agents-setup

Goal: README のリンク切れを修正する。
Owned files: README.md
Acceptance:
  - test -s README.md が終了コード 0
  - git diff --check が終了コード 0
Time budget: 30m
Assumptions: リンク先の内容は変更しない。
Report: status、変更ファイル、各チェック結果、PR URL、未解決事項を5行以内で記録する。
```

通常は `model:` 行と `fallback:` 行を書きません。`model:` や `fallback: off` を明示した場合はその route だけを使います。

## 結果の判定

Bridge の `done` は実行プロセスの結果です。MissionHub は最新の done コメントで、コードフェンス出力の先頭行にある明示的な `status: blocked|failed|needs-approval` または `**状態: ...**` も別の `agent_outcome` として表示します。たとえば `done (agent blocked)` は注意対象で、完了成功とは読みません。`VERIFIED:` は後続のトップレベルコメントに記録されたことだけを示し、コメント作成者や独立検証を collector が認証するものではありません。PR があれば head revision・必須 check・変更内容を、成果物があればリンク先の中身を開き直して確認します。証拠が足りなければ追加確認を一度だけ起票し、それでも不明なら blocked と報告します。

## 安全

Grok Bot は Bot 同士で同じクラウド PC とブラウザを共有します。これは Bot ごとのセキュリティ境界になりません。Mac mini の SSH 鍵、NAS 認証情報、API key などの秘密はクラウドへ移しません。

## 関連文書

- [Bot の役割分担](bot-roles.md): 4つの Bot、引き継ぎ形式、`VERIFIED:` の記録、運用ハブ、collector、投稿の7項目との対応。
- [Dispatcher instructions](dispatcher-instructions.md): コード屋の説明欄に入れる指示。
- [有効化の経緯と復旧手順](activation-plan.md): 実施済みの手順と、壊れたときの戻し方。
- 参考にした運用例: [dansyu_callenge の投稿](https://x.com/dansyu_callenge/status/2114110194963841236)
- 製品仕様: [Grok Bot](https://cursor.com/docs/grok-bot)、[Cursor CLI headless mode](https://cursor.com/docs/cli/headless)、[xAI changelog](https://x.ai/changelog/bot)
