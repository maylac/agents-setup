# Cursor CLIの識別と読み取り専用ルーティング

- 日付: 2026-10-25
- 更新: 2026-11-01
- 領域: agents-setup / Slack bridge
- 種別: debugging

## 問題
ホスト上の `agent` はGrok Build TUIで、Cursor CLI `agent` と名前が重なる。コマンド名や `-p` の存在だけではCursorと確認できず、`-p` 単独は読み取り専用の証拠にもならない。独自routing JSONにCursorを追加すると、事前確認を通らない経路や、Cursorの失敗後に書き込み可能な別エージェントへ進む経路もできていた。

## 試して駄目だった道
- `agent` という名前をCursorの証拠とする: このホストでは同名のGrok Buildだった。
- `-p` の存在、または `--help` が `--mode ask` を表示することだけで読み取り専用を保証する: 前者は書き込み権限を残し、後者は機能の表示であって、任意の実行ファイルがAsk modeを守る証明ではない。
- routing JSONだけでCursorを単独経路にする: `BRIDGE_ROUTING_FILE` の差し替えでポリシー外から経路が追加できる。

## 効いたアプローチ
対話用のレビューhelperは、Cursor CLIの識別とAsk機能の表示をbounded preflightで確かめた後、`--mode ask` を明示して実行する。`--trust` を含む書き込み・権限回避flagは拒否し、`--model` が指定されない場合はCLIの設定済みモデルを使う。bridgeの既存 `BRIDGE_CURSOR_BIN` は `-p BODY --output-format text` を受け取る厳格なadapterで、legacy契約としてadapter自身がAsk modeと `--trust` を付ける。この契約は維持するが、今回のprivate `bridge.run_task` smokeはそのadapterを使わず、新helperを `BRIDGE_CURSOR_BIN` に指定していた。help preflightだけを任意binaryの安全性保証と見なさない。実行前後のroutingもコードで固定し、Cursor契約はCursor単独、他エージェントのfallbackからはCursorを除外する。

## なぜ効いたか
`-p` だけを根拠にせず、対話helper側がAskを明示し、trust overrideを拒否することで実行引数の契約を検証できる。helperの7テストは通過した。初回のfixture smokeとprivate `bridge.run_task` は新helperに残っていた `--trust` を使った成功で、no-override evidenceから除外する。修正後のfixture試行はworkspace trust gateでexit 1となり、期待した引用とmarkerは返らなかったが、fixtureは1ファイルのままでSHA-256も不変だった。既存の設定済みbridge adapterはversion/help/authの確認だけで、成功推論を実行した証拠はない。bridge/doctorのhelp preflightは識別と機能表示を確認するだけで、任意のbinaryがAskを守る保証ではない。

## 関連する可用性判定
実際のClaude終了結果 `You've hit your session limit · resets 2:50pm (Asia/Tokyo)` は、旧regexの `rate limit` / `usage limit` / `resets at` に一致せず、次のCodex経路へ進まなかった。観測済みの `session limit` をrate-limit分類に加え、同じ文面のfakeで通常fallbackとmodel pin時の停止・reset表示を検証する。

## 一般化できる原則
- `-p` やhelp上の機能表示だけで安全性を断定せず、実行経路が要求する安全modeを明示し、権限回避flagを拒否する。
- 同じ実行名を持つ複数ツールがある環境では、実行ファイル名で製品を判定せず、bounded preflightで製品識別と必要機能の表示を検証する。表示は実行時の安全性保証と区別する。
- 分離が安全条件なら、外部routing設定だけに委ねず、dispatch時にも許可された経路を強制する。
