# selfimprove — ハーネス自己改善エコシステム

Claude Code環境(ハーネス)そのものを継続的に改善する仕組み。設計の出発点は
[takasekの3分類](https://x.com/takasek/status/2074359553815400770):

- **① 腐敗検知** — skill / memory / hooks / permissions / CLAUDE.md / 外部pin / launchd の7系統を監査
- **② 教訓定着** — セッションの試行錯誤を lint / CLAUDE.md / skill / memory に振り分けて固定
- **③ 外部知見取り込み** — 蒸留元URLを台帳化して定例巡回し、採否をログに残す

## 設計原則

1. **決定的な検査はスクリプト、判断だけモデル** (Anthropic loops記事)。週次の腐敗検知は
   `rot_check.py`(stdlibのみ・LLM不要・トークン0)が行い、レポートの読解と修正判断だけを
   エージェントセッションで行う。
2. **モデル非依存で生き残る**。判断手順はすべて `/self-improve` スキルのチェックリストとして
   焼き込んであり、Opus / Sonnet / Codex いずれでも実行できる。特定モデル(Fable等)の
   サブスク終了に依存しない。
3. **見送り判断こそ資産**。採用したものは adoption-log に「行き先」まで、見送ったものは
   rejection-log に「理由と再評価条件」まで書く。次に同じ情報に出会ったとき再検討を繰り返さない。
4. **既存資産を呼ぶ、複製しない**。深掘り監査は `harness-audit` / `skill-stocktake`、
   許可整理は公式 `/fewer-permission-prompts`、解法記録は `extract-approach`、
   スキル化は `skill-create` に委譲する。本システムはそれらの「配車係+台帳」に徹する。

## 構成

```
selfimprove/
├── README.md              # この設計書 兼 運用手順
├── ledger/
│   ├── sources.md         # ③ 蒸留元台帳 (cadenceと巡回期限)
│   ├── adoption-log.md    # ③ 採用ログ (行き先まで記録)
│   └── rejection-log.md   # ③ 見送りログ (理由と再評価条件)
├── scripts/
│   ├── rot_check.py       # ① 7系統の決定的チェック + 台帳期限チェック
│   ├── rot_check_weekly.sh # launchd用ラッパー (通知付き)
│   └── install_launchd.sh # launchdジョブの登録 (テンプレートをレンダリング)
├── launchd/
│   └── com.maylac.selfimprove-rot.plist.template  # __HOME__ 置換して配置
└── reports/               # rot-YYYY-MM-DD.md (gitignore、直近のみ残す)
```

判断レイヤーは skill `self-improve`(正本 `~/.agents/skills/self-improve`、
sync-skills.sh で Claude/Codex 両方へ symlink)。

## 運用サイクル

| 頻度 | 何が | 誰が | 内容 |
|---|---|---|---|
| 週次(月曜08:30) | launchd `com.maylac.selfimprove-rot` | スクリプト | rot_check.py実行→レポート出力。findingsか巡回期限があればmacOS通知 |
| 通知が来たら | `/self-improve` | 任意モデル | レポートを読み、findings修正 + 期限が来た③巡回 |
| 随時(教訓が溜まったら) | `/self-improve distill` | 任意モデル | lessons.md等を行き先に振り分け+圧縮 |
| 月次(月初) | `/self-improve full` | Opus推奨 | 上記全部 + skill-stocktake(Full) + fewer-permission-prompts |

## ②のルーティング表 (教訓の行き先)

上の行き先ほど強い(実行時強制 > 常時注入 > 条件発火 > 想起)。**lintにできる教訓をCLAUDE.mdに書かない**。

| 教訓の性質 | 行き先 |
|---|---|
| コマンドで機械的に判定できる | hook / lint / スクリプト (post-write-check.sh, rot_check.py, CI) |
| 全セッションで常に効くべき短い行動規範 | CLAUDE.md / rules/*.md (行数予算内、既存ルールとの矛盾を先に確認) |
| 特定状況で発火する長い手順 | skill (skill-create経由で正本に作成) |
| ユーザー・環境の事実 | auto-memory |
| 解法・設計判断の記録 | extract-approach (docs/learnings / ~/tasks/learnings) |

## 既存資産との境界

- **fable5** (`~/workspace/fable5`): ワークフロー実行内(ランタイム層)の自己改善。本システムは
  ハーネス層。思想(判断はログに・資産はファイルに)は共有、コードは共有しない
  (rejection-log 2026-07-08 参照)。
- **hermes** (`~/workspace/hermes-hub`): 汎用タスクオーケストレーション。selfimproveの修正作業が
  大きくなったらタスクYAMLとしてhermesに載せてよいが、台帳と判断ログはここが正本。
- **improvement-backlog.md** (`~/tasks/`): 業務プロセス改善の台帳。こちらはハーネス資産専用。

## セットアップ / 復旧

```sh
# launchd登録 (初回 or 復旧時)
zsh scripts/install_launchd.sh

# 手動実行
python3 scripts/rot_check.py
```
