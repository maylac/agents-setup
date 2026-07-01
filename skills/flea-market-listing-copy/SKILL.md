---
name: flea-market-listing-copy
description: Create Japanese listing copy for Mercari, Rakuma, Yahoo! Flea Market, and similar resale or flea-market platforms. Use when the user asks for sellable product titles, item descriptions, condition notes, search keywords, price recommendations, price-negotiation replies, comment responses, or photo-based product research for secondhand listings.
---

# Flea Market Listing Copy

## Workflow

Start from the user's actual item facts. If important facts are missing, draft conservatively and place unknowns under `要確認`; ask follow-up questions only when the missing information would create a false claim, safety issue, rights issue, or unusable listing.

For a normal listing request, produce the complete answer in one pass:

1. `タイトル候補`: 3 concise Japanese titles with different angles.
2. `出品説明`: a paste-ready description.
3. `状態・注意点`: transparent condition notes, including defects and uncertainty.
4. `価格提案`: recommended list price, quick-sale price, and negotiation-aware price when current market data is relevant.
5. `検索キーワード`: relevant keywords only; avoid spam-like stuffing.
6. `要確認`: only facts that cannot be known from the user's text, photos, or verified sources.
7. `購入前コメント対応`: short buyer-facing replies only when useful or requested.

When the user provides photos and asks to research product information, inspect the photos first, identify visible model numbers/SKUs/labels/accessories, then verify product specs from official or reliable current sources before drafting. Also check current resale/new-price signals when price will affect the listing; cite the source briefly in the answer.

When the user specifies a platform, follow that platform's current constraints if known from the provided context. If exact limits, prohibited-item rules, fee rules, shipping rules, or price-comparison data matter and are not in context, verify them before presenting them as current facts.

## Photo-Based Listings

- Treat visible external characteristics as facts when the image is clear enough: color, key layout, included visible accessories, obvious scratches, missing keys, labels, and visible damage. Use direct wording such as `US/ANSI配列です` or `USBレシーバー付きです`; do not write `と思われます` for clear visual facts.
- Reserve uncertainty for internal, operational, or off-camera facts: battery health, full key operation, charging behavior, odors, prior repairs, purchase date, warranty, hidden damage, and accessories not shown or not stated by the user.
- If the photo label or SKU is partly readable, state the strongest safe identification and separate the evidence, for example `背面ラベルから Keychron B1 Pro / B1P-K1 系です`.
- If the user later adds an accessory or condition fact, incorporate it as confirmed and update the copy and price instead of asking a follow-up.
- For electronics, include a compact `要確認` list for operation and battery only when the user has not provided those facts.

## Copy Rules

- Write in natural, polite Japanese that feels like a careful individual seller, not an ad agency.
- Lead with concrete buyer value: brand/model, size, color, use case, included items, and condition.
- Use scannable short paragraphs and bullets. Avoid dense prose.
- State flaws plainly. Do not hide stains, scratches, odor, missing parts, battery degradation, name engraving, altered condition, or uncertainty.
- Avoid overclaiming words such as `新品同様`, `美品`, `正規品保証`, `完全動作`, or `最安値` unless the user provides evidence.
- Do not invent purchase date, retail price, authenticity, usage count, measurements, compatibility, or shipping method.
- Do not include seller-only disclaimers that attempt to deny buyer rights. Prefer factual notes such as `中古品のため、写真と説明をご確認ください`.
- For branded goods, keep brand names accurate and avoid counterfeit-risk language.
- For cosmetics, food, health, electronics, batteries, children's goods, or regulated categories, be extra conservative and surface safety or policy checks.

## Missing Information

If the item facts are thin, still help the user by producing a usable draft with placeholders. Put placeholders in brackets, for example `[サイズ]`, `[使用回数]`, `[傷の有無]`, and list the exact facts needed to finalize the copy.

Prioritize these facts:

- Item name, brand, model, size, color, material, and quantity.
- Condition, visible defects, smell, storage environment, and operation status.
- Included accessories, box, manual, receipt, tags, spare parts, or missing items.
- Approximate purchase time, usage frequency, reason for selling, and storage period.
- Shipping method, packing notes, and whether the item can be cleaned or tested before shipment.

Do not ask the user to provide facts that are already visible in the photos. Use placeholders or `要確認` only for facts that are genuinely unavailable.

## Output Style

Use this compact format unless the user asks otherwise:

```markdown
## 商品情報メモ
- ...

## タイトル候補
1. ...
2. ...
3. ...

## 出品説明
...

## 状態・注意点
- ...

## 価格提案
- おすすめ出品価格: ...
- 早く売りたい場合: ...
- 値下げ交渉を見込む場合: ...

## 検索キーワード
...

## 要確認
- ...
```

If the user asks for a stronger sales tone, improve clarity, ordering, and buyer reassurance first. Do not make unverifiable claims stronger.
