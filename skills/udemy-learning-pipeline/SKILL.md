---
name: udemy-learning-pipeline
description: 'Run the Udemy learning pipeline: collect transcripts, generate study assets, and create NotebookLM-ready materials.'
---

# Udemy Learning Pipeline

Udemy受講済み講座のトランスクリプトを収集し、学習資産として整理してNotebookLMにアップロードするフルパイプライン。

## 運用原則

- 動画本体は取得しない。収集対象は、正規アクセスできる字幕VTT、Udemy APIメタデータ、講座のsupplementary resources、公開公式Docsに限定する。
- transcriptが取れない講座は「未取得」と明記し、講座メタデータ、配布資料、公式Docsで補強する。本文を推測して完全な講義要約として扱わない。
- 長いtranscriptは先頭だけで完結扱いしない。分割要約、章単位処理、または「partial」と明記した出力にする。
- 検索時点の `enrolled` 表示と、登録後の `subscribed-courses/{course_id}` 検証結果を混同しない。

## スクリプトの場所

```
~/workspace/udemy-transcripts/
├── collect.py          # トランスクリプト収集（yt-dlp + Udemy API）
├── make_assets.py      # 学習資産生成（Codex）
├── transcripts/        # 収集したトランスクリプトMD
└── learning-assets/    # 生成した学習資産MD
```

---

## Step 1: トランスクリプト収集

### 1-1. Cookie エクスポート（初回 or セッション切れ時）

```bash
yt-dlp --cookies-from-browser=chrome \
  --cookies=/tmp/udemy_cookies.txt \
  --skip-download "https://www.udemy.com/home/my-courses/" 2>/dev/null
```

### 1-2. 受講コース一覧を確認

```bash
python3 ~/workspace/udemy-transcripts/collect.py --list-only
```

- Udemy Base URL: `https://toyotajp.udemy.com`（企業アカウントの場合）
  - **Toyota 企業テナントは 2026-08-31 まで**。テナント失効後は個人アカウント `https://www.udemy.com` に切り替え、organizations 検索 API（下記）は使用不可。
- Cookie ファイル: `/tmp/udemy_cookies.txt`
- API: `GET /api-2.0/users/me/subscribed-courses/?ordering=-last_accessed`

### 1-3. 一括収集（screenセッションで実行）

```bash
screen -dmS udemy-collect bash -c "
  PYTHONUNBUFFERED=1 python3 ~/workspace/udemy-transcripts/collect.py \
    >> /tmp/udemy_collect.log 2>&1
"
```

進捗確認:
```bash
strings /tmp/udemy_collect.log | grep -E "^\[|Done:" | tail -5
ls ~/workspace/udemy-transcripts/transcripts/*.md | wc -l
```

### 収集スクリプト仕様（collect.py）

- yt-dlp で VTT 字幕をダウンロード（`--sub-langs ja,en --skip-download`）
- VTT → Markdown: タイムスタンプ・タグ除去、重複行排除
- 字幕なしコース（模擬試験・DRM等）は自動スキップ
- 既存 MD があるコースはスキップ（冪等）

### 1-4. Udemy Business検索から講座を拡張する場合

テナント内検索は、公開UdemyではなくBusiness tenantを使う。

```text
GET https://toyotajp.udemy.com/api-2.0/organizations/199704/search-courses/v2/?q=<query>&skip_price=true&page_size=50&src=sac
```

- 検索候補は `/tmp/udemy_<topic>_search_candidates_<date>.json` のように保存する。
- 候補選定はCSVやスコアを鵜呑みにせず、今回の学習目的、キャリア戦略、既存ローカル資産の不足から絞る。
- 登録確認は、検索APIで得た `id` を正として `GET /api-2.0/users/me/subscribed-courses/{id}/?fields[course]=id,title,url` で検証する。
- ブラウザページで捕捉した別リクエストのcourse_idは、ページ遷移タイミング次第で直前講座のIDを拾うことがあるため、登録検証の正本にしない。
- 登録できない講座は `no_enroll_button` などの状態を残し、ノートには未登録/未確認として記載する。

---

## Step 2: 学習資産生成（Codexが直接実施）

収集した `transcripts/*.md` を1ファイルずつ読み込み、以下フォーマットで `learning-assets/` に保存する。

### 出力フォーマット

```markdown
# コース名

## 📋 コース概要
（全体の目的・対象者・学習後に得られるスキルを3〜5行で）

## 🗂️ 章別サマリー
### 章タイトル
- 要点（箇条書き3〜5点）

## 💡 キーコンセプト
（核心となる概念を10〜15項目、各1行説明付き）

## 📖 用語集
（重要用語とその定義を15〜20項目）
```

### 実行手順

1. 対象ファイルを列挙
   ```bash
   ls ~/workspace/udemy-transcripts/transcripts/*.md | wc -l
   ls ~/workspace/udemy-transcripts/learning-assets/*.md 2>/dev/null | wc -l
   ```

2. 未処理ファイルを特定して1件ずつ処理
   - 字幕誤変換（例: Dify→DIY/リファイ、LLM→LLVM）は正しい表記に修正
   - 長大なトランスクリプトは章単位またはチャンク単位で処理し、先頭だけを使う場合は `partial` と明記する

3. 処理済みとして記録（同名ファイルが存在する場合はスキップ）

### make_assets.py（Codexを使う場合）

```bash
screen -dmS make-assets bash -c "
  source ~/.config/secrets/sakana
  PYTHONUNBUFFERED=1 python3 ~/workspace/udemy-transcripts/make_assets.py \
    >> /tmp/make_assets.log 2>&1
"
```

---

## Step 2.5: ダウンロードリソース確認

講座に配布資料がある場合は、講義ノート生成前にsupplementary resourcesを確認する。

- 全体収集: `collect_udemy_downloadables.py` を使う。
- focused research: 対象course_idだけを処理する小さなmanifestを作り、既存の全体manifestを不用意に上書きしない。
- manifestには `downloaded`、`external_link`、`metadata_only`、`download_failed` を分けて記録する。
- 外部リンクは本文をコピーせず、リンク、講義名、用途を記録する。
- ZIP、PDF、DOCX、XLSXなどの配布ファイルは、ライセンス範囲内のローカル学習用素材として保存し、再配布しない。

---

## Step 3: NotebookLM アップロード

### 3-1. 認証確認

```bash
nlm login   # セッション切れ時のみ
```

### 3-2. ジャンル分類ルール

| ジャンル | キーワード（ファイル名マッチ） |
|----------|-------------------------------|
| 生成AI・入門・活用 | NotebookLM, ChatGPT, 生成AI, AIトレンド, AI倫理, AI活用, AI時代, はじめての |
| AIコーディング・開発 | Codex, Cline, Cursor, Roo, アルゴリズム, Kubernetes, DevOps, コーディング |
| AI自動化・エージェント | n8n, N8N, Copilot Studio, Dify, エージェント, 自動化, Automation, Workspace Studio |
| AWS・クラウド・インフラ | AWS, SAA, クラウド, インフラ |
| PMP・プロジェクト管理 | PMP, PMBOK, プロジェクト |
| ビジネス・戦略・思考 | MBA, アカウンティング, マーケティング, 論理思考, コンサル, 戦略, CTO |
| 生産性・ツール活用 | Obsidian, Outlook, Power BI, タイムマネジメント, 時間管理, アウトルック |
| データ・セキュリティ・AI倫理 | サイバー, ハッキング, セキュリティ, データサイエンス, データマネジメント, DMBOK |
| 組織・人材・スキルアップ | ダイバーシティ, DEI, リーダー, スキルアップ, PDCA |

### 3-3. ノートブック作成とアップロード

MCP ツール `mcp__notebooklm-mcp__notebook_create` と `mcp__notebooklm-mcp__source_add` を使用。

```
# ノートブック作成
notebook_create(title="生成AI・入門・活用")

# ファイルアップロード（source_type="file"）
source_add(
  notebook_id=<id>,
  source_type="file",
  file_path="$HOME/workspace/udemy-transcripts/learning-assets/<file>.md"
)
```

- ファイル名に `~` を含む場合は `/tmp/` にコピーしてからアップロード
- 並列アップロード可（同一ノートブックへの複数 source_add を同時発行）

### 既存ノートブック ID（2026-05-29 時点）

> 鮮度注記: 下表は 2026-05-29 時点のスナップショット。再利用前に `notebook_list` で存在を確認すること。

| ジャンル | ノートブック ID |
|----------|----------------|
| 生成AI・入門・活用 | d66ea0c5-692f-45f6-8584-28196641b08d |
| AIコーディング・開発 | ca5a640e-017c-47d8-a060-267f8db09e6d |
| AI自動化・エージェント | c2641f3b-0174-4ddd-9c5e-8d9607bb07d5 |
| PMP・プロジェクト管理 | f6d300d8-c884-41d1-9525-81ff841d05fa |
| ビジネス・戦略・思考 | 79a8f90c-975c-4090-9daf-bfaa3fa6c07d |
| 生産性・ツール活用 | 8d44a0c3-ef1f-444e-b1cd-c8368d6953bd |
| データ・セキュリティ・AI倫理 | 8217d282-cdf0-4b38-b78d-d8405c37117b |
| 組織・人材・スキルアップ | ac263ef2-6409-4236-9575-0c013ad98393 |
| AWS SAA 模擬試験 復習 | 5c530dde-0c85-49cc-bb48-ef71a41cb7eb |

---

## Step 4: 模擬試験エクスポート（AWS SAA）

模擬試験のエクスポート手順・スクレイパーの場所は `/udemy-mockexam-exporter` スキルを正とする（このパイプラインから場所をハードコードしない）。

### 命名規則

- 生ファイル: `aws_saa_exam<NN>.md`（例: `aws_saa_exam04.md`）
- 圧縮版: `aws_saa_exam<NN>_condensed.md`
- 問題 ID 形式: `[AWS_SAA_EXAM<NN>-Q<NN>]`

### condensed 版の作成

```python
# ーーーーーーーーーー / 【構成の詳細情報】/ 【詳細情報】/ 【参照】 以降を除去
import re
CUTPATTERN = r'(\s*ーーーーーーーーーー+|\s*【構成の詳細情報】|\s*【詳細情報】|\s*【注釈】|\s*【参照】)'

def condense(content):
    def replacer(m):
        summary = re.sub(CUTPATTERN + r'.*', '', m.group(1), flags=re.DOTALL).rstrip()
        return f'**まとめ解説**\n\n{summary}\n\n**ドメイン**'
    return re.sub(
        r'\*\*まとめ解説\*\*\n\n(.+?)\n\n\*\*ドメイン\*\*',
        replacer, content, flags=re.DOTALL
    )
```

---

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| Udemy API 403 | Cookie 期限切れ → Step 1-1 を再実行 |
| yt-dlp DRM エラー | 正常（DRM 保護動画はスキップ） |
| NotebookLM 認証エラー | `! nlm login` を実行 |
| `~ ` を含むファイルアップロード失敗 | `/tmp/` にコピーしてから `source_add` |
| screenセッション確認 | `screen -list` |
| ログ確認 | `strings /tmp/udemy_collect.log \| tail -10` |

## 環境変数・認証情報

- Udemy Cookie: `/tmp/udemy_cookies.txt`（有効期間 数日〜数週間）
- NotebookLM 認証: `~/.notebooklm-mcp-cli/profiles/default`
