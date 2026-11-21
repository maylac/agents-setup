# autonomous-team 運用ガイド

X の投稿（[本文](https://x.com/claudecode84/status/2117494886744404205)、[リンク先の記事](https://x.com/claudecode84/status/2115647088134377843)）にある「リーダーが小さな仕事を分けて渡し、結果を検証してから完了とする」進め方を、既存の Claude Code と共有スキルで実装したものです。詳しい手順は `skills/autonomous-team/SKILL.md` にあります。

## 呼び出し方

- Claude: `/autonomous-team [目的]`
- Codex: `$autonomous-team [目的]`

## 構成

| 要素 | 役割 |
| --- | --- |
| `skills/autonomous-team/` | 進め方の手順と、呼び出しからセッション終了まで有効な hook。ゲート用ヘルパーで証跡を照合する |
| `claude/agents/team-worker.md` | 実装担当のサブエージェント。メインのモデルを継承し、effort は medium、`isolation: worktree`、`maxTurns: 25` |
| `claude/agents/code-reviewer.md` | 統合後の差分を読むだけのレビュー担当 |

## リーダー（メインセッション）の手順

1. 目的、担当ファイル（owned paths）、実行できる受け入れコマンド、依存関係、基準コミットの SHA を決め、`init` で登録します。ディレクトリの担当範囲は `src/` のように末尾へ `/` を付けます。Claude は実際の `${CLAUDE_SESSION_ID}` を使い、1つの会話で1つのタスクを扱います。担当ファイルに未コミットの変更があれば開始を止めます。
2. 互いに依存しない小さな仕事だけを `team-worker` に渡します。Claude の worktree は既定でデフォルトブランチから作られることがあるため、ワーカーが報告した基準 SHA が意図したものかを確かめます。
3. ワーカーの差分を確認し、契約にあるパスだけを統合します。無関係な変更が混ざっていないことも確かめます。
4. 統合後の実際の作業ツリーに対して、リーダーの Bash から `check` で受け入れコマンドを実行します。サンドボックスは有効なままです。
5. `snapshot` で対象のハッシュを取得し、`code-reviewer` にそのハッシュと統合後の差分を渡します。レビュー結果に `Snapshot: ハッシュ` を含め、`review --snapshot` で対象が変わっていないことを確認します。
6. 失敗したタスクだけをワーカーに差し戻します。別の方法を試すのは 2 回までとし、それでも直らなければ `blocked` で止めます。
7. `finish` で終了状態を記録します。

## 終了状態

- `ready`: 現在のスナップショットで受け入れコマンドとレビューが通った
- `blocked`: 解決できない失敗が残った
- `approval-required`: マージ、デプロイ、公開など、人の承認が必要な操作が残った

`blocked` と `approval-required` は正当な報告であり、成功ではありません。レビューで指摘が出た状態は、レビュー通過として扱いません。

## hook の動き（Claude のみ）

- **PreToolUse（Bash）**: force push、履歴の書き換え、デフォルトブランチへのマージ、PR のマージ、デプロイ、公開といった、よくある高リスクのシェル操作の前に承認を求めます。自動で許可することはありません。
- **Stop**: 証跡、担当範囲、スナップショット、レビューを確認します。受け入れコマンドは実行しません。未検証なら停止を最大2回まで止め、その後は利用者に「未検証」の警告を表示して停止を許します。警告は、モデルの最終文面が正しいことを保証するものではありません。
- Stop は `init` していなければ動きません。Bash の承認フックは、スキルを呼び出したセッションの残りの期間も有効です。

## Codex での使い方

スキルの hook は Claude でしか動きません。Codex は `$HOME/.agents/skills/autonomous-team/scripts/team_gate.py` を明示的に呼び、任意のタスク ID を `--session` に渡します。実装は `gpt-6-luna` ワーカーに任せ、メインの `gpt-6-astra` が判断と統合を受け持ちます。サンドボックスと承認ポリシーはそのまま使います。

## 制約

この仕組みは既存の安全策を補うものです。Bash hook のパターン照合は、シェル操作の完全なセキュリティ境界にはなりません。Git の無視対象ファイル、サブモジュール内部の未コミット変更、実行環境の変更はスナップショットの対象外です。OS のサンドボックス、権限設定、グローバル設定は変更せず、サービスの再起動も行いません。共有スキルストアから Claude と Codex にリンクして使います。

## 参考

- [Claude Code: Subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code: Hooks in skills and agents](https://code.claude.com/docs/en/hooks#hooks-in-skills-and-agents)
- [X の投稿](https://x.com/claudecode84/status/2117494886744404205) / [リンク先の記事](https://x.com/claudecode84/status/2115647088134377843)
