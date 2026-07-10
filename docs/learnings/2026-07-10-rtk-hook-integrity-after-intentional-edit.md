# RTKフックを意図的に変更した後のintegrity復旧

- 日付: 2026-07-10
- 領域: agents-setup / RTK PreToolUse hook
- 種別: debugging

## 問題

`rtk-rewrite.sh`へpush/force-pushの承認境界を追加した直後、以降のRTK対象コマンドが「hook integrity check FAILED」で停止した。フック本体は意図どおりだったが、`~/.claude/hooks/.rtk-hook.sha256`と`~/.codex/hooks/.rtk-hook.sha256`が旧内容のhashを保持していた。

## 試して駄目だった道

- フック本体だけを更新してテストを続けた: integrity guardが先に発火するため、正しい新ロジックまで到達しなかった。
- `rtk init -g --auto-patch`で直そうとした: 意図的に追加したローカル安全判定を上流テンプレートで上書きする可能性があるため採用しなかった。

## 効いたアプローチ

1. `/usr/bin/shasum -a 256`で実際にロードされるフックのhashを取得した。
2. Claude/Codex双方のread-only hashファイルを一時的に書き込み可能にし、新hashへ更新後、再びread-onlyへ戻した。
3. repoのClaude/Codexフック、`~/.agents/hooks`、`~/.codex/hooks`が同一hashであることを確認した。
4. `rtk verify`とフック回帰テストを実行し、integrityと141件のRTKテストを通した。

## なぜ効いたか

RTKはフックの実行前に、隣接するhashファイルを信頼基準として内容を照合する。したがって意図的なフック変更は、コード変更とtrust metadata更新を一つの原子的な変更として扱わない限り、改ざんと区別できない。

## 一般化できる原則

- integrityで保護されたhookを変更する場合、実体・全ミラー・trust hash・検証コマンドを同じ変更単位で更新する。
- 自動再初期化コマンドを使う前に、ローカル差分を上書きしないことを確認する。
- 完了条件はファイル一致だけでなく、integrity verifierと実際のhook回帰テストの両方が通ることとする。
