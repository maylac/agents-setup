---
name: repo-scaffold
description: 新規リポジトリを起こすとき、この環境の標準構成(チェック可能な基準を持つAgent Guide、docs/learnings、必要に応じてBacklog.md)を再現する。「新しいレポジトリを作って」「プロジェクトを立ち上げて」「リポジトリを初期化して」と言われたときに使用する。
---

# repo-scaffold — 標準リポジトリ構成の再現

## 目的

2026-07-07のFable抽出プレイブックで確立した構成を、新規リポジトリで機械的に再現する。
静的テンプレートのコピーではなく、プロジェクトの種別に合わせて**生成**する。

## 生成物(標準セット)

```
<repo>/
├── CLAUDE.md → AGENTS.md への symlink   (エージェント間共有のため AGENTS.md が正本)
├── AGENTS.md                             (Agent Guide — 下記形式)
├── docs/learnings/                       (extract-approachスキルの出力先。.gitkeepを置く)
├── .gitignore                            (言語/ツールに応じて生成)
└── backlog/                              (任意 — 下記の条件のときだけ backlog init)
```

グローバル設定(~/CLAUDE.md、rules/、hooks)は agents-setup が既に供給しているため、
リポジトリ側には**リポジトリ固有のこと以外を書かない**。重複はドリフトの温床。

## 手順

1. **プロジェクト種別の把握** — 言語・ランタイム・目的(アプリ/ライブラリ/台帳/実験)を
   ユーザーの依頼文から推定。実装に影響する不明点(テストコマンド、公開範囲)だけ確認する。
2. **git init + .gitignore** — 種別に応じた最小の .gitignore(生成物・ローカルデータ・秘密)。
3. **AGENTS.md を生成** — 下記の家風フォーマットに従う。CLAUDE.md は
   `ln -s AGENTS.md CLAUDE.md` で symlink にする。
4. **docs/learnings/.gitkeep を作成** — extract-approachスキル(グローバル配線済み)の出力先。
5. **Backlog.md 初期化(条件付き)** — 複数ステップの開発が確定している場合のみ
   `backlog init "<Project Name>"`。単発ツール・実験リポジトリには入れない(~/CLAUDE.mdの規約)。
6. **初回コミット** — `chore: scaffold repository` 等。push はユーザーが求めたときだけ。

## AGENTS.md の家風フォーマット

FolioCapture / agents-setup / hermes-hub と同型。セクションは以下の5つ、各3-6行で簡潔に:

```markdown
# Agent Guide

## Purpose
<このrepoが何で、何でないか。1-2行>

## Structure
<トップレベルの主要ディレクトリと役割。箇条書き>

## Commands
<テスト・ビルド・検証の実行コマンド。実在するものだけ書く>

## Completion Standards (checkable)
<合否判定できる基準行。必ず「A change is done only when ...」形式で、
 プロジェクト固有の証拠要求を書く。例:
 - the `<test command>` command and its output are pasted in the report and show 0 failures
 - <このrepo特有のリスク面>に触れる変更は<固有の検証>の結果を含む
 - no new dependency was added without a stated reason>

## Guardrails
<やってはいけないこと。コミット禁止物・境界・秘密の扱い>
```

### Completion Standards を書くときの基準(この節が本スキルの核心)

- 各行は**貼られた証拠**を要求する形にする(「テストが通ること」ではなく「テスト出力が貼られていること」)
- 「readable」「clean」「appropriate」のような判定不能な形容詞を使わない
- そのプロジェクトで**一番壊れると痛い面**(データ喪失・機密・公開面)に対応する行を最低1つ入れる
- 5行以内。基準は多いほど守られなくなる

## 後付け適用(既存リポジトリ)

既存repoには不足分だけ足す: AGENTS.md がなければ生成、CLAUDE.md が実体ファイルなら
内容を AGENTS.md に移して symlink 化を提案(勝手に壊さない)、docs/learnings/ を追加。
既存の Completion Standards がある場合は上書きせず「checkable か」だけレビューして提案する。

## 関連

- extract-approach スキル — learnings ノートの書式と発火条件
- ~/workspace/agents-setup — グローバル設定の正本(このスキルはrepoローカル分のみ担当)
- ~/CLAUDE.md「Development Workflow Standard: Backlog.md」— backlog init の判断基準
