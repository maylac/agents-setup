# NotebookLMヘッドレス自動化パイプラインの落とし穴2つ（typer.Exit / 通知transport実在確認）

- 日付: 2026-07-17
- 領域: agents-setup / plan-infographic パイプライン（~/bin/plan-infographic, ~/.agents/hooks/notify-mobile-photo.sh）
- 種別: debugging / design-tradeoff

## 問題

plan modeのplanをNotebookLMに投入しインフォグラフィックを自動生成するパイプラインを構築。
(1) `notebooklm_tools.cli.utils.get_client()` の認証失敗を捕捉して exit=2 + 「nlm login」案内を出す設計が、
レビューで「到達不能」と判明。(2) 設計時に前提としたTelegram配信が、実行段階でこのMacに
トークンが存在しない（ccgramデーモン撤去済み、~/.hermes/.envのTelegram欄もコメントアウト）と判明。

## 試して駄目だった道

- `except SystemExit` で typer の認証エラーを捕捉 — `typer.Exit` は `SystemExit` のサブクラスではない
  （MRO: `click.exceptions.Exit → RuntimeError → Exception`）ため一度も発火しない。実装・テストとも
  「文字列がソースに存在する」ことしか確認しておらず、経路が生きている証明になっていなかった。
- ポーリングで `status == "error"` を判定 — パッケージの語彙は `{1: in_progress, 3: completed, 4: failed}`。
  `"error"` は決して返らず、生成失敗が10分のタイムアウト（exit=3）に化ける。
- Telegram sendPhoto直叩きを唯一のモバイル配信経路にする設計 — メモリ上の「Telegram主体」を信じて
  実在確認を後回しにした。トークンはどこにも無かった。

## 効いたアプローチ

- `except click.exceptions.Exit` を明示的に追加（typer.Exitはこれを継承）。検証は `HOME` を空ディレクトリに
  向けて `get_client()` に本物の `typer.Exit` を投げさせ、exit=2 + stderr文言を実測（Fable再レビューが実施）。
- ステータス判定を `in ("failed", "error")` に修正（実語彙+防御的エイリアス）。
- 配信は transport chain 化: Telegramトークンがあれば sendPhoto、無ければ `hermes send -t slack:… "MEDIA:<png> <caption>"`
  へフォールバック。`hermes send` はゲートウェイ起動不要でSlack添付を送れる（実測2回 exit=0）。

## なぜ効いたか

- typer は Click 8 の上に構築され、`typer.Exit` は意図的に `SystemExit` を避けている（Clickの
  スタンドアロンモードが外側で捕まえて `sys.exit()` に変換する設計）。ライブラリのCLIヘルパーを
  ライブラリとして呼ぶと、この変換層が無いので例外がそのまま伝播する。
- 裏づけ: `issubclass(typer.Exit, SystemExit) == False` / `issubclass(typer.Exit, click.exceptions.Exit) == True` を
  venv内で実測。HOMEリダイレクトによる実経路テストで exit=2 を観測。

## 一般化できる原則

- CLIフレームワークのユーティリティ（typer/click/richを使うget_client等）をスクリプトから直接importする場合、
  例外契約を`issubclass`で実測してからexceptを書くこと。「SystemExitだろう」は typer では偽。
- エラー分岐のテストは「メッセージ文字列がソースにある」ではなく「その経路を実際に発火させて終了コードと
  stderrを観測した」こと（発火手段が無ければHOME/env/引数の細工で作る）。
- 通知・配信系の設計は、コードを書く前にトークン/デーモンの実在を`ls`/`rg`で確認すること。
  メモリや設計書の「設定済み」は現在の実在証明ではない。
