# refactor-instructions.md — maylac ワークスペース環境リファクタリング指示書(確定版)

> 本書は分析担当モデルが 2026-06-12 にコードベースを実際に読んで作成し、所有者の決定(§10)を反映した確定版。
> 実装担当モデルは本書の範囲内でのみ作業すること。証拠なき大規模削除・全面書き換えは禁止。

---

## 1. Objective

対象は以下の3領域。目的は「既存の自動化・運用を一切壊さずに、指示ファイルの重複と実態との乖離を解消し、構成を変更しやすい状態にする」こと。見た目の綺麗さや全面書き換えは目的ではない。

1. **ホームレベルのエージェント指示ファイル群** — `~/AGENTS.md`(`~/CLAUDE.md` はこれへの symlink)、`~/.claude/CLAUDE.md`、`~/.claude/AGENTS.md`、`~/.claude/rules/`、`~/.claude/RTK.md`、`~/.claude/settings*.json`
2. **myLife リポジトリ** — `/Users/maylac/workspace/myLife`(個人ライフログの LLM Wiki + 自動同期パイプライン)
3. **全体フォルダ構成** — `$HOME` 直下と `~/workspace/` の配置

---

## 2. Project Understanding

### 2.1 ホームディレクトリ(`/Users/maylac`)

- `$HOME` 自体が **open-slide ワークスペース**になっている: `package.json`(name: "maylac", scripts: `open-slide dev/build/preview`)、`slides/`(getting-started, industrial-ai-anomaly の2デッキ)、`themes/`(空、.gitkeep のみ)、`tsconfig.json`、`netlify.toml`、`vercel.json`、`open-slide.config.ts`(空設定)、`package-lock.json`。
- **`$HOME` は git リポジトリでもある**が、`git ls-files` は **0件**(何もトラックしていない)、remote なし。→ 所有者確認済み: **意図していない**(§10 Q1)。
- `~/AGENTS.md` = Karpathy Guidelines 全文。`~/CLAUDE.md` はそれへの symlink。
- その他 home 直下: `tasks/`(todo.md, lessons.md, plans/)、`bin/`(シェルスクリプト2本)、`docs/`、STL ファイル3つ(mona2-case 等、ZMK キーボード関連)、`actions-dashboard.html` 等。

### 2.2 `~/.claude/`(グローバル Claude Code 設定)

- `CLAUDE.md`(5.5K): 「Workflow Orchestration」+ `@RTK.md` include + **Karpathy Guidelines の再掲**。
- `AGENTS.md`(10K): 「Everything Claude Code (ECC) v1.9.0」プラグインの説明書。CLAUDE.md とは**別内容**。
- `rules/`: common + 11言語分のルールファイル。`agents/` 28個、`skills/` 123個(skill `karpathy-guidelines` が存在する)。
- `settings.local.json` が **105KB**(トップレベルキーは permissions のみ)。`settings.json.backup`(3バイト=実質空)、`settings.json.bak`、`settings.json.bak.20260527_193350` などバックアップが散乱。
- 結果として毎セッション、`~/.claude/CLAUDE.md`(Karpathy 含む)+ `~/CLAUDE.md`(Karpathy 全文)の **同一ガイドラインが二重ロード**されている。

### 2.3 myLife リポジトリ(`~/workspace/myLife`)

- **Karpathy LLM-Wiki パターン準拠の個人知識基盤**。3層: `raw/`(自動収集・読取専用)/ `wiki/`(LLM 管理知識)/ `CLAUDE.md`(唯一の Schema)。
- **データフロー**: 外部ソース(X ブックマーク、Kindle、YouTube、Pocket Casts、note、Apple Health、音声日記 ほか)→ GitHub Actions(cron / workflow_dispatch / push)→ `scripts/<source>-sync/` が `raw/` へ書き込み → `scripts/wiki-sync/ingest_*.py` が `wiki/pages/` へ取り込み → lint / 週次・月次レビュー / brain-pack / product-assembly が派生物を生成 → Discord 通知。
- **エントリーポイント**: `.github/workflows/` の28本の YAML が実質のエントリーポイント。手動操作は `.claude/skills/` の `/clip` `/query` `/lint` `/ingest` `/insight`。
- **主要モジュール**: `scripts/lib/`(共通: claude.py, frontmatter.py, notify.py, wiki_ops.py, transcribe.py 等。各々 `test_*.py` 併設)、各 `scripts/<機能>/`。
- **検証**: `python3 scripts/run_tests.py`(scripts/ 配下の `test*.py` を順次実行する自作ランナー)。CI: `shared-lib-guard.yml` が PR 時に `python scripts/lib/check_shared_lib_usage.py` を実行。`wiki-lint.yml` が lint 系スクリプトを実行(現状は全ステップ `continue-on-error: true`)。
- **外部依存**: Claude API、Groq Whisper、Jina Reader、X/Kindle Cookie、YouTube OAuth2、Pocket Casts、Discord Webhook、GitHub Secrets。
- **Boundaries(CLAUDE.md 明記・絶対遵守)**: メール送信禁止 / 外部サービスへの投稿禁止 / 個人情報を公開リポジトリへコミット禁止 / `raw/` の手動編集禁止。
- **現在進行中の未コミット作業がある**: `.github/workflows/daily-audio-brief.yml`、`scripts/daily-audio-brief/`、`scripts/generate_pulse_shortcut_config.py`、`scripts/test_generate_pulse_shortcut_config.py`(いずれも untracked)。**これらに触れないこと。**

### 2.4 workspace 構成

`~/workspace/` に約20プロジェクト。polymarket 関連は3箇所に存在:
1. `~/workspace/polymarket-signal-agent/`(agent.py 10K, tests/, docs/, data/)→ **所有者確認済み: これが正本**(§10 Q2)
2. `~/workspace/myLife-experiments/polymarket-signal-note-agent/`
3. `~/workspace/myLife/scripts/polymarket-signal-note-agent/`(agent.py, spike.py, fixtures, prompts, test_agent.py)

GitHub workflows から polymarket への参照は**ゼロ**(grep 確認済み)。`MYLIFE_POLYMARKET_EXPERIMENT_DIR` 環境変数を参照するのは `scripts/polymarket-signal-note-agent/agent.py` 自身のみ。

---

## 3. Behaviors To Preserve(絶対に壊してはいけない挙動)

1. **myLife の全 GitHub Actions ワークフロー**(28本)が現状のパス・スクリプト名で動くこと。ワークフロー YAML が参照するパスを変える場合は YAML 側も同一 PR で更新する。
2. **`raw/` は読取専用**。リファクタリングで `raw/` 配下を移動・編集・削除しない(`raw/Archive/` 含む)。
3. **`ops/state/` の同期状態ファイル**(`overcast_processed.txt` 等の旧名のものも含む)。削除・リネームすると**再取り込み・重複取り込みが発生**する。
4. **wiki の WikiLink 規約・frontmatter 規約**(myLife/CLAUDE.md 記載)。wiki ページの中身はリファクタ対象外。
5. **iOS Shortcut 連携**: `scripts/generate_*_shortcut*.py`、`save-research.sh`、`research-save.yml`/`note-clip.yml` 等の workflow_dispatch 入口。Shortcut 側は外部にあり修正できないため、**dispatch されるワークフロー名・inputs・スクリプトの CLI 引数は変更禁止**。
6. **myLife の Boundaries**: 投稿・送信系の自動化を追加しない。
7. **Claude Code のグローバル設定の有効性**: `~/.claude/settings.json` の hooks を壊さない(RTK hook 等)。settings 系の編集前に必ずタイムスタンプ付きバックアップを取る。
8. **open-slide ワークスペース**: 移設後も `slides/` の2デッキがビルドできること(baseline で npm / pnpm のどちらが正か確認して記録)。
9. **myLife の未コミット作業**(daily-audio-brief 一式)をステージ・コミット・削除・編集しない。
10. **正本 polymarket**(`~/workspace/polymarket-signal-agent/`)には一切触れない。

---

## 4. Non-Negotiables(作業規律)

- 作業開始時に各対象リポジトリで `git status` を確認し、結果を記録する。
- 既存の未コミット変更と自分の変更を**絶対に混ぜない**。myLife では既存 untracked ファイルに触れない。
- 編集前に Baseline Commands を実行し、結果(成功/失敗、失敗内容)を記録する。baseline で既に失敗しているものは「既知の失敗」として記録し、修正対象が明示されていない限り直さない。
- 変更は小さく、フェーズごとに独立して revert 可能な単位にする。1フェーズ = 1コミット(または1PR)。
- 無関係な整形・「ついで」のリファクタリングをしない。diff の全行がフェーズの目的に直結すること。
- 既存挙動を勝手に変えない。正しさが不明なら実装を止めて質問する(§5)。
- `~/.claude/settings*.json` を編集する場合は、編集前にタイムスタンプ付きコピーを `~/.claude/backups/refactor-<日付>/` に保存する。
- ファイル削除は「git 追跡状況」「他からの参照(grep)」「(重複削除の場合)正本との diff」を確認した証拠をログに残してから行う。

## 5. Stop And Ask Conditions(即停止して人間に質問する条件)

- iOS Shortcut が参照する可能性のあるワークフロー名・inputs・CLI 引数を変えたくなったとき。
- `ops/state/`・`raw/`・`wiki/pages/` 配下を変更したくなったとき。
- `~/.claude/settings.json` の hooks を変更したくなったとき。
- 削除候補ファイルへの参照が grep で1件でも見つかったとき(本書に記載済みの参照を除く)。
- **D9 で myLife 内 polymarket コピーに、正本に存在しない独自変更(diff)が見つかったとき**(消すと作業が失われる可能性)。
- **D11 で wiki-lint を blocking 化する前のローカル実行が失敗したとき**(コンテンツ起因の失敗を直すのは本リファクタの範囲外。失敗一覧を報告して指示を仰ぐ)。
- **D3 で settings.local.json の permissions に、機械的判断では安全と断定できないエントリが残ったとき**(削除せず「人間レビュー用リスト」に回す)。
- テストと実装が矛盾しているように見えたとき(テストを直さず質問する)。

---

## 6. Baseline Commands

実装前と各フェーズ後に実行し、結果を記録する。

```bash
# --- myLife ---
cd ~/workspace/myLife
git status --short            # 既存 untracked 4件(daily-audio-brief 一式)を確認
python3 scripts/run_tests.py  # 全テスト。baseline の pass/fail を記録
python3 scripts/lib/check_shared_lib_usage.py
python3 scripts/wiki-lint/lint.py
python3 scripts/wiki-lint/build_indexes.py
python3 scripts/wiki-lint/build_backlinks.py
python3 scripts/wiki-lint/publish_safety.py
# ↑ lint 系は D11(blocking 化)の前提。baseline で exit code を必ず記録

# --- home (open-slide) ---
cd ~
git status --short | head -5  # 全部 untracked であることを確認(これが現状)
npm run build                 # package-lock.json があるため npm。失敗したら pnpm build を試し、どちらが正か記録

# --- ~/.claude ---
ls -la ~/.claude/settings*.json
python3 -c "import json; d=json.load(open('/Users/maylac/.claude/settings.local.json')); p=d.get('permissions',{}); print({k: len(v) for k,v in p.items()})"
```

---

## 7. Debt Map

各項目: **根拠 / なぜ負債か / 影響範囲 / リスク / 改善案 / 検証 / 実装可否**

### D1. Karpathy Guidelines の多重定義(実装可・Phase 3)【決定: skill に一本化】
- **根拠**: `~/AGENTS.md`(全文)、`~/.claude/CLAUDE.md` 後半(全文再掲)、skill `karpathy-guidelines`。
- **なぜ負債か**: 同一テキストが毎セッション二重ロードされ、コンテキストを浪費。更新時に複数箇所の同期が必要。
- **改善案(確定)**: 正本 = **skill `karpathy-guidelines`**(§10 Q4 = (c))。
  - `~/.claude/CLAUDE.md` から Karpathy Guidelines 全文(「# Karpathy Guidelines」見出し以降のコピー部分)を削除し、「コーディング時の振る舞いは skill `karpathy-guidelines` を参照」という1〜2行に置き換える。
  - `~/AGENTS.md` の中身を同様の短いポインタに置き換える(**ファイル自体と symlink `~/CLAUDE.md` は残す**。消すと home 配下プロジェクトの指示が空になるため)。
  - skill 本体(`karpathy-guidelines`)の内容は一切変更しない。事前に skill の実体ファイルを読み、全文が含まれていることを確認してから他を削る。
- **リスク**: 中。skill は常時ロードされないため、ガイドラインの「常時適用」性は弱まる。これは所有者が承知の上の決定。
- **検証**: skill 実体に全文があること。`~/.claude/CLAUDE.md` と `~/AGENTS.md` にガイドライン本文が残っていないこと。symlink が生きていること(`readlink ~/CLAUDE.md`)。
- **実装可否**: **実装可**。

### D2. `~/.claude/AGENTS.md` と `~/.claude/CLAUDE.md` の役割不明瞭(提案のみ)
- **根拠**: 前者は ECC プラグイン v1.9.0 の説明書、後者は Workflow Orchestration。同階層に別内容で並存。
- **改善案**: ECC プラグイン管理下のファイルか確認した上で、手書き指示は CLAUDE.md 側に集約。**プラグイン由来か不明なため提案のみ**(提案メモに出所調査結果を書く)。

### D3. `~/.claude/settings.local.json` の肥大(105KB、permissions)(実装可・Phase 5)【決定: 今回整理する】
- **根拠**: `settings.local.json` 105.2KB、トップレベルキーは permissions のみ。
- **なぜ負債か**: 許可リストが無秩序に蓄積し、監査不能。意図しない広い許可が紛れるセキュリティ境界の問題。
- **改善案(確定)**: 段階的に安全な縮約のみ機械実行し、判断が要るものは人間レビューに回す。
  1. タイムスタンプ付きバックアップを `~/.claude/backups/refactor-<日付>/` に保存(必須)。
  2. **完全重複エントリの除去**(同一文字列の重複)。
  3. **包含関係で冗長なエントリの除去**: より広いルールに完全に包含される狭いルールのみ(例: `Bash(git status)` と `Bash(git status:*)` が併存 → 狭い方を除去)。判定に確信が持てないペアは触らない。
  4. **存在しないローカルパスを指すエントリの抽出**: パスが実在しないものをリスト化。**削除はせず**「人間レビュー用リスト」として `~/tasks/permissions-review.md` に出力(プロジェクトを将来 clone し直す場合があるため)。
  5. before/after のエントリ数・ファイルサイズを報告。
- **リスク**: 高(消しすぎると許可プロンプト多発)。→ 機械的に安全な (2)(3) のみ削除し、それ以外はリスト化に留めることでリスクを抑える。
- **検証**: 編集後に `python3 -c "import json; json.load(open('...settings.local.json'))"` で JSON 妥当性確認。permissions のキー構造(allow/deny/ask 等)が編集前と同一であること。Claude Code を1回起動して設定エラーが出ないこと。
- **実装可否**: **実装可**(上記の範囲内のみ)。

### D4. `~/.claude/` のバックアップファイル散乱(実装可・Phase 2)
- **根拠**: `settings.json.backup`(3バイト=実質空)、`settings.json.bak`、`settings.json.bak.20260527_193350`。
- **改善案**: 3ファイルを `~/.claude/backups/legacy/` へ移動(削除はしない)。
- **検証**: `settings.json` / `settings.local.json` 本体の diff がゼロ。
- **実装可否**: 実装可。

### D5. `$HOME` 直下の空 git リポジトリ(実装可・Phase 4)【決定: 撤去】
- **根拠**: `~/.git` が存在、`git ls-files` 0件、remote なし。所有者確認済み: 意図していない。
- **改善案(確定)**: 撤去前に最終確認として `cd ~ && git ls-files | wc -l`(0件)、`git stash list`(空)、`git log --oneline -3`(コミット有無)を記録。**コミットが1件でも存在したら停止して質問**。0件確認後、`~/.git` をディレクトリごと `~/.Trash/home-git-backup-<日付>/` へ移動(rm はしない)。
- **検証**: `cd ~ && git rev-parse --is-inside-work-tree` がエラーになること(workspace 配下の各リポジトリは引き続き正常に動くこと: `cd ~/workspace/myLife && git status` 成功)。
- **実装可否**: **実装可**(D6 の移設完了後に実行。順序厳守: 先に open-slide を移設してから .git を撤去)。

### D6. open-slide ワークスペースの `$HOME` 同居(実装可・Phase 4)【決定: workspace へ移設】
- **根拠**: `~/package.json`、`~/slides/`、`~/themes/`、`~/netlify.toml`、`~/vercel.json`、`~/tsconfig.json`、`~/open-slide.config.ts`、`~/package-lock.json`、`~/node_modules/`(存在する場合)、`~/README.md`(open-slide テンプレ由来)。
- **改善案(確定)**: `~/workspace/open-slide/` を新設し、上記一式 + `slides/` + `themes/` を移動。
  - 移設前に `~/.claude/skills/` と `~/.agents/`、home の `.claude/` 配下で `slides/`・`open-slide` への絶対パス参照を grep し、ヒットした参照を新パスに更新する(create-slide / apply-comments / slide-authoring 系 skill が候補)。
  - `~/README.md` は open-slide テンプレの内容なので一緒に移動する。ただし**移動前に内容を確認し、open-slide 以外の記述が混ざっていたら停止して質問**。
  - `~/AGENTS.md` / `~/CLAUDE.md`(symlink)は**移動しない**(home 全体への指示ファイルとして残す。D1 でポインタ化される)。
  - STL 3ファイル(mona2-case 等)は ZMK 関連のため `~/workspace/zmk-config-moNa2-v2/` 配下への移動を**提案メモに書くのみ**(zmk リポジトリの構成規約が不明なため)。
  - 移設後、新ディレクトリで `git init` するかは所有者判断のため**しない**(提案メモに記載)。
- **検証**: `cd ~/workspace/open-slide && npm install && npm run build`(または baseline で確認した正のコマンド)が成功。grep でホーム直下の旧パスを指す skill 参照が残っていないこと。
- **実装可否**: **実装可**。

### D7. myLife/CLAUDE.md(Schema)と scripts/ 実態の乖離(実装可・Phase 2)
- **根拠**: CLAUDE.md のディレクトリツリー(L67-87)に存在しないディレクトリが実在: `brain-pack/`, `career-map/`, `ci/`, `codex-pet/`, `content-pipeline/`, `decisions/`, `overcast-sync/`, `product-assembly/`, `resurface/`, `sync-health/`(`daily-audio-brief/` は未コミットのため除外)。
- **改善案**: CLAUDE.md のツリーを実態に合わせて更新。各ディレクトリの1行説明は README またはスクリプト docstring から**証拠に基づいて**書く。D8/D9 でディレクトリを削除する場合は削除後の姿に合わせる。あわせて L552 の Polymarket 行を正本パス `~/workspace/polymarket-signal-agent/` に更新する(D9)。
- **検証**: `ls scripts/` と CLAUDE.md ツリーの差分がゼロ(未コミットの daily-audio-brief を除く)。`python3 scripts/wiki-lint/lint.py` がエラーなく完走。
- **実装可否**: 実装可。

### D8. `scripts/overcast-sync/` が空殻(実装可・Phase 2)
- **根拠**: 中身は `__pycache__/` と空の `tests/` のみ。git 追跡ファイル0件。`raw/Archive/overcast-2026-06-01/` に退避記録あり。Pocket Casts へ移行済み。
- **改善案**: `scripts/overcast-sync/` ディレクトリのみ削除。`ops/state/podcast/overcast_*` は触らない。削除前に `grep -ri "overcast-sync" --include="*.py" --include="*.yml" .` で参照ゼロを再確認。
- **検証**: `python3 scripts/run_tests.py` が baseline と同結果。
- **実装可否**: 実装可(参照ゼロ確認を条件に)。

### D9. polymarket-signal-note-agent の三重存在(実装可・Phase 4)【決定: workspace 直下が正本】
- **根拠**: §2.4 の3コピー。CLAUDE.md L552 は「`../myLife-experiments/polymarket-signal-note-agent/`」と記載しており、決定された正本(`~/workspace/polymarket-signal-agent/`)とも実態とも食い違う。workflows からの参照ゼロ確認済み。
- **改善案(確定)**:
  1. `diff -r ~/workspace/myLife/scripts/polymarket-signal-note-agent/ ~/workspace/polymarket-signal-agent/` を実行(`__pycache__`, `.serena`, `data` は除外)。**myLife 側にしかない実質的な差分(コード・プロンプト・fixtures)があれば停止して質問**。
  2. 差分なし(または正本が新しい)と確認できたら `myLife/scripts/polymarket-signal-note-agent/` を git rm で削除。
  3. `~/workspace/myLife-experiments/polymarket-signal-note-agent/` も同様に diff 確認の上、**削除はせず**正本への移行が済んでいる旨を提案メモに記載(myLife-experiments は git 管理状況が未調査のため、削除は人間判断)。
  4. myLife/CLAUDE.md L552 のパスを `~/workspace/polymarket-signal-agent/`(`MYLIFE_POLYMARKET_EXPERIMENT_DIR` で上書き可、の記述は維持)に更新。
- **検証**: `python3 scripts/run_tests.py` が baseline と同結果(polymarket のテストが scripts/ から消えるため、テスト件数の減少は期待どおりであることを明記して報告)。
- **実装可否**: **実装可**(diff 確認を条件に)。

### D10. myLife ルート直下のフラットなスクリプト群(提案のみ)
- **根拠**: `scripts/generate_*_shortcut*.py` 4本(+未コミット1本)、`save-research.sh` が scripts/ 直下に平置き。
- **リスク**: 中〜高。iOS Shortcut・workflow がフルパス参照している可能性(Behaviors To Preserve #5)。
- **実装可否**: 提案のみ。移動しない。

### D11. wiki-lint CI の全ステップ `continue-on-error: true`(実装可・Phase 5)【決定: blocking 化】
- **根拠**: `.github/workflows/wiki-lint.yml` の lint/build_indexes/build_backlinks/lifecycle/provenance_graph/publish_safety/brain-pack 各ステップに `continue-on-error: true`。
- **改善案(確定)**: 段階的に blocking 化する。
  1. まずローカルで全 lint 系スクリプトを実行し、**現時点の exit code を記録**(Baseline Commands に含む)。
  2. **全部成功している場合のみ**、`continue-on-error: true` を各ステップから削除。
  3. 1つでも失敗している場合: 失敗がスクリプトのバグか wiki コンテンツ起因かを切り分けて**報告し、停止**(コンテンツ修正は本リファクタの範囲外)。
  4. brain-pack ステップは外部 API(Claude API)依存の可能性があるため、YAML を読んで API 呼び出しがある場合は **blocking 化の対象から除外し**、その旨を報告(API 障害で CI が赤くなるのは lint の意図と異なる)。レポート生成系で `git push` を伴うステップも同様に挙動を読んでから判断し、確信が持てなければ除外して報告。
- **検証**: 変更後に `workflow_dispatch` で wiki-lint.yml を手動実行し、成功すること(gh CLI: `gh workflow run wiki-lint.yml` → `gh run watch`)。
- **実装可否**: **実装可**(上記の条件分岐に従う)。

### D12. テストランナーが自作・pytest 不使用(提案のみ)
- **根拠**: `scripts/run_tests.py` が `test*.py` を逐次実行。依存ゼロで CI と相性が良く、意図的にシンプルにしている可能性が高い。
- **実装可否**: 提案のみ。現ランナーは壊さない。

### D13. `.venv_overcast/` が myLife ルートに残存(実装可・Phase 2)
- **根拠**: `~/workspace/myLife/.venv_overcast/` が存在。overcast は廃止済み(D8)。
- **改善案**: `git ls-files | grep venv_overcast`(0件)を確認の上、ローカル削除。追跡されていた場合は停止して質問。あわせて `.gitignore` に `.venv_overcast/` を追加する必要はない(削除するため)。
- **実装可否**: 未追跡確認を条件に実装可。

### D14. `~/.claude/rules/` 内の陳腐化した記述(提案のみ)
- **根拠**: `rules/common/performance.md` が「Opus 4.6 — Deepest reasoning」と記載(現行は Opus 4.8 / Fable 5)。
- **改善案**: rules 群は ECC プラグイン由来の可能性があるため**出所を確認して提案メモに報告するのみ**。

---

## 8. Implementation Phases

> 各フェーズ完了ごとに §9 の検証を行い、1コミット(リポジトリ外の変更は1作業ログ)単位で記録する。
> 条件未達(diff あり・lint 失敗等)のフェーズは Stop And Ask に従って停止または部分スキップし、報告に明記する。

### Phase 0 — 現状確認(変更なし)
1. `git status` を home / myLife の両方で実行・記録。
2. §6 Baseline Commands を全て実行し、結果を `~/tasks/refactor-baseline.md` に記録(lint 系の exit code を必ず含める)。
3. myLife の未コミット4ファイルを「不可侵リスト」として記録。
- **verify**: baseline 記録が存在し、各コマンドの成否が明記されている。

### Phase 1 — 安全網と削除前提の確認
1. `python3 scripts/run_tests.py` の baseline 結果確認(fail があれば一覧記録、修正はしない)。
2. 参照 grep を実行し記録: `overcast-sync` / `venv_overcast` / `polymarket`(workflows・scripts・skills・README)。
3. D9 の diff: myLife 内コピー vs 正本 `~/workspace/polymarket-signal-agent/`。差分の有無を記録。
- **verify**: 参照調査ログと diff 結果がある。

### Phase 2 — 明らかに安全な整理(myLife + ~/.claude、低リスク)
1. **D8**: `scripts/overcast-sync/` 削除(参照ゼロ確認済みの場合のみ)。
2. **D13**: `.venv_overcast/` ローカル削除(未追跡確認済みの場合のみ)。
3. **D7**: myLife/CLAUDE.md の scripts ツリーを実態に同期(daily-audio-brief は除外。D9 の削除を先に行う場合は削除後の姿で書く)。
4. **D4**: `~/.claude/settings.json.backup` / `.bak` / `.bak.20260527_193350` を `~/.claude/backups/legacy/` へ移動。
- **verify**: `run_tests.py` baseline 同等。`lint.py` 完走。settings 本体 diff ゼロ。
- **commit**: myLife 側は1コミット(例: `chore: remove dead overcast-sync, sync CLAUDE.md schema tree`)。

### Phase 3 — Karpathy Guidelines の一本化(D1)
1. skill `karpathy-guidelines` の実体ファイルを読み、全文が含まれることを確認。
2. `~/.claude/CLAUDE.md` のコピー部分を削除しポインタ化。
3. `~/AGENTS.md` をポインタ化(symlink `~/CLAUDE.md` は維持)。
- **verify**: 本文が skill のみに存在。`readlink ~/CLAUDE.md` が `AGENTS.md` を指す。

### Phase 4 — フォルダ構成の是正(D6 → D5 → D9 の順)
1. **D6**: open-slide 一式を `~/workspace/open-slide/` へ移設。skill 内パス参照を grep・更新。移設後にビルド確認。
2. **D5**: home の git メタデータ最終確認(`git log` にコミットがあれば停止)→ `~/.git` を `~/.Trash/home-git-backup-<日付>/` へ移動。
3. **D9**: diff 確認済みなら myLife 内 polymarket コピーを `git rm`。CLAUDE.md L552 のパス更新(D7 と同一コミットでも可)。
- **verify**: 新パスで open-slide ビルド成功。`cd ~ && git rev-parse --is-inside-work-tree` が失敗。`cd ~/workspace/myLife && git status` 正常。`run_tests.py` の件数減が polymarket テスト分のみであること。

### Phase 5 — 高リスク項目(条件付き実装)
1. **D11**: lint 系の baseline が全部成功している場合のみ `continue-on-error` を除去(brain-pack 等の API 依存・push 伴うステップは除外判断)。`gh workflow run wiki-lint.yml` で動作確認。
2. **D3**: settings.local.json のバックアップ → 完全重複と包含冗長の除去 → 実在しないパスのエントリは `~/tasks/permissions-review.md` にリスト化(削除しない)→ before/after 報告。
- **verify**: wiki-lint workflow_dispatch 成功。settings.local.json が valid JSON で構造不変。

### Phase 6 — 提案書の作成(実装しない)
1. **D2, D10, D12, D14** + STL 移動 + open-slide の git init 要否 + myLife-experiments 内 polymarket の削除可否について、証拠を引用した提案メモを `~/tasks/refactor-proposals.md` に書く。
- **verify**: 各提案に「やる場合の手順」「リスク」「確認すべき相手」が書かれている。

---

## 9. Verification Requirements

- 各フェーズ後: `cd ~/workspace/myLife && python3 scripts/run_tests.py` → baseline と同結果(Phase 4 の polymarket テスト減のみ例外、その旨明記)。
- myLife を変更したフェーズ後: `python3 scripts/wiki-lint/lint.py` と `python3 scripts/lib/check_shared_lib_usage.py` が完走。
- `git status` で意図しないファイルがステージ/変更されていないこと(特に myLife の未コミット4ファイルが無傷であること)。
- `~/.claude` を変更したフェーズ後: settings 系が valid JSON であること、hooks 設定が不変であること。
- ファイル削除・移動を行った場合: 事前の grep ログ / diff ログが報告に含まれていること。
- D11 実施時: `gh workflow run wiki-lint.yml` の実行結果(run URL と結論)。

## 10. 所有者の決定事項(2026-06-12 確定)

| # | 質問 | 決定 |
|---|------|------|
| Q1 | `$HOME` の空 git リポジトリと open-slide 同居 | 意図していない。**(a) `~/.git` 撤去 と (b) open-slide を workspace へ移設 の両方を実行** |
| Q2 | polymarket の正本 | **`~/workspace/polymarket-signal-agent/`(workspace 直下)が正本**。myLife 内コピーは diff 確認の上削除、CLAUDE.md のパス参照を更新 |
| Q3 | wiki-lint CI の `continue-on-error` | **blocking 化する**(段階的手順 D11 に従う) |
| Q4 | Karpathy Guidelines の正本 | **(c) skill `karpathy-guidelines` のみ**。他はポインタ化 |
| Q5 | settings.local.json(105KB)の整理 | **今回実施**(D3 の安全な範囲のみ機械実行、それ以外はレビュー用リスト化) |

## 11. Reporting Format

作業完了時(または中断時)に以下を報告する:

```
## 実施フェーズ
- Phase N: 完了/スキップ/部分実施(理由)

## Baseline 結果
- run_tests.py: <pass/fail 詳細>
- lint 系 exit code 一覧
- (その他コマンドと結果)

## 変更一覧
- <ファイル>: <変更内容1行>(コミット hash / リポジトリ外は作業ログ)

## 削除・移動の証拠
- <ファイル>: grep ログ・git 追跡確認・diff 結果の要約

## settings.local.json
- before/after エントリ数・サイズ、レビュー用リストの場所

## 最終検証
- 最後に実行したコマンドと結果(そのまま貼る)

## 未解決・停止した項目
- Stop And Ask に該当した内容と、人間に確認したい点
```

## 12. Out-of-scope Items(本リファクタで触らないもの)

- `myLife/raw/`、`myLife/wiki/pages/` 配下の全コンテンツ(知識データそのもの)。lint がコンテンツ起因で失敗してもコンテンツは直さない。
- `myLife/ops/state/` の状態ファイル。
- myLife の未コミット作業(daily-audio-brief 一式、generate_pulse_shortcut_config.py + test)。
- `~/workspace/polymarket-signal-agent/`(正本。読み取り・diff 比較のみ可)。
- `~/workspace/myLife-experiments/` の削除(diff 確認と提案メモのみ)。
- `~/.claude/settings.json`(local でない方)の permissions・hooks の中身。
- `~/.claude/agents/`(28個)・`~/.claude/skills/`(123個)・`~/.claude/rules/` の棚卸し(別タスク)。
- workspace 内の他プロジェクト(zmk-config, twitter, mf-dashboard 等)。STL ファイルの移動(提案のみ)。
- GitHub Actions の cron スケジュール・Secrets・外部 API 連携の変更。
- pytest への移行(提案のみ)。
