#!/usr/bin/env python3
"""FolioCapture book.md -> NotebookLM 用の章分割ソースを生成する汎用ヘルパー。

書籍ごとに構造が異なるため、境界判断は呼び出し側(Claude)が book.md を検査して引数で与える。
本スクリプトは機械的処理のみ担当する:
  1. 本編ページ範囲 [--start-page, --end-page] だけを残す(表紙/前付け/索引/奥付を除外)
  2. OCRノイズ除去(記号のみ行・単独ページ番号・章タイトルのランニングヘッダ)
  3. 章で分割(--chapters "PAGE:TITLE;..." を優先。無ければ --chunk-pages でサイズ分割)
  4. 任意で節番号 N.M / N.M.K を見出し化(--section-heading。章内で既出番号は
     ランニングヘッダの繰り返しとみなし破棄)
  5. 各ソースに書名ヘッダを付けて outdir に書き出し、マニフェストを標準出力に表示

例:
  python3 clean_split.py --input book.md --outdir out \
    --title "うかる！情報処理安全確保支援士 2026年版" --author 上原孝之 \
    --start-page 22 --end-page 438 --section-heading \
    --chapters "22:第1章 情報セキュリティ及びITの基礎;65:第2章 情報セキュリティにおける脅威;..."
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

PAGE_RE = re.compile(r"^##\s*Page\s+(\d+)\s*$")
FM_RE = re.compile(r"^---\s*$")
PAGENUM_RE = re.compile(r"^\s*\d{1,4}\s*$")
SYMBOLS_ONLY_RE = re.compile(
    r"^[\s　\^＼／\\/・…\.。、,，･\-—―~〜；;:：'\"`｀＿_=＝\*※©®™°|｜<>＜＞\(\)（）\[\]【】○●◯◆■□▪◦‣]+$"
)
SECTION_RE = re.compile(r"^([1-9][0-9]?)\.(\d{1,2})(?:\.(\d{1,2}))?(?:[\s　]+(.*))?$")


def parse_book(md: str):
    lines = md.splitlines()
    i = 0
    if lines and FM_RE.match(lines[0]):
        i = 1
        while i < len(lines) and not FM_RE.match(lines[i]):
            i += 1
        i += 1
    pages, no, cur = [], None, []
    for ln in lines[i:]:
        m = PAGE_RE.match(ln)
        if m:
            if no is not None:
                pages.append((no, cur))
            no, cur = int(m.group(1)), []
        elif no is not None:
            cur.append(ln)
    if no is not None:
        pages.append((no, cur))
    return pages


def clean(lines, headers):
    out = []
    for ln in lines:
        s = ln.strip()
        if not s:
            out.append("")
            continue
        if SYMBOLS_ONLY_RE.match(s) or PAGENUM_RE.match(s) or s in headers:
            continue
        out.append(s)
    res = []
    for s in out:
        if s == "" and (not res or res[-1] == ""):
            continue
        res.append(s)
    while res and res[0] == "":
        res.pop(0)
    while res and res[-1] == "":
        res.pop()
    return res


def is_section_number(s):
    m = SECTION_RE.match(s)
    return bool(m) and not (m.group(4) or "").strip()


def is_toc_page(lines):
    """章扉/ミニ目次ページ判定: 節番号が近接して連続(目次パターン)。本文は節間に段落が入る。"""
    ne = [s for s in lines if s.strip()]
    idx = [i for i, s in enumerate(ne) if is_section_number(s)]
    if len(idx) < 3:
        return False
    return sum(1 for a, b in zip(idx, idx[1:]) if b - a <= 3) >= 2


def render(pages, section_heading, headers):
    """cleaned pages -> markdown 行リスト。任意で節見出し化(N.M+タイトル、章内 seen で重複除去)。
    章扉ミニ目次ページ(本文と重複するナビ)は section_heading 時に丸ごとスキップ。"""
    out, seen = [], set()
    for _no, raw in pages:
        lines = clean(raw, headers)
        if section_heading and is_toc_page(lines):
            continue
        n = len(lines)
        j = 0
        while j < n:
            ln = lines[j]
            if section_heading:
                m = SECTION_RE.match(ln)
                if m:
                    num = f"{m.group(1)}.{m.group(2)}" + (f".{m.group(3)}" if m.group(3) else "")
                    title = (m.group(4) or "").strip()
                    consumed = 1
                    if not title:
                        k = j + 1
                        while k < n and not lines[k].strip():
                            k += 1
                        if k < n and not is_section_number(lines[k].strip()):
                            title = lines[k].strip()
                            consumed = (k - j) + 1
                    if num not in seen:  # 既出=ランニングヘッダの繰り返し
                        seen.add(num)
                        title = title.lstrip("・•●○◦‣ 　")
                        lvl = "###" if m.group(3) else "##"
                        out += ["", f"{lvl} {num} {title}".rstrip(), ""]
                    j += consumed
                    continue
            if PAGENUM_RE.match(ln):
                j += 1
                continue
            out.append(ln)
            j += 1
        out.append("")
    res = []
    for s in out:
        if s == "" and (not res or res[-1] == ""):
            continue
        res.append(s)
    return res, seen


def safe(name):
    return re.sub(r'[\\/:*?"<>|]', "", name).strip().replace(" ", "_")[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--title", default="")
    ap.add_argument("--author", default="")
    ap.add_argument("--start-page", type=int, default=None)
    ap.add_argument("--end-page", type=int, default=None)
    ap.add_argument("--chapters", default="", help='"PAGE:TITLE;PAGE:TITLE;..." 章開始ページと見出し')
    ap.add_argument("--chunk-pages", type=int, default=40, help="章指定が無い場合のサイズ分割単位")
    ap.add_argument("--section-heading", action="store_true", help="節番号 N.M を見出し化")
    ap.add_argument("--note", default="試験合格に必要な部分のみ抽出したNotebookLM学習ソース(前付け・目次・索引・事務情報を除外)。")
    args = ap.parse_args()

    pages = parse_book(args.input.read_text(encoding="utf-8"))
    if not pages:
        print("no pages", file=sys.stderr); sys.exit(1)
    total = len(pages)
    start = args.start_page or pages[0][0]
    end = args.end_page or pages[-1][0]
    content = [(no, ls) for no, ls in pages if start <= no <= end]

    # 章境界の決定
    chapters = []  # (start_page, title)
    if args.chapters.strip():
        for tok in args.chapters.split(";"):
            tok = tok.strip()
            if not tok:
                continue
            p, _, t = tok.partition(":")
            chapters.append((int(p), t.strip()))
        chapters.sort()
    else:  # サイズ分割
        idx = 0
        for i in range(0, len(content), args.chunk_pages):
            idx += 1
            chapters.append((content[i][0], f"Part {idx:02d}"))

    headers = {t for _, t in chapters if t}  # 章タイトルの単独行=ランニングヘッダとして除去

    args.outdir.mkdir(parents=True, exist_ok=True)
    book_head = (f"# {args.title}\n" if args.title else "")
    if args.author:
        book_head += f"著者: {args.author}\n"
    book_head += f"> {args.note}\n"

    written = []
    for ci, (cstart, title) in enumerate(chapters):
        cend = chapters[ci + 1][0] - 1 if ci + 1 < len(chapters) else end
        seg = [(no, ls) for no, ls in content if cstart <= no <= cend]
        body, _ = render(seg, args.section_heading, headers)
        m = re.match(r"第(\d+)章", title)
        seq = f"{int(m.group(1)):02d}" if m else f"{ci + 1:02d}"
        fname = f"{seq}_{safe(title) or 'part'}.md"
        text = f"{book_head}\n# {title}\n\n" + "\n".join(body) + "\n"
        (args.outdir / fname).write_text(text, encoding="utf-8")
        written.append((fname, len(text)))

    print(f"total pages: {total} / content: {start}-{end} ({len(content)}p)")
    print(f"chapters: {len(chapters)}  section-heading: {args.section_heading}")
    for f, n in written:
        print(f"  {f}\t{n:,} chars")
    print(f"-> {args.outdir}")


if __name__ == "__main__":
    main()
