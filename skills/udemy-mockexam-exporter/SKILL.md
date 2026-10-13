---
name: udemy-mockexam-exporter
description: "Udemy模擬試験をエクスポートし、ドライランとバックアップ確認後にVantikへ取り込む。"
disable-model-invocation: true
---

Run only when the user invokes `/udemy-mockexam-exporter` directly.

Udemyの模擬試験を取得し、内容を検査してNAS上のVantikへ取り込む。

- **Vantik一括モード（推奨）** — 講座URLまたはエクスポート済みファイルを使う。英語問題なら先にLunaで日本語版を作成し、英日ペアのドライラン、オンラインDBバックアップと`PRAGMA quick_check`確認、本取込まで行う。本取込はNASの本番Vantik DBを変更する。
- **既存Markdown取込モード** — `--input-dir`で既存のエクスポートを使い、同じドライラン・バックアップ・本取込を行う。
- **講座一括モード（推奨）** — 講座URLを1本渡すと、その講座の全模試（practice test）を自動発見して回ごとにエクスポートする。assessments API を使うため**受験済み・未受験を問わず**正解・解説を取得できる。
- **単一結果モード（旧来）** — 各模試のURLから問題・正解・解説を1回ずつエクスポートする。

## スクリプトと初期設定

スクリプトは `reskilling-os/scripts/udemy-mockexam-exporter/` にあります。初回のみセットアップを実行します。

```bash
"$HOME/workspace/maylac/reskilling-os/scripts/udemy-mockexam-exporter/setup.sh"
```

ログイン情報は専用Chromeプロファイル（`~/.cache/udemy-mockexam-exporter/browser-profile`）に保存します。Cookieやトークンをファイルへ書き出しません。

## 使い方

### Vantikへワンストップで取り込む（推奨）

```bash
REPO="$HOME/workspace/maylac/reskilling-os"
TOOL="$REPO/scripts/udemy-mockexam-exporter"
"$HOME/.cache/udemy-mockexam-exporter/venv/bin/python" "$TOOL/udemy_to_vantik.py" \
  "<Udemy講座URL>" --exam-code <Vantik試験コード>
```

GH-300講座（例: `copilot-certification-practice-exams`）は、Vantikカタログの`GitHub Copilot Certification (GH-300)`に対応する`github-copilot`を指定する。ほかの講座は対応するVantik試験コードを明示する。

問題文・選択肢・解説が英語の場合は、日本語として直接取り込まない。Lunaに全問題を日本語へ翻訳させ、`ja/`サブフォルダに原文と同じファイル名で保存する。source ID、選択肢ラベル、正解集合、Markdown構造、コード、製品名、URLは維持する。ENを`--lang en`で先に登録し、対応するJAを`--lang ja`で翻訳として紐付ける。

既にMarkdownをエクスポート済みなら、講座URLの代わりにフォルダを渡す:

```bash
"$HOME/.cache/udemy-mockexam-exporter/venv/bin/python" "$TOOL/udemy_to_vantik.py" \
  --input-dir "$REPO/data/imports/udemy_exports/copilot-certification-practice-exams" \
  --exam-code github-copilot
```

英語原文とLuna翻訳を一緒に登録する場合:

```bash
"$HOME/.cache/udemy-mockexam-exporter/venv/bin/python" "$TOOL/udemy_to_vantik.py" \
  --input-dir "$REPO/data/imports/udemy_exports/copilot-certification-practice-exams" \
  --exam-code github-copilot --lang en \
  --ja-dir "$REPO/data/imports/udemy_exports/copilot-certification-practice-exams/ja"
```

講座URLモードでは毎回新しいローカル出力フォルダを作り、その実行で取得したファイルだけを使う。入力フォルダモードでは、そのフォルダ直下のMarkdownだけを対象にする。`--lang en`では同名ファイルのJA翻訳を必須とし、問題ID、選択肢ラベル、正解が一致することを確認してから、英語・日本語それぞれを読み取り専用DBでドライランする。全言語の件数、問題文、選択肢、正解を確認し、構造不整合や既存問題との内容競合があれば停止する。ドメインや解説の任意欠落は統計に表示して続行する。その後オンラインバックアップを作成し、ファイル・スキーマ・SQLite `quick_check`を確認してからEN、JAの順で本取込する。SSH alias `ugnas`またはコンテナに接続できない場合は停止する。

このコマンドはバックアップ後にNAS本番DBへ書き込む。実行前に試験コードを既存Vantikカタログと照合し、ユーザーに取込先を明示する。コマンドの結果で新規作成数・更新数・警告数を報告する。Udemyの自動受講登録は既定で行わず、ユーザーが明示的に許可した場合だけ`--auto-enroll`を付ける。Udemyの認証切れで停止した場合は、専用Chromeプロファイルでログインしてもらい、ログイン完了後に同じ一括コマンドを再実行する。

### 講座一括モード（推奨）

引数：
1. **講座URL または slug** — `https://<tenant>.udemy.com/course/<slug>/...`（quiz/results 付きでも可）
2. `--prefix PREFIX` — 出力ファイル名の接頭辞（省略時は slug 由来）
3. `--out-dir DIR` — 出力先（省略時は現在のディレクトリ）

```bash
REPO="$HOME/workspace/maylac/reskilling-os"
TOOL="$REPO/scripts/udemy-mockexam-exporter"
"$HOME/.cache/udemy-mockexam-exporter/venv/bin/python" "$TOOL/udemy_course.py" \
  "<講座URL or slug>" --prefix <PREFIX> --out-dir "$REPO/data/imports/udemy_exports/<course-slug>" 2>&1
```

出力は `<PREFIX>_exam01.md`, `<PREFIX>_exam02.md` … と回ごとに分かれる（curriculum 順）。
ARCHIVED（旧カリキュラム）の模試も「全ての回」として含まれる点に注意。

受講登録は既定では行いません。登録して続行する場合だけ `--auto-enroll` を指定してください。

### 単一結果モード（旧来）

引数：
1. **URL** — Udemyの模擬試験URL
2. **出力ファイル名**（省略時は `exam_<日付>.md` を自動生成）

## 実行手順

### Step 1: セッション確認・スクレイプ実行

**講座一括モード（推奨）:**

```bash
REPO="$HOME/workspace/maylac/reskilling-os"
TOOL="$REPO/scripts/udemy-mockexam-exporter"
"$HOME/.cache/udemy-mockexam-exporter/venv/bin/python" "$TOOL/udemy_course.py" "<講座URL or slug>" --prefix <PREFIX> --out-dir "$REPO/data/imports/udemy_exports/<course-slug>" 2>&1
```

**単一結果モード（旧来）:**

```bash
REPO="$HOME/workspace/maylac/reskilling-os"
TOOL="$REPO/scripts/udemy-mockexam-exporter"
"$HOME/.cache/udemy-mockexam-exporter/venv/bin/python" "$TOOL/udemy_scraper.py" "<URL>" "$REPO/data/imports/udemy_exports/<出力ファイル名>.md" 2>&1
```

成功すれば完了。エラーが `セッションが切れています` の場合は Step 2 へ。

### Step 2: セッション切れ時の自動再ログイン

セッション切れエラーが出た場合、以下を案内する：

```
セッションが切れています。以下のコマンドでログインしてください：

! "$HOME/.cache/udemy-mockexam-exporter/venv/bin/python" "$HOME/workspace/maylac/reskilling-os/scripts/udemy-mockexam-exporter/udemy_login.py" --url "<講座と同じUdemyテナントのURL>"

ブラウザでログインし、完了後にターミナルで Enter を押してください。
```

ユーザーがログイン完了を伝えたら Step 1 を再実行する。

### Step 3: 結果の確認

スクレイプ成功後、以下を確認して報告する：

```bash
wc -l "$HOME/workspace/maylac/reskilling-os/data/imports/udemy_exports/<出力先>/<出力ファイル名>.md"
head -30 "$HOME/workspace/maylac/reskilling-os/data/imports/udemy_exports/<出力先>/<出力ファイル名>.md"
```

以前の手動取込手順は使わず、上記の `udemy_to_vantik.py` を使う。ドライラン・バックアップ確認を省略しないこと。

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

**単一結果モード**（正解・解説を出力）：

```markdown
## [EXAM_ID-Q01] 問題1　正解: A

**問題文**
...

**選択肢**
- ✅ **A.** 正解の選択肢　← **正解**
- 　　**B.** その他の選択肢
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
| `HTTP 403 権限なし`（未受講） | 受講権限を確認する。登録してよい場合だけ `--auto-enroll` を指定 |
| `HTTP 403` | 専用Chromeプロファイルでログインし直し、講座の受講権限を確認 |
| `Chrome executable not found` | `/Applications/Google Chrome.app` の存在を確認 |
| タイムアウト | ネットワーク遅延の可能性。再実行で解消することが多い |

## セッションの持続期間

Chromeプロファイル内のログインセッションはUdemyのポリシーに従って期限切れになります。期限切れ時は、対象テナントを指定してログインスクリプトを再実行してください。
