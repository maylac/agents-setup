# Grok Bot を Dispatcher にする構成案

この構成では Grok Bot アプリを依頼の入口と報告・承認窓口にし、GitHub Issue を Mac mini への指示経路にします。設定と接続はまだ完了していません。2026-10-25 時点で、ローカルの bridge→Codex loopback が一度通り、依頼したマーカーファイルを読み戻せています。これはローカル bridge/CLI 経路だけの確認で、実際に指定モデルが処理した証明ではありません。bridge の env 設定ファイルと launchd 登録はなく、dispatch 用 GitHub リポジトリは解決できず、Cursor アプリ/CLI も見つかっていません。Grok Bot の connector と実際の handoff も未確認です。Claude と Codex の認証済み状態はローカルホスト上で観測されていますが、この文書では秘密値やアカウント識別子を扱いません。

Grok Bot は xAI の説明上、Bot 同士が同じクラウド PC とブラウザを共有します。Mac mini の SSH 鍵、NAS 認証情報、その他の秘密を Bot に渡さないでください。[Grok Bot の公式説明](https://cursor.com/docs/grok-bot) にある共有環境と delegation の説明を前提に、クラウド側は契約の作成と証拠確認を担当します。

| 役割 | 担当 |
|---|---|
| Grok Bot / Dispatcher | 依頼を Issue 契約にする。人の承認を求め、結果の PR・CI・成果物を確認して元の入口へ報告する。自分で実装しない。 |
| Claude Code | 通常の実装、修正、調査。 |
| Codex | Claude の利用制限時の実装、または独立したレビュー。 |
| Cursor CLI | 明示的に導入・有効化した後の読み取り専用レビューと提案。bridge は Cursor に編集を依頼しない。 |

## 作業の流れ

```text
Grok Bot アプリ ──依頼──> Dispatcher ──agent-task Issue──> GitHub
                                                        │
                                   Mac mini bridge <─────┘
                                         │
                               Claude / Codex / Cursor review
                                         │
                                  Issue 結果・PR・checks
                                         │
                          Dispatcher が証拠を確認して報告
```

依頼ごとに一つの Issue を使います。Issue には担当 agent、repo ref、目的、編集可能なファイル、実行可能な完了条件、制限時間、仮定を記します。単一 controller を維持し、同じファイルに別経路の作業がある場合は `manual` 扱いにして重複指示を止めます。無関係な Bot の大量作成や、新しい scheduler/dashboard は追加しません。繰り返し処理は接続と安全性を確認した後に必要なものだけ設定します。

## 契約例

本文の先頭は機械判読可能なヘッダーです。行末コメントを付けず、空行の後に依頼本文を置きます。repo の `<user>` は実際の Mac mini のユーザー名に置き換えます。

```text
agent: claude
repo: /Users/<user>/workspace/maylac/agents-setup

Goal: README のリンク切れを修正する。
Owned files: README.md
Acceptance:
  - test -s README.md が終了コード 0
  - git diff --check が終了コード 0
Time budget: 30m
Assumptions: リンク先の内容は変更しない。
Report: status、変更ファイル、各チェック結果、PR URL、未解決事項を5行以内で記録する。
```

モデル指定を空のまま送らず、省略する場合は `model:` 行ごと削除します。必要な時だけ `fallback: off` など routing の契約オプションを別の有効なヘッダー行として使います。

## 結果の判定

`done` のコメントが届いたら、終了コードだけで完了扱いにしません。PR がある場合は head revision、必須 CI/check、対象変更を照合します。成果物がある場合はリンクを開き、存在と内容を確認します。結果リンクがない、条件未達、証拠が不明な場合は Dispatcher が追加確認を一度だけ契約にし、なお不明なら blocked と報告します。利用制限はコメントの route と再開時刻をそのまま伝え、別 controller が同じ作業を起票しないようにします。

人の判断が必要な場合は、理由、対象の正確な操作、最後に確認できた時刻を添えて一度だけ尋ねます。返答を待っている間、無関係で安全な調査は続けます。沈黙は承認ではありません。

## 接続・有効化

具体的な順序と承認対象は [有効化計画](activation-plan.md) に記載しています。bridge 側の読み取り診断は `python3 slack-bridge/doctor.py`、GitHub への読み取り確認を含める場合は `python3 slack-bridge/doctor.py --check-github` です。この診断だけでは Bot connector や end-to-end handoff の成功は確認できません。

## 公式資料

- [Cursor CLI headless mode](https://cursor.com/docs/cli/headless): `--print` の出力形式と、変更適用に関するフラグを確認する資料。
- [Grok Bot](https://cursor.com/docs/grok-bot): Bot の共有クラウド PC と委任機能の説明。
- [xAI changelog](https://x.ai/changelog/bot): GitHub connector の機能更新。

これらの資料は製品仕様の根拠です。この環境で connector が有効か、Grok Bot が実際に Issue を作れるかの証拠にはなりません。
