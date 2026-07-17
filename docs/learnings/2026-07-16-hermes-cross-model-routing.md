# Hermesの方針文だけではAntigravity委任を保証できない

- 日付: 2026-07-16
- 領域: agents-setup / Hermes model routing
- 種別: architecture

## 問題
Hermesの親モデルをSOLに保ちつつ、実作業をAntigravityへ優先委任する方針が`AGENTS.md`に存在したが、実利用はSOLに偏っていた。Hermes標準の`delegate_task`は単一の設定済みモデル（この環境ではTerra）に固定され、Antigravityはネイティブ委任先ではない。Fableレビューも実行済みだったが、呼び出しモデルの証跡が完了報告に出ず、未実行に見えた。

## 試して駄目だった道
- 方針文の強化だけ: 既に「Antigravity優先」「SOL親は実装しない」と明記済みでも、`agy`を明示起動しなければ経路は切り替わらなかった。
- `delegation.model`の変更: `delegate_task`全体を別OpenAI互換モデルへ固定する設定であり、Antigravity CLIやFableの役割別ルーティングを表現できない。
- 稼働中Gatewayからの自己restart: Hermesが親GatewayをSIGTERMで巻き込むため、CLIがfail-closedで拒否した。

## 効いたアプローチ
ユーザープラグイン`~/.hermes/plugins/cross-model-router/`を追加し、モデルに直接見える2ツールを登録した。

- `antigravity_delegate`: 許可したGeminiモデルを明示指定して`agy --print`を実行。
- `fable_review`: advisor/verifier役を選び、`claude --model fable`を明示実行。失敗時は別モデルへ黙ってフォールバックしない。
- 両経路ともプロンプトを含まないJSONL監査証跡を`~/.hermes/logs/model-routing.jsonl`へ残す。
- 非自明タスクの完了報告では非SOL routing receiptまたは具体的な例外理由を要求する。

## なぜ効いたか
モデル選択を自然言語上の希望から、引数enum・固定CLI引数・終了コード・監査receiptを持つ実行可能なツール契約へ変えたため。Hermesのfresh CLI E2Eで`antigravity_delegate`から`Gemini 3.5 Flash (Low)`へ配車し`HERMES_PLUGIN_ROUTE_OK`を取得した。Fable smoke testのClaude transcriptには`message.model: claude-fable-5`が記録された。

## 一般化できる原則
- ルーティング方針は、モデル固定の実行経路と検証可能なreceiptがなければ強制ではない。
- 外部ハーネスは汎用subagent設定へ押し込まず、専用の明示モデル付きadapter/toolとして露出する。
- 「高位モデルでレビュー済み」という主張は、コマンド引数だけでなく生成側transcriptの実model fieldでも確認する。
