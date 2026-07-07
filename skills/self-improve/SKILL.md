---
name: self-improve
description: ハーネス自己改善エコシステムの実行手順。週次rot通知への対応、教訓のlint/CLAUDE.md/skill/memoryへの振り分け(distill)、蒸留元台帳の巡回と採否記録(sources)、月次フル監査(full)。「self-improve」「rotレポート対応」「教訓を定着」「蒸留元を巡回」で発火。
---

# self-improve — ハーネス自己改善の実行手順

正本と設計書: `~/workspace/agents-setup/selfimprove/README.md`(以下 `$SI` = そのディレクトリ)。
このスキルはどのモデルでも実行できるよう手順を焼き込んである。判断に迷ったらREADMEの設計原則に戻る。

## モード

引数なし(または `quick`) = **rot対応 + 期限が来たsourcesの巡回**。他に `rot` / `distill` / `sources` / `full`。

## rot — ①腐敗検知への対応

1. `python3 $SI/scripts/rot_check.py` を実行(直近レポートが当日分ならそれを読む)。
2. 各findingを分類して処理する:
   - **機械的に直せる**(リンク切れ・索引もれ・残骸ルール) → その場で修正。ミラー系は `bash ~/.agents/sync-skills.sh` で再同期してから再チェック。
   - **判断が要る**(skill品質・重複疑い) → `skill-stocktake`(skillのみ) か `harness-audit`(横断)に委譲。
   - **陳腐化projectメモリ** → 内容を現状と照合し、上書き更新するか「(superseded, 日付)」を付ける。
3. 修正後に rot_check.py を再実行し、findings が減ったことを確認して報告する。

## distill — ②教訓の定着

入力: `~/tasks/lessons.md` の未処理エントリ、`~/tasks/learnings/` と各repo `docs/learnings/` の新規ノート、直近セッションでのユーザー訂正。

1. 各教訓を **ルーティング表**(README記載。要旨: lint/hook > CLAUDE.md > skill > memory の順に強い。lintにできる教訓をCLAUDE.mdに書かない)で行き先を決める。
2. 行き先に反映する。CLAUDE.md/rulesへ書く場合は既存ルールとの矛盾を先に確認。skill化は `skill-create` を使う。
3. 反映済み・陳腐化したlessonsエントリは `~/tasks/lessons-archive.md` へ移して圧縮する(上限50行。ユーザー指示由来の恒久ルールは解除宣言があるまで残す)。
4. 報告には「何をどこへ定着させ、何を捨てたか」を列挙する。

## sources — ③外部知見の取り込み

1. `$SI/ledger/sources.md` で期限が来た行を確認(rot レポートにも列挙される)。
2. kindに応じて巡回する: x-account/x-search → `opencli twitter tweets/search`、blog → WebFetch/Exa、repo → 上流diff(前回checked以降のコミット/CHANGELOG)。
3. 収穫した知見ごとに採否を判断する:
   - **採用** → ②のルーティング表で行き先に反映し、`adoption-log.md` に「行き先」まで記録。
   - **見送り** → `rejection-log.md` に「理由 + 再評価条件」を記録。**先に既存の rejection-log を検索し、過去に見送った同種の知見の再検討を繰り返さない**(再評価条件が成立した場合のみ再検討)。
4. 巡回した行の `last_checked` を当日に更新。収穫ゼロが3回続いた行は cadence倍増か削除。

## full — 月次フル監査

quick の全手順に加えて: `skill-stocktake`(Full) → 公式 `/fewer-permission-prompts` → distill。
大規模な修正が出たら一括でやらず、hermes のタスクYAMLか別セッションに切り出す。

## 完了条件(全モード共通)

- rot_check.py が実行済みで、対応した findings は再実行で消えている
- 台帳(sources/adoption/rejection)への記録が漏れていない
- 変更は `~/workspace/agents-setup` にコミットされている(ハーネス資産の正本はこのrepo)
