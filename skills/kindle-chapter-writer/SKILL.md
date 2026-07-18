---
name: kindle-chapter-writer
description: Kindle電子書籍の本文をoutline_packに沿って章単位で執筆しdraft.mdを作る。企画・目次にはkindle-book-plannerを使う。文体仕上げ(AI臭除去)はhumanizer、EPUB変換はmarkdown-to-epubを使う。
---

# Kindle Chapter Writer

Kindle出版パイプライン(設計書: `~/tasks/kindle-publishing-pipeline-design.md`)のステージ3。
outline_pack に沿って章単位で本文を書き、人間が価値を足すべき箇所をマーキングした `draft.md` を出力する。

## Workflow

1. **前提の検証**
   - `~/workspace/kindle-books/<book-slug>/book.yaml` を読み、`stages.book_planner.status: ok` を確認する。
   - `packs/book_brief.yaml` と `packs/outline_pack.yaml` の `status: ok` を確認する。満たさなければ `kindle-book-planner` に差し戻す。
2. **章単位で執筆**
   - 執筆前に `cognitive-rhythm-writing` スキル(`../cognitive-rhythm-writing/SKILL.md`。japanese-tech-writing を併せて読み込む)を読み、読み物としての緩急規範を最初から適用して書く。後から直す前提で平坦に書かない。
   - outline の章順に、1章ずつ `draft.md` に追記する(H1 = 章タイトル。EPUB変換の章区切り契約)。
   - 各章に必ず入れる: 具体例(required_examples の種類)、手順または判断基準、よくある失敗とその対処。
   - 断定できない事実・数値は書かない。出典が要る主張は `<!-- HUMAN: 出典確認 -->` を付ける。
3. **HUMANマーカーの埋め込み**
   - 人間の体験・独自視点・実例で置き換える/追記すべき箇所に `<!-- HUMAN: <何を足すか> -->` を本文中に埋める。
   - 各章に最低1箇所。これが Gate 1(人間レビュー)の作業指示になる。
4. **章ごとの自己検証**
   - book_brief の `quality_bar`(最低文字数・具体例数)を章ごとに検証する。
   - `cognitive-rhythm-writing` の「執筆後の点検手順」(話題テスト・漏出テスト・緊張台帳・拍・境界)を章ごとに通す。
   - 満たさない章は書き直す。書き直しても満たせない場合はその章を `status: error` として原因を記録し、停止する(後段を巻き込まない)。
5. **成果物の書き出し**
   - `packs/draft_pack.yaml` を書き、`book.yaml` の `stages.chapter_writer` を更新する。
   - 次工程を案内する: `humanizer` で全章の文体仕上げ(AI臭除去)→ `manuscript.md` + `humanize_log.md` を作成 → 人間の Gate 1 レビュー(HUMANマーカーへの追記と `human_value_log.md` の記録)。

## draft.md の契約

- H1 = 章(`markdown-to-epub` の章区切り契約と一致)。H1より上位の前置きテキストは置かない。
- HUMANマーカーは `<!-- HUMAN: ... -->` 形式のHTMLコメントのみ。文体仕上げ(humanizer)はマーカーを保持したまま適用する。

## Output

### packs/draft_pack.yaml

```yaml
pack: draft_pack
status: ok               # ok | error
created_at: <date>
inputs:
  book_brief_ref: packs/book_brief.yaml
  outline_pack_ref: packs/outline_pack.yaml
draft_path: draft.md
verification:
  chapter_count: <数値>
  min_chars_per_chapter: pass   # pass | fail
  min_examples_per_chapter: pass
  human_markers_total: <数値>
error: null
```

## Decision Rules

- outline に無い章を勝手に追加しない。構成変更が必要なら `kindle-book-planner` に差し戻す。
- 体験談・実績・数値を捏造しない。人間が埋めるべき箇所は HUMANマーカーで空けておく。
- `gate1` の approved はこのスキルでは絶対に記入しない(人間のみ)。
- 出版・KDP操作はこのスキルの範囲外。
