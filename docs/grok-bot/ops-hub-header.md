## ⚠ 本人の確認待ち (3)

- **Dispatcher以外の起票が43件ある(#11〜#53、タイトル `[manual]`、`model: gpt-6.1-sol` / `gpt-6-luna` 固定)— 本人の操作か確認が必要**: 起票アカウントは `maylac`、作業ファイルはMac上の `/tmp/claude-501/trap/`。管理範囲の「実行Issueの起票はコード屋だけ」から外れる。特に [#53](https://github.com/maylac/agent-tasks/issues/53) は保留中の reskilling-os の PR #64 の読み取りレビュー(未着手、キュー待ち)。本人の新たな指示によるものなら記録のみでよい。点検では停止・再起票・ラベル変更をしない。
- **#10 の検品結果「要修正」(PR #18 設計書、findings 4件)への対応**: [#10 最終コメント](https://github.com/maylac/agent-tasks/issues/10#issuecomment-6536488576)。finding 1(`LINEAR_API_KEY` が子agent環境に継承)は Dispatcher が実コードで照合済みと記録。設計書の修正契約は未起票で本人判断待ち。PR #18 の merge は本人操作と 2026-10-31 に確認済み。
- 追加Bot「検品係」「運用ハブ」「Bot設計係」3体の作成は、Grok Bot追加利用規約への本人同意が確認できるまで保留(変化なし)。課金・プラン・認証権限は変更しない。

## 管理範囲

- 実行対象: agents-setupのみ。実行Issueの起票はコード屋だけ。
- reskilling-osの過去作業は保留。別Botや定期実行で再開しない。
- このIssueはmanual/ops-hubの一覧で、実行契約ではない。agent-taskを付けない。
- bridgeのdoneはプロセス終了の報告。後続コメントのVERIFIED:/NOT VERIFIEDはDispatcherの記録で、点検は実物(コメント本文、SHA、head、CI)を取り直して確認する。
- 更新が古い、未接続、取得失敗の場合は未更新として扱い、正常とみなさない。started後60分結果なしは停止疑いとして照会し、勝手に再起票しない。
