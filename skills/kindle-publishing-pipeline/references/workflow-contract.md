# Kindle Workflow Contract

Kindle出版パイプラインのステージ間で受け渡す成果物のスキーマ。設計書: `~/tasks/kindle-publishing-pipeline-design.md` 5章が正。

## ディレクトリレイアウト(1冊=1プロジェクト)

```
~/workspace/kindle-books/<book-slug>/
├── book.yaml            # 状態管理の単一の正
├── packs/               # 本ファイルのスキーマに従うYAML群
├── draft.md             # H1=章、<!-- HUMAN: --> マーカー付き
├── manuscript.md        # humanize後 + Gate 1で人間が編集
├── humanize_log.md
├── human_value_log.md   # Gate 1の追記記録 = AI申告の根拠資料
├── cover/cover.png
└── dist/book.epub
```

## 共通フィールド(全pack)

```yaml
pack: <pack名>
status: ok            # ok | error | queued | pending_asset
created_at: <date>
inputs: {<前段>_ref: <path>}   # 参照鎖。前段の status: ok を検証してから処理
error: null           # error時に原因を記述
```

## book.yaml

```yaml
slug: <book-slug>
title_working: "(仮)<タイトル>"
status: in_progress   # in_progress | gate1_pending | gate2_pending | ready_to_publish | published
stages:
  genre_scout:    {status: queued}
  book_planner:   {status: queued}
  chapter_writer: {status: queued}
  humanize:       {status: queued}
  gate1:          {status: queued}   # approved(+by/at)は人間のみ記入
  listing:        {status: queued}
  cover:          {status: queued}
  epub:           {status: queued}
  kdp_package:    {status: queued}
  gate2:          {status: queued}   # approved は人間のみ記入
```

## 各packの固有フィールド

固有フィールドの詳細は各ステージスキルのSKILL.md「Output」節が正。ここでは参照鎖のみ示す。

```
genre_brief                     (kindle-genre-scout)
  └▶ book_brief, outline_pack   (kindle-book-planner)
       └▶ draft_pack            (kindle-chapter-writer)  draft.md
            └▶ manuscript_pack  (humanizer)              manuscript.md + humanize_log
                 ◆ gate1: approved(人間)+ human_value_log.md
                 ├▶ listing_pack (kindle-listing-builder)
                 └▶ cover_pack   (kindle-cover-director)  cover/cover.png は人間/外部配置
                      └▶ epub_pack (markdown-to-epub)     dist/book.epub + epubcheck
                           └▶ kdp_submission_pack (kdp-submission-packager)
                                ◆ gate2: approved(人間)→ ready_to_publish
```

### manuscript_pack(humanizeステージ出力)

```yaml
pack: manuscript_pack
status: ok
created_at: <date>
inputs: {draft_pack_ref: packs/draft_pack.yaml}
manuscript_path: manuscript.md
humanize_log_path: humanize_log.md
verification:
  chapter_count: <数値>
  human_markers_remaining: <数値>   # Gate 1完了時に0になるべき
gate1: pending                       # pending | approved(人間のみ)
```

### epub_pack(markdown-to-epubステージ出力)

```yaml
pack: epub_pack
status: ok
created_at: <date>
inputs:
  manuscript_ref: manuscript.md      # gate1: approved 必須
  cover_pack_ref: packs/cover_pack.yaml   # status: ok(画像配置済み)必須
  listing_pack_ref: packs/listing_pack.yaml
epub_path: dist/book.epub
build_command: 'pandoc manuscript.md -o dist/book.epub --metadata title="..." --metadata author="..." --toc --split-level=1 --epub-cover-image=cover/cover.png'
verification:
  epubcheck: pass                    # pass | fail(fail時は status: error)
  device_check: pending              # Send-to-Kindleでの実機確認(任意)
```

## 不変条件

1. `gate1`/`gate2` の `approved` はAIが書かない。
2. `status: ok` でない前段packを入力に処理を始めない。
3. `human_value_log.md` が空のまま kdp_submission_pack を作らない。
4. パイプラインのどのステージもKDPへのアップロード・出版操作を行わない。
