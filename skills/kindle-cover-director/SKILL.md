---
name: kindle-cover-director
description: Kindle電子書籍の表紙デザインブリーフ(cover_pack)を作る。画像生成そのものは行わない(人間または外部ツールがcover/cover.pngを配置)。タイトル文面にはkindle-listing-builderを使う。
---

# Kindle Cover Director

Kindle出版パイプライン(設計書: `~/tasks/kindle-publishing-pipeline-design.md`)のステージ6。
表紙の設計を「そのまま外注・画像生成ツールに渡せる指示書」の粒度まで落とす。表紙はクリック率を左右する最重要要素のひとつであり、安っぽい表紙はそれだけで避けられる。

## Workflow

1. **入力の確認**
   - `packs/book_brief.yaml` を読む。`packs/listing_pack.yaml` があれば確定タイトルを使い、なければ仮タイトルで進めて後で更新する。
2. **競合表紙の観察**
   - 同カテゴリ上位本の表紙傾向(配色・文字量・写真かイラストか)を観察し、「並んだ時に埋もれない差分」を1つ決める。
3. **デザインブリーフ作成**
   - コンセプト、メインコピー(表紙に載せる文言)、配色(基調+アクセント)、構図、フォントの方向性、避けること。
4. **視認性チェック項目の定義**
   - Kindleストアのサムネイルサイズ(検索結果一覧の小サイズ)でタイトルが読めるか、白背景でも輪郭が出るか、をチェック項目として明文化する。
5. **成果物の書き出しと画像待ち**
   - `packs/cover_pack.yaml` を `status: pending_asset` で書き出す。
   - 人間または外部ツールが `cover/cover.png` を配置したら、視認性チェックを実施して `status: ok` に更新する。**画像ファイルが存在しない限り ok にしない。**

## Output

### packs/cover_pack.yaml

```yaml
pack: cover_pack
status: pending_asset     # cover/cover.png 配置 + 視認性チェック通過で ok
created_at: <date>
inputs:
  book_brief_ref: packs/book_brief.yaml
  listing_pack_ref: packs/listing_pack.yaml   # 無ければ null(仮タイトル使用を明記)
brief:
  concept: ""
  main_copy: "<表紙に載せる文言>"
  colors: {base: "", accent: ""}
  composition: ""
  typography: ""
  avoid: ["<やらないこと>"]
  differentiation: "<同カテゴリ上位と並んだ時の差分>"
asset_path: cover/cover.png
visibility_check:
  thumbnail_readable: pending   # pending | pass | fail
  contrast_on_white: pending
```

## Decision Rules

- 画像生成はこのスキルの範囲外。ブリーフの質で表紙品質を担保する。
- KDPの表紙推奨仕様(推奨2,560×1,600px、比率1.6:1)をブリーフに明記する。
- 実在の人物・作品・商標を想起させるビジュアル指示を書かない。
