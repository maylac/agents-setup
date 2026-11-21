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
AUTH_MSG = "認証エラー: `nlm login` で再認証してください"


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

    import typer
    from notebooklm_tools.cli.utils import get_client
    from notebooklm_tools.services import downloads as dl_svc
    from notebooklm_tools.services import studio as studio_svc

    try:
        client = get_client()
    except (SystemExit, typer.Exit):
        # typer.Exit は SystemExit を継承しない（0.13 系では RuntimeError 直系）
        die(2, AUTH_MSG)
    except Exception as e:
        die(2, f"client init failed ({type(e).__name__}: {e}); {AUTH_MSG}")

    try:
        with client:
            nb = next((n for n in client.list_notebooks() if n.title == args.notebook_title), None)
            if nb is None:
                nb = client.create_notebook(args.notebook_title)
                if nb is None:
                    die(4, "notebook_create failed")
            nb_id = nb.id

            # ソース上限ガード（タイトル昇順 = 日付プレフィックス順で古い方から削除）
            sources = client.get_notebook_sources_with_types(nb_id)
            if len(sources) >= MAX_SOURCES:
                excess = len(sources) - MAX_SOURCES + 1
                oldest = sorted(sources, key=lambda s: s.get("title") or "")[:excess]
                client.delete_sources([s["id"] for s in oldest])

            src = client.add_text_source(nb_id, text, title=plan_path.stem, wait=True)
            if not src or not src.get("id"):
                die(4, f"source_add failed: {src}")
            source_id = src["id"]

            created = studio_svc.create_artifact(
                client,
                nb_id,
                "infographic",
                source_ids=[source_id],
                orientation=args.orientation,
                detail_level=args.detail,
                infographic_style=args.style,
                language=args.language,
                focus_prompt="実装プランの承認判断用: スコープ、実行手順、リスク、検証方法を強調する",
            )
            artifact_id = created["artifact_id"]

            deadline = time.time() + args.timeout
            while True:
                status = studio_svc.get_studio_status(client, nb_id, artifact_id=artifact_id)
                mine = next(
                    (a for a in status["artifacts"] if a.get("artifact_id") == artifact_id), None
                )
                state = mine.get("status") if mine else None
                if state == "completed":
                    break
                if state in ("failed", "error"):
                    die(4, f"generation failed: {mine.get('error_reason') or mine}")
                if time.time() > deadline:
                    die(3, f"generation timed out after {args.timeout}s (artifact {artifact_id})")
                time.sleep(POLL_INTERVAL)

            png_path = plan_path.with_suffix(".png")
            asyncio.run(
                dl_svc.download_async(
                    client, nb_id, "infographic", str(png_path), artifact_id=artifact_id
                )
            )
            if not png_path.is_file() or png_path.stat().st_size == 0:
                die(4, f"download produced no file: {png_path}")
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
