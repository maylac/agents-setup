---
name: kdp-submission-packager
description: Kindle電子書籍のKDP入稿パッケージ(kdp_submission_pack)を集約し、AI利用申告ドラフトと規約チェックリストを作る。Gate 2(人間承認)まで。KDPへのアップロード・出版操作は行わない。
---

# KDP Submission Packager

Kindle出版パイプライン(設計書: `~/tasks/kindle-publishing-pipeline-design.md`)のステージ8(最終)。
KDPの入稿画面で必要な全項目を1ファイルに集約し、規約チェックを通した上でGate 2(人間承認)に渡す。

## Workflow

1. **前提の検証**
   - 全packの `status: ok` を確認する: manuscript_pack(`gate1: approved`)、listing_pack、cover_pack、epub_pack。
   - `human_value_log.md` の存在と内容(Gate 1で人間が何を足したかの記録)を確認する。空ならGate 1に差し戻す。
2. **入稿項目の集約**
   - タイトル/サブタイトル/紹介文/キーワード7枠/カテゴリ(listing_packから)、EPUBパス・表紙パス(epub_pack/cover_packから)、価格・ロイヤリティプラン(70%対象の$2.99〜9.99帯を基本に提案、決定は人間)。
3. **AI利用申告ドラフトの作成**
   - KDPの申告区分に沿って、AIの利用範囲(下書き生成・編集支援)と人間の関与(human_value_log を根拠とした編集・加筆の内容)を明文化する。
   - **申告を回避・軽減する表現を提案しない。** 事実をそのまま書く。
4. **規約チェックリストの実施**
   - 薄いコンテンツ該当性の自己点検(章の厚み・独自性・具体例)。
   - 本文内の外部リンク・誘導のPR表記・規約適合。
   - 紹介文の保証表現・誇大表現の有無。
   - チェック時点の最新KDP規約と突き合わせる(規約は流動的。前回のチェックリストを盲用しない)。
5. **Gate 2への提出**
   - `packs/kdp_submission_pack.yaml` を `approval_required: true` で書き出し、`book.yaml` を `gate2_pending` にする。
   - 人間がチェックリストを承認したら `gate2: approved` を人間が記入し、`status: ready_to_publish` となる。**以降のKDP操作(アップロード・出版ボタン)は人間が実施する。このスキルおよびパイプラインは出版操作を行わない。**

## Output

### packs/kdp_submission_pack.yaml

```yaml
pack: kdp_submission_pack
status: ok
approval_required: true
created_at: <date>
inputs:
  manuscript_ref: manuscript.md          # gate1: approved
  listing_pack_ref: packs/listing_pack.yaml
  cover_pack_ref: packs/cover_pack.yaml
  epub_pack_ref: packs/epub_pack.yaml
  human_value_log_ref: human_value_log.md
submission:
  title: ""
  subtitle: ""
  description: ""
  keywords: ["", "", "", "", "", "", ""]
  categories: ["", ""]
  epub_path: dist/book.epub
  cover_path: cover/cover.png
  price_proposal: {usd: 0.00, royalty_plan: "70%"}   # 決定は人間
ai_disclosure_draft: |
  <AI利用範囲と人間の関与の明文化(human_value_log 根拠)>
compliance_checklist:
  thin_content_self_check: pending    # pending | pass | fail
  external_links_pr_labeling: pending
  no_guarantee_claims: pending
  latest_kdp_policy_reviewed: pending  # チェック日付を併記
gate2: pending                         # approved は人間のみが記入
```

## Decision Rules

- `gate1: approved` と `human_value_log.md` なしでは実行しない。
- AI申告のドラフトは事実ベース。申告回避の提案は禁止。
- チェックリストのいずれかが fail のままGate 2に出さない(該当ステージへ差し戻す)。
- 出版操作・価格の最終決定・アカウント操作はこのスキルの範囲外。
