# t2 正解キー(モデルに渡さない)

## BUG-1: summarize の並び順が docstring と逆(確実)

docstringは "sorted by total descending" だが `sorted(..., key=lambda kv: kv[1])`
は昇順。`reverse=True` の欠落。
壊れる例: `summarize([(d, "a", 10), (d, "b", 90)])` → `[("a",10),("b",90)]`
(期待は b が先頭)。

## BUG-2: render の IndexError(確実)

`for i in range(limit)` が `summary` の長さを確認しない。カテゴリ数が
`limit`(既定5)未満だと `summary[i]` で IndexError。
壊れる例: `render([("a", 10)])`。
修正: `range(min(limit, len(summary)))`。

## BUG-3: parse_entry の None が下流契約に乗っていない(設計欠陥)

`except Exception: return None` で None を返すが、`last_n_days` /
`summarize` は None を除去せず `e[0]` / アンパックで TypeError になる。
「パース失敗行を除去する契約がどこにもない」ことを指摘していれば正解。
広い `except Exception` の握りつぶし自体への指摘も同一バグ扱いで可。

## NOT-A-BUG: last_n_days の境界は正しい

`cutoff = today - timedelta(days=n)` + `e[0] > cutoff and e[0] <= today` は
today を含む直近 n 日ちょうど(n=7, today=7/12 → 7/6〜7/12 の7日分)。
これを off-by-one と指摘したら false positive として -1点。
