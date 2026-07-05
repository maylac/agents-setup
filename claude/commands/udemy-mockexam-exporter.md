---
description: Udemyの模擬試験結果URLをMarkdown形式でエクスポートする。セッション切れ時は自動でログインを促す。
allowed_tools: ["Bash", "Read"]
---

# /udemy-mockexam-exporter

Udemyの模擬試験を Markdown にエクスポートする。**2つのモード**がある。

- **講座一括モード（推奨）** — 講座URLを1本渡すと、その講座の全模試（practice test）を自動発見して回ごとにエクスポートする。assessments API を使うため**受験済み・未受験を問わず**正解・解説を取得できる。
- **単一結果モード（旧来）** — 各模試の結果ページURL（`/results?expanded=...`）を1本ずつエクスポートする。受験者自身の回答（正誤）も付与される。

## スクリプトの場所

```
$HOME/workspace/PMP_mock/
├── udemy_course.py     # 講座一括モード（assessments API）
├── udemy_scraper.py    # 単一結果モード（結果ページDOM）
├── udemy_login.py      # セッション更新用ログインスクリプト
└── udemy_session.json  # 保存済みセッション（自動再利用）
```

## 使い方

### 講座一括モード（推奨）

引数：
1. **講座URL または slug** — `https://toyotajp.udemy.com/course/<slug>/...`（quiz/results 付きでも可）
2. `--prefix PREFIX` — 出力ファイル名の接頭辞（省略時は slug 由来）
3. `--out-dir DIR` — 出力先（省略時はスクリプトと同じディレクトリ）

```bash
cd $HOME/workspace/PMP_mock && \
python3 udemy_course.py "<講座URL or slug>" --prefix <PREFIX> 2>&1
```

出力は `<PREFIX>_exam01.md`, `<PREFIX>_exam02.md` … と回ごとに分かれる（curriculum 順）。
ARCHIVED（旧カリキュラム）の模試も「全ての回」として含まれる点に注意。

**自動受講開始（auto-enroll）**: 未受講（HTTP 403）の講座は、ランディングの「今すぐ登録」ボタン（`data-purpose="buy-this-course-button"`）を自動クリックして受講開始し、そのまま取得を続行する（Udemy Business は無料で即時登録）。自動登録させたくない場合は `--no-auto-enroll` を付ける。

### 単一結果モード（旧来）

引数：
1. **URL** — `https://toyotajp.udemy.com/course/.../results?expanded=...` 形式
2. **出力ファイル名**（省略時は `exam_<日付>.md` を自動生成）

## 実行手順

### Step 1: セッション確認・スクレイプ実行

**講座一括モード（推奨）:**

```bash
cd $HOME/workspace/PMP_mock && \
python3 udemy_course.py "<講座URL or slug>" --prefix <PREFIX> 2>&1
```

**単一結果モード（旧来）:**

```bash
cd $HOME/workspace/PMP_mock && \
python3 udemy_scraper.py "<URL>" "<出力ファイル名>.md" 2>&1
```

成功すれば完了。エラーが `セッションが切れています` の場合は Step 2 へ。

### Step 2: セッション切れ時の自動再ログイン

セッション切れエラーが出た場合、以下を案内する：

```
セッションが切れています。以下のコマンドでログインしてください：

! cd $HOME/workspace/PMP_mock && python3 udemy_login.py

ブラウザが開くので toyotajp.udemy.com にログインしてください。
マイコースページが表示されたら自動で閉じます。
```

ユーザーがログイン完了を伝えたら Step 1 を再実行する。

### Step 3: 結果の確認

スクレイプ成功後、以下を確認して報告する：

```bash
wc -l $HOME/workspace/PMP_mock/<出力ファイル名>.md
head -30 $HOME/workspace/PMP_mock/<出力ファイル名>.md
```

### Step 4: 解説の圧縮（ユーザーが希望した場合）

ユーザーが「解説が冗長」「まとめて」などと言った場合、以下のスクリプトで圧縮する。
**Claude API は使わない。** Claudeが直接、各問題の「まとめ解説」を書き直す。

#### 圧縮ルール

「まとめ解説」の内容を以下の形式に置き換える：

```
- **正解の理由**: （1〜2文。なぜその選択肢が正解か）
- **不正解の理由**:
  - A: （1文。正解の場合は省略）
  - B: （1文。正解の場合は省略）
  - C: （1文。正解の場合は省略）
  - D: （1文。正解の場合は省略）
```

削除対象：
- `ーーーーーー...` 区切り線以降の「詳細情報」セクションすべて
- 「【参照】」「【構成の詳細情報】」以降のテキスト
- 前置き文（「このシナリオでは〜」など問題文の繰り返し）

#### 実行方法

Claudeが直接ファイルを読み込み、各問題ブロックの `**まとめ解説**` セクションを書き直してファイルを上書き保存する。
出力ファイル名は `<元のファイル名>_condensed.md` とする。

---

## 出力フォーマット

**講座一括モード**（受験状況に依存しないため、ヘッダに正解の選択肢を表示）：

```markdown
## [EXAM_ID-Q01] 問題1　正解: C

**問題文**
...

**選択肢**
- 　　**A.** その他の選択肢
- 　　**B.** その他の選択肢
- ✅ **C.** 正解の選択肢　← **正解**

**まとめ解説**
...

**ドメイン**: （あれば section を表示）
---
```

**単一結果モード**（受験者自身の回答も付与）：

```markdown
## [EXAM_ID-Q01] 問題1　❌ 不正解

**問題文**
...

**選択肢**
- ✅ **A.** 正解の選択肢　← **正解**
- ❌ **B.** 誤った選択肢　← あなたの回答（**不正解**）
- 　　**C.** その他の選択肢

**まとめ解説**
...

**ドメイン**: EC2
---
```

## exam_id の決まり方

出力ファイル名から自動生成される：
- `aws_saa_exam01.md` → `AWS_SAA_EXAM01`
- `exam03-2.md` → `EXAM03-2`

## トラブルシューティング

| エラー | 対処 |
|--------|------|
| `セッションが切れています` | Step 2 のログインを実行 |
| `course_id を取得できませんでした` | 講座URL/slug が正しいか確認（講座一括モード） |
| `HTTP 403 権限なし`（未受講） | 既定では自動で受講開始する。`自動受講開始に失敗` の場合のみ手動で受講開始 |
| `0問取得` | セレクター不一致の可能性。URL が `/results?expanded=...` 形式かを確認（単一結果モード） |
| `Chrome executable not found` | `/Applications/Google Chrome.app` の存在を確認 |
| タイムアウト | ネットワーク遅延の可能性。再実行で解消することが多い |

## セッションの持続期間

ログイン後のセッション（`udemy_session.json`）は Udemy のポリシーに従い数日〜数週間有効。
有効期間中はログイン不要でエクスポートできる。
