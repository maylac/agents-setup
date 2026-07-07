---
name: markdown-to-epub
description: Convert markdown documents and chat summaries into formatted EPUB ebook files that can be read on any device or uploaded to Kindle.
---

# Markdown to EPUB

Turn a markdown file (research doc, article, chat summary) into a portable `.epub`. Use H1 headings as chapter breaks.

## Primary path: pandoc

```bash
brew install pandoc   # once
pandoc input.md -o output.epub \
  --metadata title="My Title" \
  --metadata author="Author Name" \
  --toc --split-level=1
```

- `--split-level=1` makes each top-level `#` heading a chapter.
- Add a cover with `--epub-cover-image=cover.png`.
- Add CSS with `--css=style.css` if you want custom typography.

## Fallback: Python (ebooklib)

If pandoc is unavailable:

```bash
pip install ebooklib markdown
```

```python
import re, markdown
from ebooklib import epub

book = epub.EpubBook()
book.set_title("My Title"); book.add_author("Author Name")

# Split on H1 headings
parts = re.split(r'(?m)^# ', open("input.md").read())
chapters = []
for i, part in enumerate(p for p in parts if p.strip()):
    title = part.splitlines()[0].strip()
    html = markdown.markdown("# " + part)
    ch = epub.EpubHtml(title=title, file_name=f"chap_{i}.xhtml", content=html)
    book.add_item(ch); chapters.append(ch)

book.toc = chapters
book.add_item(epub.EpubNcx()); book.add_item(epub.EpubNav())
book.spine = ["nav", *chapters]
epub.write_epub("output.epub", book)
```

## Verify

- Open `output.epub` in Apple Books (macOS) to eyeball chapters and the TOC.
- Validate structure with `epubcheck output.epub` (`brew install epubcheck`) if strict conformance matters.

## Kindle

Send-to-Kindle accepts `.epub` directly now — no MOBI conversion needed. Email it to your `@kindle.com` address or use the Send to Kindle app.
