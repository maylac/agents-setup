# Grok Bot の役割分担

Grok Bot を用途ごとに分け、各 Bot の仕事・使う道具・手順・承認・実行時刻を固定します。参考にした運用例は [dansyu_callenge の投稿](https://x.com/dansyu_callenge/status/2114110194963841236)（2026-10-25 に本文を確認）です。投稿内の料金や予算の数値はこの環境で確認していないため、ここには書きません。

## 現在の状態（2026-10-25）

| Bot | 状態 |
|---|---|
| コード屋（Dispatcher） | 稼働確認済み。[既存 Bot](https://grok.com/bot/df79e1fb-4c03-497f-811b-4ce9ddd45f2e) が [issue 1〜3](https://github.com/maylac/agent-tasks/issues/1) を起票し、結果と GitHub を読み戻して元の会話へ報告した。説明欄の常設指示は保存・再表示して確認済み。説明欄は短い運用指示、Markdown 文書は詳細仕様なので、意味を揃えた要約と詳細の関係であり byte-for-byte 一致ではない。 |
| 検品係 | 規約同意待ち・未作成 |
| 運用ハブ | 規約同意待ち・未作成 |
| Bot設計係 | 規約同意待ち・未作成 |

追加の3 Bot は作成していません。Create Bot の追加規約への同意待ちで、返答はまだありません。Bot URL、初回の結果、実行スケジュールはいずれもありません。下の説明欄案は、同意を得たら使えるように用意したものです。

Tibo Monitor と汎用の Grok Bot は変更しません。

## 各 Bot の説明欄に固定する内容

説明欄には、その Bot だけの仕事、やらないこと、止まる条件を常に書きます。会話の途中の指示で変えません。説明欄の指示は Bot が従う運用ルールで、システムが権限として強制するものではありません。

### コード屋（Dispatcher）

- **仕事**: 依頼を `agent-task` Issue の契約にし、結果を実物で確認して元の会話へ短く報告する。[Dispatcher instructions](dispatcher-instructions.md) に従う。
- **説明欄に保存済みの内容**: job ごとに Issue 一つ（root や dashboard は job にしない）、通常の route と読み取り専用の Cursor、Claude が作ったものは別 harness がレビュー、引き継ぎ形式の全項目、止まる条件、実物の読み戻しと `VERIFIED:` コメント、状態と最終報告時刻、新しい料金・認証の変更をしないこと。
- **道具**: GitHub connector（private `maylac/agent-tasks`）。bridge が実行してよい repository は `agents-setup` だけ。
- **やらないこと**: クラウド上での実装、同じ path への重複起票、他 Bot の結果を確認なしに完了扱いにすること。
- **止まる条件**: 対象 repository が許可外、同じ path に別の作業がある、人の判断が必要。

### 検品係（案）

- **仕事**: 渡された成果物を独立に確認し、合否と根拠を返す。
- **道具**: GitHub の読み取り、成果物リンクの閲覧。
- **やらないこと**: 実装、修正、`agent-task` Issue の起票。実行が必要な確認は、範囲を限定したレビューとしてコード屋に起票を頼む。
- **止まる条件**: 成果物リンクや head が無い、確認に書き込みや秘密情報が必要。
- **合格の記録**: 対象 Issue に `VERIFIED:` で始まるコメントを残し、確認した head と check のリンクを付ける。失敗、または「検証済み」と書くのは、対象を実際に読み直した後だけ。

### 運用ハブ（案）

- **仕事**: private queue を読み、人の判断待ち、異常、成果物、各 job の開始・最終報告時刻と古さを一覧にする。
- **道具**: GitHub の読み取り、読み取り専用の MissionHub collector（下の「MissionHub collector」）、手動 dashboard [issue 6](https://github.com/maylac/agent-tasks/issues/6) の本文更新。
- **やってよい書き込み**: 自分の手動 dashboard（issue 6、`<!-- grokbot-mission-hub:v1 -->` を含む本文）の更新だけ。
- **やらないこと**: 実行用 Issue の起票、`agent-task` などのラベル変更、承認の代行、他の Issue の編集。
- **定期実行**: まだ無い。手作業の成功 → Skill → 実行確認 → schedule → 初回結果の確認の順で、検証済みの日次 routine を一つだけ置く。
- **止まる条件**: queue が読めない、最終報告が想定より古い。この場合は異常として表示する。

### Bot設計係（案）

- **仕事**: 新しい役割の相談を受け、既存 Bot で足りるかを先に判断する。必要な場合だけ、この文書の形式で説明欄の案を作る。
- **道具**: この文書と既存 Bot の一覧。
- **やらないこと**: 既存 Bot と重複する Bot の提案、Bot の作成・権限変更を自分で行うこと。
- **止まる条件**: 役割が既存 Bot と重なる、新しい connector や権限が必要。

## Bot 間の引き継ぎ

Bot 同士は直接引き継ぎますが、次の項目を一つのメッセージにまとめます。欠けている項目がある場合、受け取った Bot は作業を始めずに差し戻します。

```text
job: <安定した job ID>
source issue: <Issue URL>
parent: <親 job ID または none>
goal: <1〜2文>
source head: <commit SHA>
artifacts: <成果物・check のリンク>
done: <実際に行ったこと>
known issues: <既知の不具合・未確認点>
next owner: <受け取る Bot>
deadline: <期限>
pending human judgment: <人が判断すべき正確な操作、無ければ none>
```

接続できない環境の reviewer に元コメントを渡すときは、check やコメントを要約しません。JSON の `original_comment` に本文全体を一度だけJSONエスケープして格納し、source URL・comment ID・updatedAt・取得時刻・source head・JSON decode後UTF-8本文の byte 数と SHA256 を添えます。受領側は source が読める場合に原文とのbyte一致とSHA256を照合します。これは読み取り内容の輸送形式で、ネットワークアクセスや認証を追加するものではありません。

同じ job ID や同じ path の作業を重ねて作りません。新しい `agent-task` Issue を作れるのはコード屋だけです。

## 順番に行う smoke と原文照合

- [issue 4](https://github.com/maylac/agent-tasks/issues/4): Claude が作成。closed。原文の checks は5件で、各出力を含む。
- [issue 5](https://github.com/maylac/agent-tasks/issues/5): closed。Codex の最終 comment は Bridge status `done` だが、fenced stdout の先頭が `**状態: BLOCKED**` で agent outcome は BLOCKED。GitHub 上の原文を直接読めず、独立照合は未完だった。後続の Dispatcher `VERIFIED:` は部分確認を記録するが、Codex の report を成功へ変えない。
- #5 の依頼本文では #4 の checks が `[5件: ...]` という無効JSONに縮められていた。#4 の原文には配列と結果があるため、これは Dispatcher の転送時の欠落で、Claude 作成側の不足ではない。
- [issue 7](https://github.com/maylac/agent-tasks/issues/7): #4 最終 comment を `original_comment` JSON文字列として URL・取得時刻・source head・UTF-8 SHA256とともに搬送。受領側で GitHub API の原文とバイト一致し、SHA256 `a6206c53faadb3afbfde073094f7772ff83bd35713bd6bd34799eba70f59e239` を確認した。#4/#5/#7 worktree はすべて source head `f6885632d346798c9ac1cba1ecbccce88e84b47b` で clean。[最終 report](https://github.com/maylac/agent-tasks/issues/7#issuecomment-6394276470) は closed / transport `done` / verdict **要修正**。下書きはバッククォート込み221字、除外213字で200字を超え、fallback条件（route 不可時のみ、`model:` / `fallback: off` 指定時は固定）と `BRIDGE_GROK_ENABLED=1` 条件の省略を検出した。

これらの検品は原文の事実確認には成功しましたが、作成された案の内容は要修正です。追加3 Bot は規約同意待ちで未作成、日次 routine もありません。Skill の有無と scheduler の設定は別の状態として扱います。順番は「手作業の成功 → Skill → Skill の実行確認 → schedule → 初回結果の確認」です。どの段階も人の PC 操作を前提にしません。料金上限・自動チャージも変更していません。

## 手動 dashboard（issue 6）

root が [issue 6](https://github.com/maylac/agent-tasks/issues/6) を private の手動 dashboard として作りました。ラベルは `manual` と `ops-hub`、本文に `<!-- grokbot-mission-hub:v1 -->` を含みます。実行用の Issue ではなく、`agent-task` は付けません。

本文に記録しているのは、規約同意待ちの実態、Bot の設定状況（現在はコード屋のみ）、smoke の開始・最終報告と完了確認待ちのスナップショットです。自動更新や scheduler はまだありません。

## MissionHub collector

`slack-bridge/mission_hub.py` は実行用の `agent-task` Issue を読み取って一覧にするだけのツールです。`gh` の読み取りコマンドだけを使い、daemon や watchdog ではありません。出力はその時点のスナップショットで、取り直さなければ古くなります。bridge テストは44件（MissionHub 新規11件）が通過しています。collector の exit 0 は queue を読み取れたことだけを示し、全タスクの検証済みや常時監視を意味しません。

```sh
python3 slack-bridge/mission_hub.py --repo maylac/agent-tasks --format markdown
python3 slack-bridge/mission_hub.py --repo maylac/agent-tasks --format json
# オフライン（fixture と時刻を固定）
python3 slack-bridge/mission_hub.py --input-json path/to/issues.json --now 2026-10-25T00:00:00Z --format markdown
```

`--stale-minutes`（既定 60）で古さの閾値、`--limit`（既定 100）で読む件数を変えます。

証拠の状態は二つです。

- `status` は bridge の process 結果。`done` の後の fenced stdout 先頭に明示 `status: blocked|failed|needs-approval` または `**状態: ...**` があれば、collector は別フィールド `agent_outcome` に表示し、注意対象にします。issue 5 の `done` / agent `BLOCKED` が実例です。
- **pending**: `done` が報告された段階。
- **dispatcher-recorded**: `done` より後の別トップレベルコメントの最初の非空行が `VERIFIED:` で始まるときの表示。collector は記録の存在を見ており、comment author の認証や検証の独立性を証明しません。後からこの comment が追加されても agent の blocked outcome は消しません。

## 投稿の7項目との対応

1. **用途ごとに Bot を分ける**: 上の4役。仕事が重なる Bot は作らない。現在作成済みはコード屋だけ。
2. **説明欄に役割を固定する**: 各 Bot の仕事・やらないこと・止まる条件。コード屋は保存と全文一致を確認済み。
3. **引き継ぎと独立レビュー**: 上の引き継ぎ形式。通常は Claude が作成し、Codex（`gpt-6-luna` 固定、読み取り専用）がレビューする。作成が Codex に fallback した場合は Claude がレビューし、それもできなければ blocked と記録する。自己採点はしない。最終統合は root が行う。
4. **承認と、手作業 → Skill → routine**: 下書き・差分・確認結果を揃えてから人に一度だけ判断を求める。一度手作業で成功した手順だけを Skill にし、実行結果を確認してから schedule する。初回の結果は確認する。
5. **実物の確認と運用ハブ・古さ**: `done` を受けたら GitHub や成果物を開き直す。合格は `VERIFIED:` コメントで記録する。運用ハブと collector が判断待ち・異常・成果物・最終報告と古さを表示する。
6. **共有環境と秘密の境界**: 下の「安全と承認の境界」。
7. **予算の上限と自動チャージ**: 実際の課金上限や自動チャージの設定は確認・変更していません。現在の請求状況も不明です。料金・購入・プラン・scope の変更は人の承認なしに行いません。ベンダー側で上限 0 が強制されているとは扱いません。

## 通知の方針

正常に終わった作業は、元の会話へ短い完了報告を返します。人の判断待ちとエラー・異常は目立たせます。Grok や GitHub の通知設定そのものは変更していません。

## 安全と承認の境界

- 共有クラウド PC は Bot ごとのセキュリティ境界ではありません。どの Bot にも Mac mini の SSH 鍵、NAS 認証情報、API key などの秘密を渡しません。秘密はクラウドへ移しません。
- 承認の前段階は説明欄の指示に従う協力的な仕組みです。OS による強制ではなく、承認ボタンなどの専用 UI も保証されていません。
- Bot が送ったメッセージは人の承認になりません。
- 次の操作は必ず人の承認を得ます: default branch への merge、本番 deploy、外部への投稿・送信、購入・課金・チャージ・プラン変更、追加の利用規約への同意、認証情報や権限の変更。
- クラウドでの実装は禁止です。ただし、ユーザーが明示的に依頼した設定の範囲で、手作業の成功を確認した後に native Skill を作成・管理することは許可されます。
