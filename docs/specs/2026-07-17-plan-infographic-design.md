# Plan → NotebookLM インフォグラフィック承認パイプライン 設計書

日付: 2026-07-17
状態: 設計承認済み（ユーザー承認）

## 目的

Plan mode で作成した実装プランを NotebookLM に自動投入してインフォグラフィックを生成し、
ユーザーがそれを見て承認判断してから実装に着手するフローを自動化する。
外出先では Telegram で画像を受け取り、モバイルから承認を返せること。

## 実現方式

ヘッドレススクリプト方式。pipx 導入済みの `notebooklm-mcp-cli`（`notebooklm_tools`
Python パッケージ、`~/.local/pipx/venvs/notebooklm-mcp-cli/`）を直接呼ぶ。
ブラウザ自動化・MCP グローバル登録は使わない。

確認済みの API 能力（`notebooklm_tools.mcp.tools.studio` / `services.downloads`）:
- `studio_create(notebook_id, artifact_type="infographic", source_ids=[...],
  orientation, detail_level, infographic_style, language)` で生成開始
- `studio_status` でポーリング、完了後 PNG ダウンロード（`STREAMING_TYPES` に infographic 含む）

## 全体フロー

```
Plan mode → ExitPlanMode（plan 本文の仮承認）
  ↓ 承認直後、実装着手前に必ず（AGENTS.md 規範）
1. plan 本文を ~/tasks/plan-reviews/YYYY-MM-DD-<slug>.md に保存
2. plan-infographic <plan.md> を実行:
   a. 常設ノートブック「Plan Reviews」へ source_add（初回は notebook_create）
   b. studio_create(infographic, source_ids=[今回のソースのみ],
      language=ja, orientation=landscape, infographic_style=professional,
      detail_level=standard)
   c. studio_status を 30 秒間隔でポーリング（上限 10 分）
   d. 完成 PNG をダウンロードし、JSON（png_path, notebook_url, source_id）を stdout に出力
3. 配信（3 系統）:
   - SendUserFile でセッション内に PNG をインライン表示
   - notify-mobile-photo.sh で Telegram に sendPhoto（キャプションに NotebookLM URL）
   - 本文に NotebookLM URL を記載
4. AskUserQuestion「承認 / 修正 / 却下」
   - 承認されるまで実装コードの変更は一切行わない（実装ゲート）
   - 修正 → plan 改訂後パイプライン再実行
   - 却下 → 中止
```

承認は二段構え: ExitPlanMode 承認＝plan 本文の仮承認、インフォグラフィック後の
AskUserQuestion＝実装ゲート。

## コンポーネント

| # | 物 | 内容 |
|---|---|---|
| 1 | `~/bin/plan-infographic` | 実行スクリプト。shebang は pipx venv の python（`~/.local/pipx/venvs/notebooklm-mcp-cli/bin/python`）。引数: plan.md パス。処理: notebook 解決（alias or 検索、無ければ作成）→ source_add → studio_create → poll → download。出力: JSON `{png_path, notebook_url, source_id}`。終了コード 0=成功 / 非 0=失敗（stderr に理由） |
| 2 | `~/.agents/hooks/notify-mobile-photo.sh` | 引数: PNG パス、キャプション。notify-mobile.sh と同じ CCGRAM_ENV 読込で Telegram `sendPhoto` を叩く。既存 notify-mobile.sh は変更しない |
| 3 | スキル `plan-infographic`（`~/.agents/skills/plan-infographic/SKILL.md`、sync-skills.sh で共有） | フロー手順書。/plan-infographic での手動起動も可能に |
| 4 | 規範追記（正本 `agents-setup/home/AGENTS.md` → sync-instructions.sh） | 「plan mode 承認後、実装着手前に plan-infographic パイプラインを実行し、インフォグラフィック承認を得るまで編集禁止。パイプライン失敗時はテキスト plan での AskUserQuestion 承認に降格」 |

## 設計上の決め

- **ノートブックは常設 1 つ**（「Plan Reviews」）。plan 毎に新規作成せず、ソース追加＋
  `source_ids` スコープで生成。ソース数が 40 件に達したらタイトルの日付プレフィックス順で
  古いものから自動削除してソース上限を回避する（API がソース作成日時を返さないため、
  日付入りタイトルを利用した件数ベースのガードとする）。
- **フォールバック**: 認証失効（HTTP 400）・生成タイムアウト（10 分超）・その他エラー時は
  非 0 終了とし、呼び出し側（スキル手順）はエラーを通知したうえで従来のテキスト plan
  承認（AskUserQuestion）に自動降格する。パイプライン故障で開発を止めない。
- **既定スタイル**: professional / landscape / standard / 日本語。スクリプト引数
  （`--style` / `--orientation` / `--detail`）で上書き可。
- **plan の保存先**: `~/tasks/plan-reviews/`。承認記録を兼ねる（同ディレクトリに
  PNG も保存）。

## 前提条件

- `nlm login` の再認証（2026-07-17 時点でクッキー失効、HTTP 400 を確認済み）。
  実装後の動作検証前にユーザーが一度実行する。

## 検証基準

1. 認証済み状態で `plan-infographic <sample-plan.md>` が PNG と URL を返す（実測）
2. Telegram に画像が届く（実測）
3. 認証失効状態で非 0 終了し、stderr に再認証を促すメッセージが出る
4. 「Plan Reviews」ノートブックにソースが追加され、2 回目実行で重複ノートブックを作らない
