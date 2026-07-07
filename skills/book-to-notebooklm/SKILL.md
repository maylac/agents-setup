---
name: book-to-notebooklm
description: Turn a FolioCapture book.md into a NotebookLM study notebook. Not for myLife notes (book-ingest) or Udemy transcripts.
---

# Book → NotebookLM

FolioCapture が生成した `book.md`（OCR済み本文）を、**合格に不要な部分を除いた章ごとのソース**に整形し、
NotebookLM の学習ノートブックへ自動でアップロードする。終着点は「ノートブック＋章ソース」まで。
NotebookLM側の学習ガイド・音声概要・クイズ生成は含めない（ユーザーが後で任意に行う）。

**前提**: `book.md` が既に存在すること。スキャン自体は画面収録権限が必要で **Claude環境からは実行不可**、
ユーザーの Terminal での `swift run FolioCaptureManualQA --until-end --direction right` が必要（このスキルの範囲外）。
`book.md` は `~/Library/Application Support/FolioCapture/Scans/<session>/book.md`。

**著作物のため出力はローカルに留める**。myLife 等の公開リポジトリにコミットしない。

## ワークフロー

### 1. 入力の解決
セッションID指定なら `~/Library/Application Support/FolioCapture/Scans/<id>/book.md`。
未指定なら `Scans/` の最新（mtime降順）を候補提示。frontmatter の `pageCount` を確認。

### 2. 構造の判定（書籍ごとに異なる。ここが判断の要）
`book.md` を実際に読んで、`clean_split.py` に渡す引数を決める:
- **本編ページ範囲** `--start-page` / `--end-page`: 先頭数ページ（表紙・試験直前チェックシート・目次・受験案内など事務情報）を読み、**第1章本文が始まるページ**を特定。末尾（索引/奥付/著者略歴）の開始ページを特定し、その手前を end に。
- **章境界** `--chapters "PAGE:TITLE;PAGE:TITLE;..."`: 目次や各章扉を見て、章開始ページと正式タイトルを列挙。
  章が判別できない本は省略し `--chunk-pages N`（既定40）でサイズ分割にフォールバック。
- **節見出し** `--section-heading`: 本文が `N.M` / `N.M.K` 形式で番号付けされた技術書なら付ける（章内で重複除去し見出し化、章扉ミニ目次ページは自動スキップ）。番号体系が無い本では付けない。

### 3. 整形・分割
```
python3 scripts/clean_split.py --input <book.md> --outdir <out> \
  --title "<正式書名>" --author "<著者>" \
  --start-page S --end-page E --section-heading \
  --chapters "S:第1章 …;P2:第2章 …;…"
```
`--help` に全オプション。ページ番号・記号のみ行・章タイトルのランニングヘッダは自動除去される。

### 4. 品質スポットチェック（必須）
出力の1〜2章を開き、①前付け/索引が混入していない ②各章が最初の節から始まる ③本文が欠落していない
を確認。ズレていれば start/end/chapters を調整して再実行（何度でも上書き可）。
OCR誤字は NotebookLM が許容するので基本放置。重要語の頻出誤変換だけ気になれば sed 等で補正してよい。

### 5. NotebookLM へアップロード
1. **認証確認**: `notebook_list`（notebooklm-mcp）を呼ぶ。エラーなら未認証。
   → ユーザーに「自分の Terminal で `nlm login --force` を実行し、Google（実体アカウント）でサインイン」を依頼。
   **Claude環境からの `nlm login` はブラウザ同期できず必ずタイムアウトするので試みない。** アカウント別名で
   「別アカウント」誤検知が出る場合は `--force`（同一アカウントならそのまま採用）。
2. `notebook_create(title="<書名>")` → notebook_id を得る。
3. 各章ファイルを `source_add(notebook_id, source_type="file", file_path=..., wait=True)` で追加（並列可）。
4. `notebook_get(notebook_id)` で source_count を検証し、NotebookLM の URL を報告。

## NotebookLM の制約
- 1ソースの上限は約50万語。章分割で各ソースを小さく保つ。1章が極端に大きければさらに分割。
- 章の無い本は `--chunk-pages` でサイズ分割（NotebookLMは意味理解するので見出し無しでも可）。

## よくある失敗
| 症状 | 原因 / 対処 |
|------|-------------|
| 事務情報・目次・索引が混入 | `--start-page`/`--end-page` 未指定 or ずれ。実ページを見て設定 |
| 章の途中から始まる/内容欠落 | `--chapters` の境界ページがずれ。目次と扉を再確認 |
| 節見出しが番号だけ/順序乱れ | 章扉ミニ目次の影響。`--section-heading` は N.M 番号体系の本のみに使う |
| `notebook_list` がエラー | nlm 認証失効。ユーザーTerminalで `nlm login --force`（Claude側では起動しない） |
| アップロードが遅い/失敗 | 1ファイルずつ `wait=True`。失敗ソースのみ再 `source_add` |
