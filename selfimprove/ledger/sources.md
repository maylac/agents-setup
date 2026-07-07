# 蒸留元台帳 (③ 外部知見の取り込み)

`/self-improve sources` が巡回する外部ソースの台帳。`rot_check.py` が `last_checked + cadence_days` を過ぎた行を週次レポートに「巡回期限」として列挙する。

運用ルール:
- 巡回したら結果の採否に関わらず `last_checked` を当日に更新する
- 採用は [adoption-log.md](adoption-log.md)、見送りは [rejection-log.md](rejection-log.md) に必ず記録する(見送り記録の方が資産)
- 3回連続で収穫ゼロのソースは cadence を倍にするか行ごと削除する(台帳自体も腐らせない)
- kind: `x-account`(プロフィール巡回) / `x-search`(検索クエリ) / `blog` / `repo`(上流diff確認)

| id | url | kind | cadence_days | last_checked | 備考 |
|---|---|---|---|---|---|
| takasek-x | https://x.com/takasek | x-account | 14 | 2026-07-08 | 本エコシステムの元ネタ。ハーネス運用の一次知見が濃い |
| oikon48-x | https://x.com/oikon48 | x-account | 14 | 2026-07-08 | Anthropic公式記事の日本語一次要約が速い |
| claudecode84-x | https://x.com/claudecode84 | x-account | 30 | 2026-07-06 | fable5実装の元記事著者。長文Article中心 |
| u1-x | https://x.com/u1 | x-account | 30 | 2026-07-08 | compact強化plugin作者。compact問題再発時は優先巡回 |
| anthropic-eng | https://www.anthropic.com/engineering | blog | 30 | 2026-07-08 | 公式エンジニアリングブログ(loops設計記事など) |
| cc-changelog | https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md | repo | 30 | 2026-07-08 | Claude Code本体の変更点。廃止APIの早期検知 |
| cc-x-search-ja | x-search:"Claude Code (skill OR hooks OR CLAUDE.md) lang:ja" | x-search | 14 | 2026-07-08 | `opencli twitter search` で定例巡回 |
| superpowers-upstream | https://github.com/obra/superpowers | repo | 30 | 2026-07-08 | pin済み外部pluginの上流diff確認 |
| anthropic-skills-upstream | https://github.com/anthropics/skills | repo | 30 | 2026-07-08 | pin済み公式skillパックの上流diff確認 |
