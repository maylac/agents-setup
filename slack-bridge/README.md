# slack-bridge

Mac mini 上で GitHub Issue の契約を受け取り、許可されたリポジトリの作業用 worktree でエージェントを実行する bridge です。GitHub transport では、既存の `gh` ログインを使います。Slack transport もサポートします。設定、認証、launchd の変更は運用者が明示的に行います。

## 診断

```sh
python3 slack-bridge/doctor.py
python3 slack-bridge/doctor.py --check-github
```

診断は既定で `~/.config/slack-bridge/env` をデータとして読み、必須キーの有無、許可パス、CLI、macOS launchd の状態を JSON で報告します。env ファイルを shell として読み込まず、値や認証情報も表示しません。`--check-github` は `gh repo view` の読み取り確認を追加します。`present` は存在確認の結果であり、Grok Bot の connector や本物の Issue handoff が動く証明ではありません。エンドツーエンドは常に `unknown` と表示します。

## 契約

ヘッダーと本文の間に空行を一つ入れます。ヘッダー行に説明コメントを書かないでください。

```text
agent: claude
repo: /Users/<user>/workspace/maylac/<repo>
model: claude-opus-5-5

Goal: 1〜2文
Owned files: 変更を許可するパス
Acceptance:
  - 実行可能な確認コマンドと期待結果
Time budget: 30m
```

パス内の `<user>` は Mac mini の実際のユーザー名に置き換えます。`cursor` は本統合に必要な読み取り専用レビュー route です。実 CLI と認証を確認するまでは無効のままにし、確認後に有効化します。Cursor に実装や修正を委任しません。設定例は [Grok Bot 導入ガイド](../docs/grok-bot/README.md) を参照してください。

## 動作と結果確認

bridge の `done` は agent process が終了コード 0 で終わったことを示します。Dispatcher はそれだけで利用者向けの完了とせず、報告された PR の head、CI/check 結果、成果物の存在と内容を確認し、必要なら agent-task を再開する前に追加の証拠を求めます。

設定されていない接続先は未接続として扱います。`doctor.py` は設定の存在を診断しますが、Issue の作成、daemon の起動、エージェントの推論は行いません。
