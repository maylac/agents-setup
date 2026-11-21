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
2. **生成実行**: `~/.agents/skills/plan-infographic/scripts/plan-infographic ~/tasks/plan-reviews/<file>.md`
   を実行する（ランチャーが `nlm` の Python を自動解決する）。
   1〜3分かかる（生成ポーリング30秒間隔、上限10分）。バックグラウンド実行
   （Bash run_in_background）にして完了通知を待ってよい。
   Claude Code のサンドボックス内では Bash の `allowed_domains` に
   `notebooklm.google.com`, `accounts.google.com`, `lh3.googleusercontent.com`, `lh3.google.com`
   を渡す（`lh3.google.com` は PNG ダウンロードのリダイレクト先。欠けると exit=4 / 403）。
   成功時はstdoutにJSON（png_path / notebook_url / notebook_id / source_id / artifact_id）。
   stdout は exit=0 のときだけ JSON として解釈する（失敗時はパッケージがエラー文を stdout に出すことがある）。
3. **配信**:
   - `SendUserFile` で png_path をセッションに送付（display: render）。送付できない
     セッション（project thread 外など）では、その旨と png_path を本文で伝える
   - 本文にも notebook_url を記載（スマホからは NotebookLM で開ける）
   - 配信失敗で中断しない
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
