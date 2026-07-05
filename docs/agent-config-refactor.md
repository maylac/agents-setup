# agent-config-refactor.md — エージェント設定ファイル群の修正方針

> 作成: 2026-06-13。`~` 配下のエージェント設定(skills / hooks / plugins / CLAUDE.md / AGENTS.md / settings / rules / agents / commands)を実際に読んで作成。
> 実装時は「/goal agent-config-refactor.md に書かれたことを完遂しろ」で渡せる形式。
> 2026-06-12 の `~/refactor-instructions.md`(ホーム構成リファクタ)は **大部分実施済み**(~/.git 撤去 ✓ / open-slide 移設 ✓ / ~/AGENTS.md・~/.claude/CLAUDE.md のポインタ化 ✓ / settings バックアップ退避 ✓)。本書はその**残件と新たに発見した負債**を扱う。

---

## 1. 現状マップ(2026-06-13 実測)

### 指示ファイルの正本関係

| ファイル | 内容 | 状態 |
|---------|------|------|
| `~/AGENTS.md`(`~/CLAUDE.md` → symlink) | Karpathy へのポインタ(5行) | ✅ 一本化済み |
| `~/.claude/CLAUDE.md` | Workflow Orchestration + `@RTK.md` + Karpathy ポインタ | ✅ ポインタ化済み |
| `~/.codex/AGENTS.md` | **Karpathy Guidelines 全文が残存** | ❌ 一本化漏れ |
| skill `karpathy-guidelines`(`~/.agents/skills/`) | Karpathy 正本(所有者決定 2026-06-12) | ✅ 正本 |
| plugin `andrej-karpathy-skills@karpathy-skills` | **同内容の skill を二重提供** | ❌ 重複 |
| `~/.claude/AGENTS.md` | ECC v1.9.0 プラグイン説明書(10KB) | ⚠️ 役割曖昧 |
| `~/.claude/rules/common/`(9ファイル) | 毎セッションロードされる共通ルール | ⚠️ 一部陳腐化 |

### 実行系

- **hooks(有効、settings.json 内)**: PreToolUse=`rtk-rewrite.sh`(rtk 実在確認済み `/opt/homebrew/bin/rtk`)、Stop/Notification=Ghostty activate、Elicitation/PermissionRequest=サウンド。→ 正常稼働、触らない。
- **hooks(休眠)**: `~/.claude/hooks/hooks.json` — `${CLAUDE_PLUGIN_ROOT}` 前提の ECC テンプレで、settings.json から参照されておらず**無効**。混乱の元。
- **plugins(6個有効)**: discord / imessage / codex / clangd-lsp / andrej-karpathy-skills / frontend-design。
- **skills**: 正本 `~/.agents/skills/` 124個、`~/.claude/skills/` と `~/.codex/skills/` は symlink で一致 ✅。うち **`source-command-*` が22個** — `~/.claude/commands/`(63個)の鏡写しで二重管理。
- **agents**: `~/.claude/agents/` 28個(ECC 由来)。
- **settings.local.json**: **102.6KB、allow 146エントリ**。完全重複は0件だが、**最大 9,939文字の heredoc コマンド全文**がそのまま許可エントリになっているものが上位を占める(一回限りのコマンドで二度とマッチしない死エントリ)。Bash 123 / WebFetch 12 / その他11。

---

## 2. 修正方針(優先度順)

### P1. Karpathy 一本化の完遂【即実施可・低リスク】

1. `~/.codex/AGENTS.md` の Karpathy 全文を、`~/AGENTS.md` と同じ5行ポインタに置き換える(Codex は skill `karpathy-guidelines` を `~/.codex/skills/` 経由で参照可能)。置換前に現行ファイルを `~/.claude/backups/refactor-20260613/` へコピー。
2. plugin `andrej-karpathy-skills@karpathy-skills` を無効化する(`settings.json` の `enabledPlugins` で `false`)。理由: ローカル skill が正本(所有者決定済み)で、plugin 版と二重に skill 一覧へ載りコンテキストを浪費。
   - **逆案**(plugin を正本にしてローカル skill を消す)もあるが、ローカル版は Codex と共用の `~/.agents/skills/` 体系に乗っており、こちらを正本とする方が一貫する。
- **検証**: 新セッションの skill 一覧に karpathy-guidelines が1つだけ載る。`grep -r "Think Before Coding" ~/AGENTS.md ~/.claude/CLAUDE.md ~/.codex/AGENTS.md` が0件(全文がどこにも残らない)。

### P2. settings.local.json の減量【即実施可・要バックアップ】

方針: **機械的に安全なものだけ削除し、判断が要るものはリスト化**(2026-06-12 所有者承認の範囲)。

1. タイムスタンプ付きバックアップを `~/.claude/backups/refactor-20260613/` に保存(必須)。
2. **削除可**: `Bash(...)` エントリのうち ①改行を含む(heredoc 等の複数行コマンド全文) ②500文字超 のもの。これらは一回限りのコマンド固有文字列であり、将来の許可マッチに再利用されることが事実上ない。
3. **リスト化のみ(削除しない)**: 実在しないローカルパスを含むエントリ(例: `~/data-reporting-pipeline/...`)→ `~/tasks/permissions-review.md` に出力して人間レビュー。
4. before/after のエントリ数・ファイルサイズを報告。編集後に `python3 -c "import json; json.load(open(...))"` で妥当性確認。
- **期待効果**: 102.6KB → 大幅減(上位5エントリだけで約43KB)。
- **検証**: valid JSON / `permissions` 構造不変 / Claude Code 起動エラーなし。

### P3. source-command-* スキル22個の整理【推奨案あり・実施前に1点確認】

- **問題**: `~/.agents/skills/source-command-*` 22個は `~/.claude/commands/` の鏡写し(ECC 由来)。skill 一覧を肥大させ、同名機能が「skill」と「command」の二経路に見える。
- **推奨**: commands/ を正本として `source-command-*` スキル22個を削除(`~/.agents/skills/` から削除すれば symlink 経由で Claude/Codex 両方から消える)。
- **実施条件**: 削除前に各 `source-command-X/SKILL.md` と `commands/X.md` を diff し、**skill 側にしかない内容があれば停止して報告**(commands 側へ取り込んでから削除)。Codex が commands/ を読めない環境で skill 版だけが Codex 用という可能性があるため、`~/.codex/` に commands 相当の仕組みがあるかを確認し、無ければ削除対象を「Claude commands と完全一致するもののみ」に絞る。
- **検証**: skill 一覧から source-command-* が消え、`/agmsg` 等のコマンドは引き続き動く。

### P4. ECC 残骸の整理【即実施可(退避のみ)・削除はしない】

- **対象**: `~/.claude/` 直下の `plugin.json` / `marketplace.json` / `program.md` / `PLUGIN_SCHEMA_NOTES.md` / `AGENTS.md`(ECC 説明書)/ `hooks/hooks.json`(休眠)。
- **方針**: ECC は plugin としてではなくファイル展開で導入されており、これらは現在の動作に寄与していない(hooks.json は `${CLAUDE_PLUGIN_ROOT}` 未解決で無効、AGENTS.md は Claude Code が自動ロードしない)。`~/.claude/docs/ecc/` を作りそこへ移動(削除しない)。`hooks/rtk-rewrite.sh` は**現役なので残す**。
- **実施条件**: 移動前に `grep -r "program.md\|PLUGIN_SCHEMA_NOTES\|hooks/hooks.json" ~/.claude/settings*.json ~/.claude/commands ~/.agents/skills --include="*.md" -l` で参照ゼロを確認。1件でも参照があれば停止。
- **検証**: 次セッションで hooks(rtk / Ghostty / サウンド)が正常動作。

### P5. rules/common の鮮度修正【小修正のみ実施可】

- `performance.md`: モデル記述が陳腐化(「Opus 4.6 — Deepest reasoning」等。現行は Opus 4.8 / Fable 5 / Sonnet 4.6 / Haiku 4.5)。**モデル名と ID の記述のみ現行に更新**。方針論(使い分けの考え方)は変えない。
- `agents.md`: エージェント一覧表が `~/.claude/agents/` の実体28個と一致するか突き合わせ、乖離があれば表を実体に合わせる(実体側は変更しない)。
- それ以外の common ルール(coding-style / testing 80% / security 等)は**内容の当否に踏み込まない**(所有者の方針そのものなので、変更提案は別途リストで提示のみ)。
- 言語別 rules(csharp / perl / php / swift 等、現在使っていない可能性のある言語)は**削除しない**。未使用言語ディレクトリの一覧を報告に含め、所有者判断に委ねる。

### P6. skills 124個の棚卸し【提案のみ・本書では実施しない】

- description が壊れている skill が存在する(例: `defense-in-depth: Skill`、`root-cause-tracing: Skill` — 説明文がプレースホルダのまま)。一覧を報告に含める。
- 棚卸しは既存の `/skill-stocktake`(Quick Scan / Full Stocktake)を所有者が実行するのが適切。本書では**対象リストの作成まで**。

---

## 3. 作業規律(Non-Negotiables)

- `~/.claude/settings*.json` を編集する前に必ず `~/.claude/backups/refactor-20260613/` へタイムスタンプ付きコピー。
- 削除は P3 の source-command-* のみ(diff 確認条件付き)。それ以外は**移動・退避**で対応し、rm しない。
- `settings.json` の hooks(rtk-rewrite / Ghostty / サウンド)と `enabledPlugins` の P1 以外の項目に触れない。
- 各フェーズ後、新しい Claude Code セッションを起動して設定エラー・hook 動作を確認する。
- 1フェーズ=1作業ログ。最後に実行したコマンドと結果を報告する。
- 正しさが不明な場合(参照が見つかった、diff に差分があった)は停止して質問する。

## 4. 実施順序

1. P1(Karpathy 完遂)→ 2. P2(settings 減量)→ 3. P4(ECC 退避)→ 4. P3(source-command 整理、確認条件付き)→ 5. P5(rules 鮮度)→ 6. P6(棚卸しリスト作成)

## 5. 検証コマンド

```bash
# Karpathy 残存チェック(P1 後: 0件であること)
grep -rl "Think Before Coding" ~/AGENTS.md ~/.claude/CLAUDE.md ~/.codex/AGENTS.md 2>/dev/null

# settings 妥当性(P2 後)
python3 -c "import json, os; d=json.load(open(os.path.expanduser('~/.claude/settings.local.json'))); print(len(d['permissions']['allow']),'entries')"

# symlink 整合(P3 後)
ls ~/.claude/skills | wc -l; ls ~/.codex/skills | wc -l; ls ~/.agents/skills | wc -l

# hooks 動作(P4 後、新セッションで)
# Bash ツール実行時に rtk 書き換えが効くこと、Stop 時に Ghostty が前面に来ること
```

## 6. 触らないもの(Out-of-scope)

- `~/.claude/settings.json` の hooks・env・statusLine(P1 の enabledPlugins 1行を除く)。
- `~/.claude/projects/`(セッション・メモリ)、`history.jsonl`、`file-history/`、`shell-snapshots/` 等の運用データ。
- `~/.codex/config.toml`・`fugu-*.toml`(Codex のモデル設定。エージェント指示ファイルではない)。
- `~/.claude/agents/` 28個の中身(モデル指定の見直しは P6 のリストで提案のみ)。
- 各プロジェクト配下の `.claude/`・CLAUDE.md(プロジェクト固有設定は対象外。myLife は別指示書)。
- rtk / RTK.md の仕組み(現役 hook)。

## 7. 報告フォーマット

```
## 実施フェーズ: P1〜P6 の完了/スキップ(理由)
## settings.local.json: before/after(エントリ数・KB)、削除エントリの種別内訳、レビューリストの場所
## source-command-*: diff 結果と削除/保留の一覧
## ECC 退避: 移動したファイルと参照ゼロ確認の grep ログ
## 棚卸しリスト: 壊れた description の skill 一覧 / 未使用言語 rules 一覧
## 最終検証: §5 のコマンド出力そのまま + 新セッションでの hook 動作確認結果
## 未解決・停止した項目
```
