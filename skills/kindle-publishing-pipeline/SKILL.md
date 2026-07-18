---
name: kindle-publishing-pipeline
description: Kindle電子書籍の企画から入稿パッケージまでをエンドツーエンドで進めるオーケストレーター。単一ステージの作業には個別スキル(kindle-genre-scout / kindle-book-planner / kindle-chapter-writer / kindle-listing-builder / kindle-cover-director / kdp-submission-packager)を直接使う。KDPへの出版操作は行わない。
---

# Kindle Publishing Pipeline

設計書: `~/tasks/kindle-publishing-pipeline-design.md`。
このスキルはオーケストレーター。詳細作業は各ステージスキルに委譲し、`book.yaml` の状態を見て次のステージを決める。

## Workflow

1. **状態の確認と再開**
   - 対象プロジェクト(`~/workspace/kindle-books/<slug>/`)が既存なら `book.yaml` を読み、未完了の最初のステージから再開する(冪等)。新規ならステージ1から。
2. **ジャンル発掘**
   - `$kindle-genre-scout` で候補を採点・推薦し、テーマを確定する。
3. **企画・目次**
   - `$kindle-book-planner` でプロジェクトを初期化し、book_brief + outline_pack を作る。
4. **執筆**
   - `$kindle-chapter-writer` で draft.md(H1=章、HUMANマーカー付き)を作る。執筆時は `$cognitive-rhythm-writing`(japanese-tech-writing 併せて読み込み)の規範を適用する。
5. **文体仕上げ**
   - `$humanizer` を全章に適用し、manuscript.md + humanize_log.md を作る。HUMANマーカーは保持する。
6. **◆ Gate 1: 原稿レビュー(人間)**
   - 人間にレビューを依頼する: HUMANマーカー箇所への体験・独自視点の追記、`human_value_log.md` への記録、humanize_logを見たAI臭残存チェック。
   - 人間が `book.yaml` に `gate1: approved` を記入するまで後段に進まない。**このゲートをAIが代行・省略することは禁止。**
7. **リスティングと表紙(並行可)**
   - `$kindle-listing-builder` で listing_pack を作る。
   - `$kindle-cover-director` で cover_pack(デザインブリーフ)を作る。cover/cover.png の配置は人間/外部ツール。
8. **EPUB変換**
   - `$markdown-to-epub` で manuscript.md + cover.png + listing メタデータから dist/book.epub を作り、epubcheck で検証する(epub_pack)。
9. **入稿パッケージと◆ Gate 2**
   - `$kdp-submission-packager` で入稿項目・AI利用申告ドラフト・規約チェックリストを集約する。
   - 人間がGate 2を承認したら `ready_to_publish`。**KDPへのアップロード・出版操作はパイプライン外(人間が実施)。**

## Output Contract

ステージ間の成果物(すべて `packs/` 配下のYAML):

- `genre_brief`: テーマ、想定読者、需要シグナル、著者適合、価格帯。
- `book_brief` + `outline_pack`: コンセプト、ペルソナ、品質基準、章立て。
- `draft_pack`: draft.md、章数、品質自己検証、HUMANマーカー数。
- `manuscript_pack`: manuscript.md、humanize_log、gate1状態。
- `listing_pack`: タイトル案、紹介文、キーワード7枠、カテゴリ。
- `cover_pack`: デザインブリーフ、asset_path、視認性チェック。
- `epub_pack`: dist/book.epub、epubcheck結果。
- `kdp_submission_pack`: 入稿項目集約、AI申告ドラフト、規約チェックリスト、`approval_required: true`。

完全なスキーマとディレクトリレイアウトは `references/workflow-contract.md` を読む。

## Decision Rules

- 各ステージは前段packの `status: ok` を検証してから実行する。失敗時は自packに `status: error` と原因を書いて停止し、後段を巻き込まない。
- `gate1: approved` / `gate2: approved` は人間のみが記入する。承認なしで後段が動く状態を作らない。
- 体験談・実績・数値の捏造禁止。人間が埋める箇所はHUMANマーカーで空ける。
- AI利用申告は事実ベースで必須。申告回避を提案しない(churn and burn型の量産はBAN対象)。
- 複数冊の並行運用は冊ごとに独立した `book.yaml` で管理する。ゲート待ちの冊があっても他の冊は先に進めてよい。
