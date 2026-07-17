# モデル選定eval(軽量・決定的)

自分の代表タスクで新旧モデルを比較し、`fable-escalation` のtier表
(Fable/Opus/Sonnet/Haiku割り当て)を**推測でなく測定で**更新するための最小ハーネス。

出典: Code w/ Claude セッション(Anthropic applied AIチーム)の指針
「Build your own lightweight evals that reflect your tasks, then properly
configure the model using the right dials」(Linas Beliūnas記事 2026-06-12 経由)。

## いつ回すか

- 新モデルのリリース時(例: Sonnet 5.x、Opus 5)
- tier表の割り当てに迷いが生じたとき(「このタスクはSonnetで足りるのか?」)
- effort設定の変更を検討するとき(medium既定を動かす前)

## どう回すか

```bash
# 同一タスクを比較したいモデルそれぞれで実行
./run.sh sonnet t2
./run.sh opus t2
# 出力は outputs/<date>-<model>-<task>.md に保存される
```

## どう採点するか

各タスクファイル末尾の「採点基準」チェックリストで人間が採点する。
基準は決定的(検出数、事実誤りの有無、形式遵守)に寄せてあり、LLM judgeは
使わない — Hermes軌跡eval(`~/.hermes/scripts/hsat_eval.py`)と同じ設計判断
(非決定性・コスト・故障面を増やさない)。

判定の使い方: 安いモデルが合格基準を満たすなら、そのタスク種別は安いtierへ
下げる。落ちるなら現行tierを維持。結果は `fable-escalation` スキルのtier表と
`results.md` に反映する。

## 構成

- `tasks/` — 代表タスク定義(プロンプト+採点基準)。実タスクから随時追加する。
- `fixtures/` — タスクが参照する固定素材(既知バグ入りコード等)と正解キー。
  正解キーはモデルに渡さないこと。
- `outputs/` — 実行結果(gitignore対象)。
- `results.md` — 採点の記録と、そこから行ったtier表更新の履歴。
