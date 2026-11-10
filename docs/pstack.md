# pstack 導入メモ

[pstack-claude](https://github.com/michael-denyer/pstack-claude) は、Lauren Tan の pstack を Claude Code と Codex などに移植したプラグインです。ここではネイティブのプラグインとして導入し、`pstack:` の名前空間に入れています。既存の共有スキル（`unslop` など）や `autonomous-team` は置き換えず、そのまま残っています。

## 導入した版

- バージョン: 0.9.126
- ソースのコミット: `c37118f3b5861cc12b2400403dab2015e5cc5930`
- 内容: スキル 67 個、エージェント 4 個。プラグイン本体は外部の MCP サーバーを追加しません。
- 導入しただけで、実際のタスクはまだ実行していません。

## 呼び出し方

- Claude: `/pstack:poteto-mode [目的]`
- Codex: `$pstack:poteto-mode [目的]`。または「pstack の poteto-mode を使って〜して」と依頼します。

Claude の新規セッションで67スキル・4エージェントの読み込みと、起動フックの正常終了を確認しました。Codex も67スキルを `enabled: true` で検出しました。Codex の起動フックは `untrusted` のため自動ルーティングは未有効です。信頼設定は変更しておらず、スキルの明示呼び出しは使えます。

## 復元手順

ソースを固定コミットで取得してから、公式 CLI で登録します。

```sh
git clone https://github.com/michael-denyer/pstack-claude "$HOME/workspace/tools/pstack-claude"
git -C "$HOME/workspace/tools/pstack-claude" checkout c37118f3b5861cc12b2400403dab2015e5cc5930
claude plugin marketplace add "$HOME/workspace/tools/pstack-claude"
claude plugin install pstack@pstack-claude --scope user
codex plugin marketplace add "$HOME/workspace/tools/pstack-claude"
codex plugin add pstack@pstack-claude
```

## 依存とモデル

- 一部の発展的なワークフローは外部コマンドを使います。PR の監視や出荷は `gh`、`watch-pr` スクリプトは Bun、`statechart` は初回に mise で TLC と Java を入れます（ネットワークが必要）。使う前に `command -v gh` などで存在を確かめてください。
- 上流の既定では、Claude 側に `fable` や `sonnet`、Codex 側に `gpt-6.1-sol` などのモデルが役割ごとに割り当てられています。この導入ではモデル設定を変えていません。グローバル設定と AGENTS.md で指定したモデル、権限、サンドボックスの設定が優先されます。

## 参考

- [README](https://github.com/michael-denyer/pstack-claude/blob/c37118f3b5861cc12b2400403dab2015e5cc5930/README.md)
- [docs/reference.md](https://github.com/michael-denyer/pstack-claude/blob/c37118f3b5861cc12b2400403dab2015e5cc5930/docs/reference.md)
