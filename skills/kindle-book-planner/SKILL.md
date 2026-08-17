---
name: kindle-book-planner
description: Kindle電子書籍の企画・目次を作り、bookプロジェクト(book.yaml + book_brief + outline_pack)を初期化する。本文執筆には使わない(kindle-chapter-writerを使う)。文体仕上げはhumanizer、EPUB変換はmarkdown-to-epubを使う。
---

# Kindle Book Planner

Kindle出版パイプライン(設計書: `~/tasks/kindle-publishing-pipeline-design.md`)のステージ2。
読者が最後まで読みたくなる構成を作り、後段(執筆→文体仕上げ→Gate 1→EPUB)が機械的に処理できる成果物契約を出力する。

## Workflow

1. **入力の確認**
   - `genre_brief.yaml` があればそれを読む。なければ(Phase 1運用)ユーザーからテーマ・想定読者・自分が語れる根拠を聞き、仮の genre_brief として記録する。
   - テーマは「カテゴリ」ではなく「誰の・どんな悩みを解決するか」の1文まで絞る。絞れないなら候補を挙げてユーザーに選ばせる。
2. **プロジェクト初期化**
   - `~/workspace/kindle-books/<book-slug>/` を作成(slug は英小文字ケバブケース)。
   - `book.yaml` と `packs/` を下記契約で初期化する。既存プロジェクトなら再初期化せず、outline 以降のみ更新する(冪等)。
3. **コンセプト確定**
   - 読者ペルソナ(1人に絞る)、解決する悩み、読後に変わること、を各1文で書く。
   - 類書との差別化点を2〜3個。自分の体験・独自視点で埋められる箇所を明示する。
4. **章立て**
   - H1章×6〜10。各章に「要点」「読者が得るもの」「必ず入れる具体例の種類」を書く。
   - 章の並びは読者の行動順(悩みの認知→解決→実践→つまずき対処)にする。
5. **品質基準の設定**
   - 章あたり最低文字数と具体例数を book_brief に明記する(後段 kindle-chapter-writer の自己検証基準になる)。
6. **成果物の書き出し**
   - `packs/book_brief.yaml` と `packs/outline_pack.yaml` を書き、`book.yaml` の stages を更新する。
   - 次工程(`kindle-chapter-writer`)をユーザーに案内する。

## プロジェクトレイアウト(契約)

```
~/workspace/kindle-books/<book-slug>/
├── book.yaml            # 状態管理の単一の正
├── packs/               # ステージ成果物(YAML)
├── draft.md             # 執筆ステージ出力(H1=章)
├── manuscript.md        # 文体仕上げ後 + Gate 1で人間が編集
├── humanize_log.md
├── human_value_log.md   # Gate 1の追記記録(KDPのAI申告根拠)
├── cover/cover.png
└── dist/book.epub
```

## Output

### book.yaml(初期化時)

```yaml
slug: <book-slug>
title_working: "(仮)<タイトル>"
status: in_progress   # in_progress | gate1_pending | gate2_pending | ready_to_publish | published
stages:
  genre_scout:    {status: ok}        # Phase 1では人間決め打ちでも ok と記録
  book_planner:   {status: ok, at: <date>}
  chapter_writer: {status: queued}
  humanize:       {status: queued}
  gate1:          {status: queued}    # approved は人間のみが記入する
  epub:           {status: queued}
```

### packs/book_brief.yaml

```yaml
pack: book_brief
status: ok
created_at: <date>
inputs: {genre_brief_ref: packs/genre_brief.yaml}   # 無ければ null
concept: "<誰の・どんな悩みを・どう解決する本か(1文)>"
persona: "<読者1人の具体像>"
after_reading: "<読後に変わること(1文)>"
differentiation:
  - "<類書との差分。人間の体験で埋める箇所は (HUMAN) を付す>"
quality_bar:
  min_chars_per_chapter: <数値>
  min_examples_per_chapter: <数値>
```

### packs/outline_pack.yaml

```yaml
pack: outline_pack
status: ok
created_at: <date>
inputs: {book_brief_ref: packs/book_brief.yaml}
chapters:
  - n: 1
    title: "<章タイトル>"
    points: ["<要点>"]
    reader_gets: "<この章で読者が得るもの>"
    required_examples: ["<具体例の種類>"]
```

## Decision Rules

- コンセプトの1文が書けないテーマは章立てに進まない(genre選定に差し戻す)。
- 「広く浅く」の企画は却下し、狭く深い切り口に変換して提案する。
- 出版・価格・KDP操作はこのスキルの範囲外。
