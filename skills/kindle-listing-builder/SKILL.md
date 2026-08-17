---
name: kindle-listing-builder
description: Kindle電子書籍のタイトル・サブタイトル・紹介文・検索キーワード・カテゴリ案(listing_pack)を作る。本文執筆にはkindle-chapter-writer、入稿パッケージにはkdp-submission-packagerを使う。
---

# Kindle Listing Builder

Kindle出版パイプライン(設計書: `~/tasks/kindle-publishing-pipeline-design.md`)のステージ5。
クリックされるタイトルと購入につながる商品ページ文面を作る。

## Workflow

1. **前提の検証**
   - `book.yaml` の `stages.gate1.status: approved` を確認する。**Gate 1未承認の原稿ではこのステージを実行しない**(差し戻す)。
   - `packs/book_brief.yaml` と `manuscript.md`(人間の価値付加済み)を読む。
2. **タイトル案**
   - タイトル+サブタイトル案×5。各案に「狙い(検索語/ベネフィット/意外性のどれで釣るか)」を付す。
   - 推奨1件と根拠(想定読者が検索結果一覧で見た時にクリックする理由)を明示する。
3. **紹介文(Amazon商品ページ用)**
   - 構成: 読者の悩みの言語化 → この本で変わること → 目次ダイジェスト → 読者の条件(誰向け/誰向けでない) → 著者の根拠。
   - 本文にない実績・数値を捏造しない。manuscript.md に書かれた内容だけを根拠にする。
4. **キーワードとカテゴリ**
   - 検索キーワード7枠(KDPの入力枠数)。タイトルと重複する語で枠を浪費しない。
   - カテゴリ案2件と選定理由。
5. **文体仕上げ**
   - タイトル案・紹介文に `humanizer` を適用してAI臭を除去する。
6. **成果物の書き出し**
   - `packs/listing_pack.yaml` を書き、`book.yaml` を更新する。

## Output

### packs/listing_pack.yaml

```yaml
pack: listing_pack
status: ok
created_at: <date>
inputs:
  book_brief_ref: packs/book_brief.yaml
  manuscript_ref: manuscript.md   # gate1 approved 必須
title_candidates:
  - {title: "", subtitle: "", strategy: "<検索語|ベネフィット|意外性>"}
recommended_title: {title: "", subtitle: "", reason: ""}
description: |
  <紹介文(humanizer適用済み)>
keywords: ["", "", "", "", "", "", ""]   # 7枠
categories:
  - {name: "", reason: ""}
```

## Decision Rules

- Gate 1未承認なら実行しない(このスキルが承認を代行することも禁止)。
- 紹介文に収益・効果の保証表現を書かない。
- タイトルは検索結果のサムネイル横で読める長さを優先する。
