# 採用ログ (③→② 取り込んだ知見と行き先)

外部知見を採用したら1エントリ追記する。「どこに定着させたか(行き先)」まで書いて初めて採用完了。

書式:
```
## YYYY-MM-DD タイトル
- source: URL または sources.md の id
- 要旨: 1〜2行
- 行き先: skill:<name> / CLAUDE.md / rules/<file> / hook:<file> / script:<file> / memory:<file>
```

---

## 2026-07-08 自己改善3分類と見送り記録の資産化 (takasek)
- source: https://x.com/takasek/status/2074359553815400770
- 要旨: ハーネス改善は ①腐敗検知(7系統監査) ②教訓定着 ③外部知見取り込み の3種。③は台帳化+定例化し、採用より「何を採用しなかったか」の記録が資産になる
- 行き先: selfimprove/ 全体の設計骨格 + script:rot_check.py + この台帳群

## 2026-07-08 追記だけの教訓ファイルは腐る→行数上限と強制圧縮 (anz__519)
- source: https://x.com/anz__519/status/2074503477737521178
- 要旨: lessons/memoryは追記オンリーだと古いルールが現状と矛盾し始める。行数上限を切って強制圧縮する
- 行き先: script:rot_check.py (LESSONS_LINE_CAP=50) + skill:self-improve (distillモードの圧縮手順)

## 2026-07-08 ループ設計の原則 (Anthropic loops記事 / oikon48要約)
- source: https://x.com/oikon48/status/2074271110431220223
- 要旨: 決定的な作業はスクリプト化しLLMに毎回考えさせない。定型は軽量モデル・判断だけ強いモデル。失敗パターンは個別修正でなくSKILLに反映してシステム全体を改善
- 行き先: selfimprove設計原則(README) — 週次rot_checkはトークン0のスクリプト、判断ループはスキル手順書化

## 2026-07-08 最強モデルの判断力を設定ファイルに焼き込む (naritai_hojosen)
- source: https://x.com/naritai_hojosen/status/2074470191757766997
- 要旨: モデルが消えても、そのモデルが書いたルールは残る。サブスク終了前の最優先はコードよりハーネスの再設計
- 行き先: 本エコシステムの目的定義(README) — Fable在任中に判断基準をチェックリスト化し、後続モデルが実行できる形にする
