# 実機が参照する未コミット作業ツリーを、本体 checkout に触れずに PR 化する

- 日付: 2026-10-13
- 領域: agents-setup / リポジトリ運用と Remote Control worktree
- 種別: design-tradeoff

## 問題

`~/AGENTS.md` `~/.claude/CLAUDE.md` `~/.agents/skills/*` は main checkout の**作業ツリー**を symlink で参照している。その作業ツリーに 151 件の未コミット差分(2026-08-17 以降 2 か月分)が溜まり、Remote Control が切る worktree は古い HEAD から始まるため、モバイル起動のセッションは毎回古い指示(Hermes・Paseo・gpt-5.6 系)を読んでいた。作業は worktree 側で行い、main checkout の index と作業ツリーには書けない(他セッションが同時に使う)。

## 試して駄目だった道

- `git -C main add -A` してコミット: main の index を書き換えるので禁止。他セッションの `git status` 観測も変わる。
- `git -C main diff > patch` + 未追跡ファイルを rsync で複製: 2 系統の複製で削除・symlink・実行ビットの扱いが分かれ、`.bak` や `.DS_Store` など ignore 対象を拾いやすい。
- main → worktree を rsync: `.claude/worktrees` 配下に自分自身が居るため再帰し、`--delete` の除外を誤ると worktree 側の `.claude/settings.json` を消す。

## 効いたアプローチ

1. main の index を一時ファイルにコピーし、`GIT_INDEX_FILE=<tmp> git -C main add -A` で**一時 index だけ**に作業ツリーを読み込ませ、`write-tree` で tree オブジェクトを得る(main の index・作業ツリーは不変。`git status` の件数で確認)。
2. worktree で新ブランチを切り `git read-tree -u --reset <tree>` → commit。`rev-parse HEAD^{tree}` が同じ tree であることを確認。
3. 独立検証: main と worktree の全ファイル sha256(`.git` `.claude/worktrees` `*.bak` `.DS_Store` 除外)と `ls-files -s` の symlink 行を diff して空。
4. マージ後の main は `reset --soft origin/main && reset -q` で HEAD だけ動かす(`merge --ff-only` はローカル変更と衝突して拒否される)。作業ツリーは書かないので、残差分は意図した sanitize 分だけになる。

## なぜ効いたか

git の index は `GIT_INDEX_FILE` で差し替えられ、`add -A` は index と object store にしか書かない。tree は object store 経由で worktree 側から参照できるため、作業ツリーの複製が不要で、ignore 規則・symlink・mode は git 自身の解釈で保存される。裏づけ: `git status --short | wc -l` が前後とも 151、`FILES-IDENTICAL` と `SYMLINKS-OK`、`tests/*.test.sh` 7 本と `validate.sh` が PASS。

## 一般化できる原則

- 他プロセスが使っている checkout の作業ツリーを取り込む場合は、`GIT_INDEX_FILE` の一時 index で tree を作り、別 worktree で `read-tree` すること。元 checkout の index と作業ツリーは書かない。
- ランタイムが symlink で作業ツリーを参照している構成では、「コミット済み」と「実機で有効」が一致しない。スナップショット PR を定期的に出すか、symlink 先を tag/branch の checkout に変える。
