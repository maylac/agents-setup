---
name: pmi-studyhall-export
description: "PMI Study Hall のミニ試験・フルレングス試験の解答済みセッションから、全問題のデータをブラウザ経由で取得し、マークダウンファイルに保存する。"
disable-model-invocation: true
---

# /pmi-studyhall-export

Run only when the user invokes `/pmi-studyhall-export` directly.

# /pmi-studyhall-export

PMI Study Hall の解答済みセッションから全問題データをブラウザ経由で取得し、マークダウンファイルとして保存する。

## 試験種別とURLパターン

| 種別 | URL パターン | 問題数 |
|------|-------------|--------|
| ミニ試験 | `#exams/answers/{session_id}/{question_id}` | 15問 |
| フルレングス | `#exams/{session_id}/exam_sections/{section_id}/{question_id}` | 175問 |

## 前提条件

- Chrome DevTools MCP が有効になっていること
- PMI Study Hall（studyhall.pmi.org）に既にログイン済みであること
- 対象の試験が完了済みであること

---

## ミニ試験のエクスポート

### Step 1: セッションIDの確認

URL（`#exams/answers/{session_id}/{question_id}`）から session_id を読み取る。

### Step 2: グローバル変数の初期化

```javascript
() => {
  window.__pmiData = {};
  window.__extractQ = function() {
    const text = document.body.innerText;
    const qNumMatch = text.match(/(\d+) of 15/);
    const qNum = parseInt(qNumMatch?.[1] || '0');
    const url = window.location.hash;
    const qId = (url.match(/\/(\d+)$/) || [])[1];
    const afterQuestion = text.split('\nQuestion\n\n')[1] || '';
    const beforeSol = afterQuestion.split('\n正解：')[0] || '';
    const qLines = beforeSol.trim().split('\n');
    let questionText = '';
    const choices = {};
    let currentChoice = null;
    for (const line of qLines) {
      const choiceMatch = line.match(/^([A-E])\./);
      if (choiceMatch) { currentChoice = choiceMatch[1]; choices[currentChoice] = ''; }
      else if (currentChoice) { choices[currentChoice] = (choices[currentChoice] + ' ' + line.trim()).trim(); }
      else if (line.trim()) { questionText = (questionText + ' ' + line.trim()).trim(); }
    }
    const solSection = text.split('\n正解：')[1] || '';
    const correctAns = (solSection.match(/^([A-E、A-E ,]+)/) || [])[1]?.trim() || '';
    const explanation = (solSection.split('\n参考文献')[0] || solSection).trim();
    const yourAns = (text.match(/Your answers? (?:are|is) ([A-E, ]+)\./) || [])[1]?.trim() || '';
    const isCorrect = text.includes('Your result is correct.');
    const difficulty = (text.match(/Difficulty Level:\n(.+)/) || [])[1]?.trim();
    const timeTaken = (text.match(/Time Spent:\n(.+)/) || [])[1]?.trim();
    const confidence = (text.match(/Confidence Level:\n(.+)/) || [])[1]?.trim();
    return { num: qNum, qId, url, questionText, choices, correctAns, explanation, yourAns, isCorrect, difficulty, timeTaken, confidence };
  };
  return 'initialized';
}
```

### Step 3: 各試験の15問を収集

1. 最初の問題URLにナビゲート → `wait_for ["1 of 15"]`
2. ループで抽出：

```javascript
() => {
  const q = window.__extractQ();
  if (!window.__pmiData.exam1) window.__pmiData.exam1 = [];
  window.__pmiData.exam1.push(q);
  return { count: window.__pmiData.exam1.length, num: q.num };
}
```

3. `take_snapshot` で "Next" ボタンの uid を特定してクリック

### Step 4: データ取得（1試験ずつ）

```javascript
// ⚠️ 複数試験まとめて取得するとサイズ超過になる → 1試験ずつ取得
() => JSON.stringify(window.__pmiData.exam1)
```

---

## フルレングス試験のエクスポート

### Step 1: セクションIDと問題ID一覧の収集

ページネーション（最大20件/ページ）を全ページ巡回して question_id をすべて収集する：

```javascript
async () => {
  const sessionId = 'XXXXXXX';
  const sectionId = 'YYYYYYY';
  let allIds = [];
  let page = 1;
  while (true) {
    const r = await fetch(`/api/exam_sections/${sectionId}/questions?page=${page}&per_page=20`, {
      headers: { 'Accept': 'application/json' }
    });
    if (!r.ok) break;
    const data = await r.json();
    const ids = data.questions?.map(q => String(q.id)) || [];
    if (!ids.length) break;
    allIds = allIds.concat(ids);
    if (!data.next_page) break;
    page++;
  }
  window.__allQIds = allIds;
  return { total: allIds.length, ids: allIds.slice(0, 5) };
}
```

> APIが使えない場合はページネーションボタンを take_snapshot で確認しながら手動巡回する。

### Step 2: 抽出関数の初期化

フルレングス試験は選択肢が **"A.\nテキスト"** 形式（ミニ試験の "A. テキスト" とは異なる）：

```javascript
() => {
  window.__fullExamData = [];
  window.__extractFullQ = function() {
    const text = document.body.innerText;
    const url = window.location.hash;
    const qId = (url.match(/\/(\d+)$/) || [])[1];
    const pos = parseInt((text.match(/(\d+) of \d+/) || [])[1] || '0');
    const afterQuestion = text.split('\nQuestion\n\n')[1] || '';
    const beforeSolution = afterQuestion.split('\n\n正解：')[0] || '';
    const qLines = beforeSolution.trim().split('\n');
    let questionText = '';
    const choices = {};
    let currentChoice = null;
    for (const line of qLines) {
      if (/^[A-E]\.$/.test(line.trim())) {
        currentChoice = line.trim().replace('.', '');
        choices[currentChoice] = '';
      } else if (currentChoice) {
        choices[currentChoice] = (choices[currentChoice] + ' ' + line.trim()).trim();
      } else if (line.trim()) {
        questionText = (questionText + ' ' + line.trim()).trim();
      }
    }
    const solSection = text.split('\n\n正解：')[1] || '';
    const correctAns = (solSection.match(/^([A-E、 ]+)/) || [])[1]?.trim() || '';
    const explanation = (solSection.split('\n参考文献')[0] || solSection).trim();
    const yourAnsMatch = text.match(/Your answer is ([A-E, ]+)\./) || text.match(/Your answers are ([A-E, ]+)\./);
    const yourAns = yourAnsMatch?.[1]?.trim() || '';
    const isCorrect = text.includes('Your result is correct.');
    const confidence = (text.match(/Confidence Level:\n(.+)/) || [])[1]?.trim();
    const timeTaken = (text.match(/Time Spent:\n(.+)/) || [])[1]?.trim();
    const difficulty = (text.match(/Difficulty Level:\n(.+)/) || [])[1]?.trim();
    return { pos, qId, url, questionText, choices, correctAns, explanation, yourAns, isCorrect, confidence, timeTaken, difficulty };
  };
  return 'initialized';
}
```

### Step 3: 全問題を自動巡回して収集

ハッシュナビゲーションで高速に全問題を巡回する（ページリロードなし）：

```javascript
async () => {
  const sessionId = 'XXXXXXX';
  const sectionId = 'YYYYYYY';
  const ids = window.__allQIds.slice(0, 60);  // 60問ずつに分割
  for (const qId of ids) {
    window.location.hash = `#exams/${sessionId}/exam_sections/${sectionId}/${qId}`;
    await new Promise(r => setTimeout(r, 700));  // 700ms待機
    const q = window.__extractFullQ();
    window.__fullExamData.push(q);
  }
  return { collected: window.__fullExamData.length, lastPos: window.__fullExamData.at(-1)?.pos };
}
```

> **60問ずつ分けて実行**する。一度に全問やるとタイムアウトする。

### Step 4: バッチ毎にデータをファイルに保存（重要）

```javascript
// ⚠️ セッション圧縮でインラインデータが消えることがある
// → 各バッチ後に必ずファイルに保存する

() => JSON.stringify(window.__fullExamData.slice(0, 60))    // バッチ1
() => JSON.stringify(window.__fullExamData.slice(60, 120))  // バッチ2
() => JSON.stringify(window.__fullExamData.slice(120, 175)) // バッチ3
```

**取得後すぐに `/tmp/pmi_batch{n}.json` に書き込む**（Bash で Python を使う）：

```bash
python3 -c "
import json, re
# evaluate_script の出力はツール結果ファイルに保存される場合がある
# ファイルパス: ~/.codex/projects/.../tool-results/mcp-chrome-devtools-evaluate_script-*.txt
"
```

> ⚠️ **ツール結果ファイルは Read ツールで読めない**（トークン超過）。**Bash + Python** で処理すること。

---

## データ復元手順（セッション継続時）

セッション圧縮後にデータが消えた場合の復元手順：

### 1. ブラウザにデータが残っているか確認（最優先）

```javascript
() => {
  if (window.__fullExamData?.length > 0) {
    return { count: window.__fullExamData.length, ok: true };
  }
  return 'no data';
}
```

ブラウザに残っていれば **再ナビゲート不要** → Step 4 のデータ取得から再開。

### 2. ツール結果ファイルから復元

```python
import json, re, os

# ツール結果ファイルは evaluate_script 出力が大きい場合に自動保存される
# 場所: ~/.codex/projects/{project_id}/tool-results/mcp-chrome-devtools-evaluate_script-*.txt
results_dir = os.path.expanduser('~/.codex/projects/{project_id}/tool-results/')
files = sorted(os.listdir(results_dir))

def parse_tool_result(path):
    with open(path) as f:
        outer = json.loads(f.read())
    text = outer[0]['text']
    m = re.search(r'```json\n(.*)\n```', text, re.DOTALL)
    if not m: return None
    parsed = json.loads(m.group(1))
    if isinstance(parsed, str):
        parsed = json.loads(parsed)
    return parsed if isinstance(parsed, list) and parsed and 'pos' in parsed[0] else None
```

### 3. JSONL から復元（最終手段）

インラインで返ったデータは JSONL に保存される。**`pos:121` ではなく最初の問題の `qId` で検索**する：

```python
# JSONL パス: ~/.codex/projects/{project_id}/{session_id}.jsonl
path = '~/.codex/projects/.../.jsonl'
with open(path) as f:
    lines = f.readlines()

target_qid = '18013713'  # Q121 の qId
for i, line in enumerate(lines):
    if target_qid in line:
        obj = json.loads(line)
        for block in obj['message']['content']:
            if block.get('type') == 'tool_result':
                for inner in block.get('content', []):
                    if inner.get('type') == 'text' and target_qid in inner['text']:
                        m = re.search(r'```json\n(.*)\n```', inner['text'], re.DOTALL)
                        parsed = json.loads(json.loads(m.group(1)))
                        # → 保存
```

---

## マークダウン生成

### データ結合

```python
import json, re, os

def parse_tool_result(path):
    with open(path) as f:
        outer = json.loads(f.read())
    text = outer[0]['text']
    m = re.search(r'```json\n(.*)\n```', text, re.DOTALL)
    parsed = json.loads(m.group(1))
    return json.loads(parsed) if isinstance(parsed, str) else parsed

all_q = sorted(data1 + data2 + data3, key=lambda x: x.get('pos', 0))
```

### 解説文のクリーニング

フルレングス試験では一部の解説に英語のボイラープレートが混入する：

```python
def clean_explanation(exp):
    lines = exp.split('\n')
    cleaned = []
    skip = False
    for line in lines:
        if 'This question and rationale were developed' in line:
            skip = True
        if skip:
            if any(s in line for s in [
                'Incorrect', 'Correct', 'Your result is', 'Your answer is',
                'Correct answer is', 'Confidence Level:', 'Time Spent:',
                'Difficulty Level:', 'Got feedback', 'copyright of PMI', 'Feedback'
            ]):
                continue
        cleaned.append(line)
    return '\n'.join(cleaned).strip()
```

### マークダウン出力

```python
def make_markdown(questions, session_id, section_id, exam_name):
    pos_key = 'pos' if 'pos' in questions[0] else 'num'
    correct = sum(1 for q in questions if q.get('isCorrect'))
    total = len(questions)
    
    lines = [
        f'# PMI Study Hall - {exam_name}',
        f'**セッションID**: {session_id}',
        f'**正答数**: {correct} / {total} ({correct/total*100:.1f}%)',
        '', '---', ''
    ]
    for q in sorted(questions, key=lambda x: x.get(pos_key, 0)):
        num = q.get(pos_key, '?')
        is_correct = q.get('isCorrect', False)
        lines += [
            f'## 問{num}', '',
            f"**問題**: {q.get('questionText', '').strip()}", '',
        ]
        for key in sorted(q.get('choices', {}).keys()):
            lines.append(f"- {key}. {q['choices'][key]}")
        lines += [
            '',
            f"**正解**: {q.get('correctAns', '').strip()}",
            f"**あなたの回答**: {q.get('yourAns', '').strip()}",
            f"**結果**: {'✓ 正解' if is_correct else '✗ 不正解'}",
        ]
        for label, key in [('難易度', 'difficulty'), ('所要時間', 'timeTaken'), ('自信度', 'confidence')]:
            if q.get(key):
                lines.append(f'**{label}**: {q[key]}')
        exp = clean_explanation(q.get('explanation', ''))
        if exp:
            lines += ['', '**解説**:', '', exp]
        lines += ['', '---', '']
    return '\n'.join(lines)
```

---

## トラブルシューティング

| 問題 | 原因 | 対処 |
|------|------|------|
| `correctAns` が空文字 | 全角文字 or 特殊フォーマット | `\n\n正解：` vs `\n正解：` を確認 |
| 選択肢が空 | フル試験は `"A.\nテキスト"` 形式 | `__extractFullQ` を使う（ミニ用と別） |
| ツール結果ファイルが Read できない | ファイルが大きすぎる（40k+ トークン） | **Bash + Python で処理**すること |
| セッション圧縮でデータ消失 | インラインデータはコンテキストに依存 | ブラウザの `window.__fullExamData` を確認→再取得 |
| JSONL に `"pos":121` が見つからない | エスケープ処理 or 別キー | **qId**（例: `"18013713"`）で検索する |
| 解説にボイラープレートが混入 | `"This question and rationale..."` 以降 | `clean_explanation()` で除去 |
| Next ボタンが見つからない | a11y tree の uid 変更 | `take_snapshot` で再確認 |

## 出力ファイル構造

```
~/Documents/PMI_StudyHall/
├── index.md          # ミニ試験 全回 成績まとめ
├── exam01.md         # ミニ試験 第1回
├── ...
├── exam15.md         # ミニ試験 第15回
└── fullexam01.md     # フルレングス試験 第1回（175問）
```

各ファイルには以下が含まれる：
- 問題文・選択肢 (A-E)
- 正解・あなたの回答・正誤
- 難易度・所要時間・自信度
- 解説文（クリーニング済み）
