# Plan Infographic Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plan mode の plan を NotebookLM に自動投入してインフォグラフィックを生成し、承認ゲートを経てから実装に入るパイプラインを構築する。

**Architecture:** pipx 導入済みの `notebooklm_tools`（`~/.local/pipx/venvs/notebooklm-mcp-cli/`）の services 層を直接呼ぶヘッドレス Python スクリプト＋Telegram sendPhoto ヘルパー＋スキル手順書＋AGENTS.md 規範の4点。

**Tech Stack:** Python 3.14（pipx venv）、notebooklm_tools（services.studio / services.downloads / core client）、bash + curl（Telegram Bot API）。

**Spec:** `~/workspace/agents-setup/docs/specs/2026-07-17-plan-infographic-design.md`

## Global Constraints

- スクリプト shebang は `#!/Users/maylac/.local/pipx/venvs/notebooklm-mcp-cli/bin/python` 固定（システム python には notebooklm_tools が無い）
- 常設ノートブック名は `Plan Reviews`、plan 保存先は `~/tasks/plan-reviews/`
- 既定値: `--style professional` / `--orientation landscape` / `--detail standard` / `--language ja` / `--timeout 600`
- 終了コード: 0=成功 / 2=認証・引数エラー / 3=生成タイムアウト / 4=API エラー
- `CreateResult` / `StatusResult` / `DownloadResult` は **TypedDict**。属性アクセス不可、`result["artifact_id"]` の形で読む
- 既存ファイル `~/.agents/hooks/notify-mobile.sh` は変更しない
- `agents-setup` リポジトリには他タスクの未コミット変更（fable 関連）がある。**自分が作ったファイル以外を git add しない**
- 現時点で NotebookLM 認証は失効中（HTTP 400）。ハッピーパス実測は Task 5（ユーザーの `nlm login` 後）で行う

---

### Task 1: Telegram 写真送信ヘルパー `notify-mobile-photo.sh`

**Files:**
- Create: `~/.agents/hooks/notify-mobile-photo.sh`

**Interfaces:**
- Produces: `notify-mobile-photo.sh <png_path> [caption]` — 成功で exit 0、トークン未設定・送信失敗で exit 1（stderr に理由）。Task 3 のスキルがこのシグネチャで呼ぶ。

- [ ] **Step 1: スクリプトを書く**

```bash
#!/usr/bin/env bash
# notify-mobile-photo.sh — Telegram bot(ccgram と同一)で写真を送る。
# 呼び出し: notify-mobile-photo.sh <png_path> [caption]
# notify-mobile.sh と同じ環境ファイルから TELEGRAM_BOT_TOKEN / chat_id を読む。
set -u
PNG="${1:?usage: notify-mobile-photo.sh <png_path> [caption]}"
CAPTION="${2:-}"
CCGRAM_ENV="$HOME/.ccgram/.env"

[ -r "$PNG" ] || { echo "photo not found: $PNG" >&2; exit 1; }

tg_token=""; tg_chat=""
if [ -r "$CCGRAM_ENV" ]; then
  set -a; . "$CCGRAM_ENV" 2>/dev/null || true; set +a
  tg_token="${TELEGRAM_BOT_TOKEN:-}"
  tg_chat="${TELEGRAM_CHAT_ID:-${ALLOWED_USERS:-}}"; tg_chat="${tg_chat%%,*}"
fi
if [ -z "$tg_token" ] || [ -z "$tg_chat" ]; then
  echo "telegram token/chat_id unavailable ($CCGRAM_ENV)" >&2; exit 1
fi

if curl -sf --max-time 30 "https://api.telegram.org/bot${tg_token}/sendPhoto" \
    -F "chat_id=${tg_chat}" \
    -F "photo=@${PNG}" \
    --form-string "caption=${CAPTION}" >/dev/null; then
  exit 0
fi
echo "sendPhoto failed" >&2; exit 1
```

- [ ] **Step 2: 実行権限を付与し、引数エラー経路をテスト**

Run: `chmod +x ~/.agents/hooks/notify-mobile-photo.sh && ~/.agents/hooks/notify-mobile-photo.sh /nonexistent.png; echo "exit=$?"`
Expected: stderr に `photo not found: /nonexistent.png`、`exit=1`

- [ ] **Step 3: 実写真の送信テスト（外部送信を伴う。実行前にユーザーへ一言確認する）**

```bash
# テスト画像を生成して送信
/usr/bin/python3 -c "
import zlib, struct
def chunk(t, d):
    c = t + d
    return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c))
ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
idat = zlib.compress(b'\x00\xff\x00\x00')
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')
open('/tmp/notify-photo-test.png','wb').write(png)
"
~/.agents/hooks/notify-mobile-photo.sh /tmp/notify-photo-test.png "notify-mobile-photo.sh 動作テスト"; echo "exit=$?"
```

Expected: `exit=0`、ユーザーの Telegram に 1x1 画像が届く（ユーザーに着信確認を依頼）

---

### Task 2: パイプライン本体 `~/bin/plan-infographic`

**Files:**
- Create: `~/bin/plan-infographic`

**Interfaces:**
- Consumes: `notebooklm_tools.cli.utils.get_client()`（プロファイル認証済みクライアント。失敗時 `typer.Exit`→`SystemExit`）、`client.list_notebooks() -> list[Notebook(id, title, ...)]`、`client.create_notebook(title) -> Notebook | None`、`client.get_notebook_sources_with_types(nb_id) -> list[dict(id, title, status, ...)]`、`client.delete_sources(ids) -> bool`、`client.add_text_source(nb_id, text, title, wait=True) -> dict("id", "title") | None`、`services.studio.create_artifact(...) -> CreateResult(TypedDict)`、`services.studio.get_studio_status(client, nb_id) -> StatusResult(TypedDict)`、`services.downloads.download_async(...)`（async）
- Produces: CLI `plan-infographic <plan.md> [--style ...] [--orientation ...] [--detail ...] [--language ...] [--notebook-title ...] [--timeout ...]`。成功時 stdout に JSON `{"png_path", "notebook_url", "notebook_id", "source_id", "artifact_id"}`。PNG は `<plan.md と同じディレクトリ>/<同名>.png`。Task 3・4 がこの契約に依存。

- [ ] **Step 1: スクリプトを書く**

```python
#!/Users/maylac/.local/pipx/venvs/notebooklm-mcp-cli/bin/python
"""plan-infographic — plan.md を NotebookLM に投入しインフォグラフィック PNG を生成する。

usage: plan-infographic <plan.md> [--style STYLE] [--orientation O] [--detail D]
                        [--language LANG] [--notebook-title T] [--timeout SEC]

stdout: 成功時 JSON {"png_path", "notebook_url", "notebook_id", "source_id", "artifact_id"}
exit: 0=成功 / 2=認証・引数エラー / 3=生成タイムアウト / 4=API エラー
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

MAX_SOURCES = 40  # 常設ノートブックのソース上限ガード
POLL_INTERVAL = 30


def die(code: int, msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_md")
    ap.add_argument("--style", default="professional")
    ap.add_argument("--orientation", default="landscape")
    ap.add_argument("--detail", default="standard")
    ap.add_argument("--language", default="ja")
    ap.add_argument("--notebook-title", default="Plan Reviews")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    plan_path = Path(args.plan_md).expanduser().resolve()
    if not plan_path.is_file():
        die(2, f"plan file not found: {plan_path}")
    text = plan_path.read_text(encoding="utf-8")

    try:
        import click
        from notebooklm_tools.cli.utils import get_client
        from notebooklm_tools.services import downloads as dl_svc
        from notebooklm_tools.services import studio as studio_svc

        client = get_client()
    except SystemExit:
        die(2, "認証エラー: `nlm login` で再認証してください")
    except click.exceptions.Exit:
        # typer.Exit は SystemExit のサブクラスではない (click.exceptions.Exit 継承)
        die(2, "認証エラー: `nlm login` で再認証してください")
    except Exception as e:
        die(2, f"client init failed: {e}")

    try:
        with client:
            # 1. 常設ノートブック解決（無ければ作成）
            nbs = client.list_notebooks()
            nb = next((n for n in nbs if n.title == args.notebook_title), None)
            if nb is None:
                nb = client.create_notebook(args.notebook_title)
                if nb is None:
                    die(4, "notebook_create failed")
            nb_id = nb.id

            # 2. ソース上限ガード（タイトル昇順 = 日付プレフィックス順で古い方から削除）
            sources = client.get_notebook_sources_with_types(nb_id)
            if len(sources) >= MAX_SOURCES:
                excess = len(sources) - MAX_SOURCES + 1
                oldest = sorted(sources, key=lambda s: s["title"])[:excess]
                client.delete_sources([s["id"] for s in oldest])

            # 3. plan をテキストソースとして追加（処理完了まで待つ）
            src = client.add_text_source(nb_id, text, title=plan_path.stem, wait=True)
            if not src or not src.get("id"):
                die(4, f"source_add failed: {src}")
            source_id = src["id"]

            # 4. インフォグラフィック生成開始（今回のソースのみ対象）
            created = studio_svc.create_artifact(
                client,
                nb_id,
                "infographic",
                source_ids=[source_id],
                orientation=args.orientation,
                detail_level=args.detail,
                infographic_style=args.style,
                language=args.language,
                focus_prompt=(
                    "実装プランの承認判断用: スコープ、実行手順、リスク、検証方法を強調する"
                ),
            )
            artifact_id = created["artifact_id"]

            # 5. 完成までポーリング
            deadline = time.time() + args.timeout
            while True:
                status = studio_svc.get_studio_status(client, nb_id)
                mine = next(
                    (a for a in status["artifacts"] if a.get("artifact_id") == artifact_id),
                    None,
                )
                if mine and mine.get("status") == "completed":
                    break
                if mine and mine.get("status") in ("failed", "error"):
                    die(4, f"generation failed: {mine}")
                if time.time() > deadline:
                    die(3, f"generation timed out after {args.timeout}s (artifact {artifact_id})")
                time.sleep(POLL_INTERVAL)

            # 6. PNG ダウンロード（plan.md と同じ場所・同名 .png）
            png_path = plan_path.with_suffix(".png")
            asyncio.run(
                dl_svc.download_async(
                    client, nb_id, "infographic", str(png_path), artifact_id=artifact_id
                )
            )
    except SystemExit:
        raise
    except Exception as e:
        die(4, f"{type(e).__name__}: {e}")

    print(
        json.dumps(
            {
                "png_path": str(png_path),
                "notebook_url": f"https://notebooklm.google.com/notebook/{nb_id}",
                "notebook_id": nb_id,
                "source_id": source_id,
                "artifact_id": artifact_id,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 実行権限付与と引数エラー経路のテスト**

Run: `chmod +x ~/bin/plan-infographic && ~/bin/plan-infographic /nonexistent-plan.md; echo "exit=$?"`
Expected: stderr に `plan file not found: /nonexistent-plan.md`、`exit=2`

- [ ] **Step 3: 認証失効経路のテスト（現在失効中なのでいま検証できる）**

Run: `printf '# sample plan\n\n- step 1\n' > /tmp/sample-plan.md && ~/bin/plan-infographic /tmp/sample-plan.md; echo "exit=$?"`
Expected: 非 0 終了（認証失効が `get_client` で捕まれば `認証エラー: nlm login で再認証してください` + exit=2、リクエスト段階で 400 になる場合は `HTTPStatusError: ...` + exit=4。どちらも仕様どおり）。トレースバックが素通しで出る場合は握り損ねなので修正する。

- [ ] **Step 4: 検証基準3の文言確認**

exit=2 経路の stderr に「nlm login」の文字列が含まれることを確認（設計書の検証基準3）。exit=4 経路だった場合は、`except Exception` 節のメッセージ先頭に `（認証失効の可能性あり: nlm login を試す） ` を条件追加せず、そのままで良い（400 の原因は認証以外もあり得るため。基準3は exit=2 経路で満たす）。

---

### Task 3: スキル `plan-infographic`

**Files:**
- Create: `~/.agents/skills/plan-infographic/SKILL.md`

**Interfaces:**
- Consumes: Task 1 の `notify-mobile-photo.sh <png> [caption]`、Task 2 の `plan-infographic <plan.md>`（JSON 出力）
- Produces: `/plan-infographic` で手動起動可能なスキル。Task 4 の AGENTS.md 規範がこのスキル名を参照。

- [ ] **Step 1: SKILL.md を書く**

```markdown
---
name: plan-infographic
description: Plan modeのplanをNotebookLMに投入してインフォグラフィックを生成し、承認ゲートにかける。plan承認直後の実装着手前に必ず使用。手動では「planをインフォグラフィックにして」「/plan-infographic」で発火。
---

# Plan → NotebookLM インフォグラフィック承認ゲート

plan本文をNotebookLMでインフォグラフィック化し、ユーザーの承認を得るまで実装に入らないためのパイプライン。

## 手順

1. **plan保存**: 直近のplan本文（ExitPlanModeで提示したもの）を
   `~/tasks/plan-reviews/YYYY-MM-DD-<slug>.md` に保存する（slugは英小文字ケバブケース）。
   ディレクトリが無ければ作る。
2. **生成実行**: `~/bin/plan-infographic ~/tasks/plan-reviews/<file>.md` を実行する。
   数分かかる（生成ポーリング30秒間隔、上限10分）。バックグラウンド実行
   （Bash run_in_background）にして完了通知を待ってよい。
   成功時はstdoutにJSON（png_path / notebook_url / notebook_id / source_id / artifact_id）。
3. **配信（3系統）**:
   - `SendUserFile` で png_path をセッションに送付（display: render）
   - `~/.agents/hooks/notify-mobile-photo.sh <png_path> "<planタイトル> の実装プラン — <notebook_url>"`
     でTelegramに送信
   - 本文にも notebook_url を記載
4. **承認ゲート**: AskUserQuestion で「承認 / 修正 / 却下」を確認する。
   - 承認 → 実装開始
   - 修正 → plan改訂後、手順1から再実行（ファイルは同名で上書きしてよい。
     ソースは新規追加されるが上限ガードが掃除する）
   - 却下 → 実装せず中止
   - **承認が返るまで実装コードの編集は一切しない**
5. **失敗時の降格**: `plan-infographic` が非0終了したら、stderrの内容と
   （exit=2なら）`nlm login` での再認証が必要な旨を伝え、テキストplanのまま
   AskUserQuestion承認に降格して先に進む。パイプライン故障で開発を止めない。

## 引数（任意）

スタイル指定があれば `--style`（professional / bento_grid / editorial / sketch_note /
instructional / scientific 等）、`--orientation`（landscape / portrait / square）、
`--detail`（concise / standard / detailed）を渡す。既定は professional / landscape / standard / 日本語。
```

- [ ] **Step 2: sync-skills.sh で各エージェントへ symlink 展開**

Run: `bash ~/.agents/sync-skills.sh && readlink ~/.claude/skills/plan-infographic`
Expected: `../../.agents/skills/plan-infographic`

---

### Task 4: AGENTS.md 規範追記

**Files:**
- Modify: `~/workspace/agents-setup/home/AGENTS.md`（末尾に追記）

**Interfaces:**
- Consumes: Task 3 のスキル名 `plan-infographic`
- Produces: 全セッションに読み込まれる規範（`~/AGENTS.md` は正本への symlink）

- [ ] **Step 1: 正本の末尾に規範セクションを追記**

`~/workspace/agents-setup/home/AGENTS.md` の末尾に追記:

```markdown
## Plan Infographic Approval Gate

Plan mode の plan が ExitPlanMode で承認されたら、実装着手前に必ず `plan-infographic`
スキルを実行する（plan保存 → NotebookLMでインフォグラフィック生成 → PNG/Telegram/URL配信 →
AskUserQuestionで承認確認）。インフォグラフィックの承認が返るまで実装コードを編集しない。
パイプラインが失敗した場合はエラーを報告し、テキスト plan のまま AskUserQuestion 承認に
降格して進める。
```

- [ ] **Step 2: sync-instructions.sh を実行して配布**

Run: `bash ~/workspace/agents-setup/scripts/sync-instructions.sh && rg -n "Plan Infographic Approval Gate" ~/AGENTS.md`
Expected: 追記したセクションが `~/AGENTS.md`（symlink経由）から読める

- [ ] **Step 3: コミットは保留する（明示）**

`home/AGENTS.md` には他タスク（fable advisor/verifier）の未コミット変更が既に載っている。
このタスクではコミットせず、完了報告で「home/AGENTS.md は fable 分と合わせて要コミット」と
ユーザーに伝える。スキル・スクリプト類の agents-setup ミラーコミットも同じタイミングで行う。

---

### Task 5: E2E 検証（要ユーザー操作: `nlm login`）

**Files:**
- Create: `~/tasks/plan-reviews/`（ディレクトリ）

**Interfaces:**
- Consumes: Task 1〜3 の全成果物

- [ ] **Step 1: ユーザーに再認証を依頼**

ユーザーに `! nlm login` の実行を依頼し、完了を待つ。
確認: `nlm notebook list` がノートブック一覧を返す（HTTP 400 が出ない）。

- [ ] **Step 2: サンプル plan でハッピーパス実測（検証基準1）**

```bash
mkdir -p ~/tasks/plan-reviews
cp ~/workspace/agents-setup/docs/specs/2026-07-17-plan-infographic-design.md \
   ~/tasks/plan-reviews/2026-07-17-plan-infographic-selftest.md
~/bin/plan-infographic ~/tasks/plan-reviews/2026-07-17-plan-infographic-selftest.md
```

Expected: 10 分以内に JSON が出力され、`png_path` のファイルが存在し 10KB 超。
`file <png_path>` が PNG image を返す。

- [ ] **Step 3: 配信経路の実測（検証基準2）**

- SendUserFile で PNG をセッションに送付 → インライン表示される
- `~/.agents/hooks/notify-mobile-photo.sh <png_path> "selftest — <notebook_url>"` → exit 0、ユーザーに Telegram 着信を確認してもらう

- [ ] **Step 4: ノートブック再利用の実測（検証基準4）**

Run: `printf '# tiny plan\n\n- do X\n- verify X\n' > ~/tasks/plan-reviews/2026-07-17-tiny-selftest.md && ~/bin/plan-infographic --detail concise ~/tasks/plan-reviews/2026-07-17-tiny-selftest.md`
Expected: JSON の `notebook_id` が Step 2 と同一。`nlm notebook list` で `Plan Reviews` が 1 つだけ。

- [ ] **Step 5: 後片付けと完了報告**

selftest 用ソース 2 件を `nlm source delete <id>` で削除（またはそのまま上限ガードに任せる旨を報告）。
完了報告に含める: 実測結果（PNG サイズ・所要時間）、`home/AGENTS.md` の要コミット状態、
今後の運用（plan 承認のたびに自動発火すること）。
