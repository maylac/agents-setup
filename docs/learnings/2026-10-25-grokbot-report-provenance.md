# GitHubキューの完了報告と実行結果を分けて読む

- 日付: 2026-10-25
- 領域: agents-setup / slack-bridge Mission Hub
- 種別: debugging

## 問題

Bridgeは実行プロセスの結果をコメント冒頭に `done` と記録し、その後ろのコードフェンスにエージェント出力を入れる。このため、プロセス終了コードが0でも、出力上の作業結果が `BLOCKED` になり得る。また、Dispatcherの後続確認とエージェント自身の文章を混同してはいけない。

## 試して駄目だった道

- コメント内の全行から `VERIFIED:` を探すと、フェンス内のエージェント出力や引用文をDispatcher確認として誤読する。
- `done` と同時刻の確認コメントを受理すると、done後に記録された確認か判定できない。
- Bridgeの `done` だけでタスク完了とすると、issue #5のように終了コード0でも本文が `**状態: BLOCKED**` の結果を見落とす。
- 記録された `VERIFIED:` を独立に認証済みと表示すると、キューのスナップショットが示す範囲を超える。

## 効いたアプローチ

- Bridge状態はコメントの先頭の非空行から読む。実行結果は最新の `done` コメントにある最初のコードフェンスだけを確認し、先頭の非空行が `status: blocked|failed|needs-approval` または `**状態: BLOCKED|FAILED|NEEDS-APPROVAL**` の場合だけ `agent_outcome` として別記する。
- `status` はBridge結果、`agent_outcome` は明示された作業結果として保持する。Bridgeが `done` でも、後者がblocked/failedなら注意対象に残す。後のDispatcher確認コメントでは消えず、後続の実際の最終実行報告で更新する。
- `VERIFIED:` は `done` より後の別コメントで、最初の非空行がマーカーの場合だけ `dispatcher-recorded` と記録する。コメントの作成者を独立に認証したとは表示しない。
- 完了状態の契約に報告がなければ `unknown` として注意対象に出す。入力JSONは集計・Markdown描画の前に形を検証し、null URLはリンクにせずラベルとして表示する。
- reviewer が source host に接続できない場合、Dispatcher が原文コメントを省略せずJSON文字列で運び、URL・comment ID・updatedAt・取得時刻・source head・UTF-8 byte数・SHA256を添える。受領側は取得可能な原文とのバイト一致を検証し、check一覧の要約転送で証拠を失わない。

## なぜ効いたか

Bridgeの先頭行とフェンスが二種類の状態の境界を作るため、輸送プロセスの終了とエージェントの結果を別々に追える。確認マーカーはコメント境界と時刻で順序付け、表示名はスナップショットが示す証拠の強さに留める。原文を直接取得できないreviewerには、要約ではなく証拠本文とハッシュを運び、受領側で照合すれば本文の欠落と作成者の不備を分けられる。根拠: issue #5 の `done` comment は fenced stdout 先頭が `**状態: BLOCKED**`。issue #7 は #4 原文3,551 UTF-8 byteをJSON搬送し、受領側でSHA256 `a6206c53faadb3afbfde073094f7772ff83bd35713bd6bd34799eba70f59e239` とバイト一致を確認。#4/#5/#7 worktree は source head `f6885632d346798c9ac1cba1ecbccce88e84b47b` で clean。Mission Hub 11テスト、bridgeテスト全体44件が通過した。

## 一般化できる原則

- プロセス終了と作業結果が別に報告される場合、両方を保存し、どちらかで他方を上書きしない。
- 埋め込み出力の制御マーカーは、決められた境界と位置でのみ解釈する。
- スナップショットで観測したマーカーは「記録された」と表し、データが示さない作成者確認まで主張しない。
