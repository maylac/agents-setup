# Grok Bot の役割分担

## 現行の構成

| 役割 | 担当 | 境界 |
|---|---|---|
| 依頼の受付、契約起票、結果報告 | Grok Bot コード屋（Dispatcher） | 作業 Issue の controller は一つ。新しい `agent-task` Issue を作成できるのは Dispatcher だけ |
| 実装・修正・調査 | Mac mini 上の Claude Code、Codex、または指定された agent | bridge が作業し、agent は `gh` を使わず Issue を書き換えない |
| queue の定期集計と issue 6 更新 | Mac mini の publisher | 決定的な処理。Bot は更新済み issue 6 を読むだけ |
| 独立レビュー、承認案内 | Claude Duet と GitHub Mobile | Duet は下書き・通知まで。承認コメントは本人が GitHub Mobile から書く |
| 個人用件 | Muse | 開発制御系の起票・承認に参加しない |

追加の「検品係」「運用ハブ」「Bot設計係」3体を作る計画は取り下げます。Claude Duet が依頼時の独立レビューと承認案内を行い、Mac publisher が issue 6 を更新します。Grok は一体の Dispatcher として維持します。

## Issue 6 の読み取り専用 routine

定期 routine「Maylac 開発運用点検」は issue 6 を読み、判断待ち・異常・実行中の差分を短く報告します。issue 6 の本文・コメント・ラベルを作成または変更してはいけません。publisher が本文を管理します。queue が読めない場合は推測せず、読み取り失敗を報告します。

## Bot 間の引き継ぎ

引き継ぎメッセージには source Issue/comment の URL と原文コメントの UTF-8 SHA256 のみを含めます。コメント本文をコピー、要約、JSON 格納して Bot 間で運びません。bridge が URL から原文を取得して SHA256 を照合し、契約末尾に正確な原文を添付します。agent は `gh` で原文を取得しません。

```text
source: <comment URL> sha256:<UTF-8 SHA256 hex>
```

## 承認

Bot は `APPROVED:` コメントを書いたり、本人の返答を代筆・転記したりしません。Duet や Grok は対象 Issue の URL と貼り付ける文面案を通知するだけです。本人が GitHub Mobile から対象 Issue に `APPROVED: <正確な操作>` とコメントし、bridge は本人の login によるコメントだけを承認とします。Bot の投稿は承認として扱いません。
