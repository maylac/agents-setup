# Cursor CLIの識別と読み取り専用ルーティング

- 日付: 2026-10-25
- 領域: agents-setup / Slack bridge
- 種別: debugging

## 問題
ホスト上の `agent` はGrok Build TUIで、Cursor CLI `agent` と名前が重なる。既定の `cursor-agent` は見つからず、コマンド名や `-p` の存在だけではCursorと確認できない。また、独自routing JSONにCursorを追加すると、事前確認を通らない経路や、Cursorの失敗後に書き込み可能な別エージェントへ進む経路ができていた。

## 試して駄目だった道
- `agent` という名前をCursorの証拠とする: このホストでは同名のGrok Buildだった。
- routing JSONだけでCursorを単独経路にする: `BRIDGE_ROUTING_FILE` の差し替えでポリシー外から経路が追加できる。

## 効いたアプローチ
既定バイナリを `cursor-agent` とし、明示ゲートが有効なときだけ、worktree作成前に10秒制限で `--help` を実行する。出力にCursor CLI/Agentの識別と `-p`、`--output-format`、text形式を要求する。タスクは `-p ... --output-format text` で実行し、`--force`等を付けない。実行前後のroutingもコードで固定し、Cursor契約はCursor単独、他エージェントのfallbackからはCursorを除外する。

## なぜ効いたか
CLIの名前ではなく、実行ファイル自身の識別情報と必要な引数機能を確認し、設定ファイルが変わっても読み取り専用ルートの制約をコードで保つため。fake executableを使ったbridge/doctorの全33テストで経路と拒否条件を確認した。実Cursor推論は実行していないため、接続や稼働の証明ではない。

## 関連する可用性判定
実際のClaude終了結果 `You've hit your session limit · resets 2:50pm (Asia/Tokyo)` は、旧regexの `rate limit` / `usage limit` / `resets at` に一致せず、次のCodex経路へ進まなかった。観測済みの `session limit` をrate-limit分類に加え、同じ文面のfakeで通常fallbackとmodel pin時の停止・reset表示を検証する。

## 一般化できる原則
- 同じ実行名を持つ複数ツールがある環境では、実行ファイル名で製品を判定せず、bounded preflightで製品識別と必要機能を検証する。
- 分離が安全条件なら、外部routing設定だけに委ねず、dispatch時にも許可された経路を強制する。
