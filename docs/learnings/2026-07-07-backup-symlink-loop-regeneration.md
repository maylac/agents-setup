# backup.sh が skills/fable-escalation に自己参照 symlink ループを再生成する

- 日付: 2026-07-07
- 領域: agents-setup / scripts/backup.sh
- 種別: bug

## 問題

`scripts/backup.sh` 実行のたびに `skills/fable-escalation` が「自分自身を指す
絶対パス symlink」になり、`git status` すら ELOOP (`Too many levels of symbolic
links`) を出す。一度 `git checkout` で復元しても、次の backup 実行で再発する。

## 試して駄目だった道

- repo 側を `git restore` するだけ → 生成機構が残っているので次の backup で必ず再発。
- 「backup.sh が symlink ループでハングするのでは」という仮説 → 実測で否定。
  `rsync -a` はループ symlink を素通しコピーするだけ、`find -type f`(sanitize 経路)は
  symlink を辿らない。問題はハングではなく**ループの複製**だった。

## 効いたアプローチ

1. 正本ストアを調査: `~/.agents/skills/fable-escalation` は実体ディレクトリではなく
   **この repo(`$ROOT/skills/fable-escalation`)への絶対 symlink** だった
   (skill の開発正本が repo 側にあるパターン)。
2. `rsync -a` は symlink を verbatim コピーするため、コピー先が symlink の指す先と
   同一パスになり「自分を指すリンク」が完成する。
3. 修正: skills 同期に `--copy-unsafe-links` を追加。ツリー外を指す symlink だけ
   実体化し、スキル内の相対 symlink は保持する。src の解決先 == dst(同一ファイル)の
   ケースは rsync が同一と判定してスキップするので破壊しない(scratchpad の
   フィクスチャで src==dst・外部リンク・自己参照ループの3ケースを事前検証)。

## なぜ効いたか

根本原因は「ミラー元(正本ストア)がミラー先(repo)への参照を含む」という循環構造。
rsync のリンク保持 (`-l` in `-a`) がその参照をミラー先に持ち込むと、参照先=自分自身に
なる。`--copy-unsafe-links` はコピー対象ツリーの外を指すリンクを内容コピーに変換する
ので、循環が snapshot 時点で切れる。

## 一般化できる原則

- ミラー/バックアップ対象のツリーに symlink が含まれる場合、「リンク先がミラー先
  自身に解決されないか」を確認すること。該当し得るなら rsync は
  `--copy-unsafe-links`(ツリー外リンクの実体化)を使うこと。
- symlink 起因の障害を疑ったら「ハング」「ループ複製」「dangling 化」は別の故障
  モードとして切り分け、フィクスチャで実測してから直すこと。
