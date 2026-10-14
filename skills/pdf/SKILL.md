---
name: pdf
description: "Standalone PDF extraction, page manipulation, OCR, and form filling when a PDF plugin is unavailable or low-level tooling is needed."
license: Proprietary. LICENSE.txt has complete terms
---

# Standalone PDF Processing

Use the user's requested tool or PDF skill. When `pdf:pdf` is installed, prefer its artifact workflow for visual creation and inspection. This skill provides standalone tools and form helpers. Resolve bundled `scripts/` paths from this skill's directory.

## Select the operation

| Request | Start with | Load only if needed |
| --- | --- | --- |
| Read text or tables | `pdftotext -layout`, pypdf, or pdfplumber; inspect layout when extraction order is ambiguous | [Precise extraction and tables](reference.md#advanced-python-techniques) |
| Merge, split, rotate, crop, or repair | pypdf or qpdf; verify page count and affected pages | [Page operations](reference.md#advanced-command-line-operations) |
| Fill an existing form | Determine whether it has fillable fields before editing | [Form workflow and bundled scripts](forms.md) |
| Extract images or render pages | pdfimages, pdftoppm, or pypdfium2 | [Rendering](reference.md#pypdfium2-library-apachebsd-license) and [image extraction](reference.md#extract-figuresimages-from-pdf) |
| Read a scanned PDF | Render pages, then OCR with an available engine; retain page associations | [Extraction troubleshooting](reference.md#text-extraction-issues) |
| Create a PDF | ReportLab with fonts covering the required language; render the result | [ReportLab examples](reference.md#reportlab-advanced-features) |
| Use JavaScript | pdf-lib or pdfjs-dist | [JavaScript reference](reference.md#javascript-libraries) |
| Open or protect an encrypted file | Use the provided credentials and an available PDF library | [Encryption troubleshooting](reference.md#encrypted-pdfs) |

## Preserve correctness

- Check the required library or CLI before running the chosen operation. Installing this skill does not install Poppler, LibreOffice, OCR engines, or Python libraries.
- Keep the source file intact unless replacement was requested. Preserve searchable text, annotations, bookmarks, forms, and metadata relevant to the task.
- For ReportLab's built-in fonts, Unicode subscript/superscript glyphs can render as black boxes. Use `<sub>` and `<super>` in Paragraph objects, or position smaller text manually on a canvas. Use an appropriate embedded font for Japanese and other uncovered glyphs.
- For scans and tables, verify extracted values against the relevant page images; do not treat OCR as exact evidence.
- After editing, reopen the file and check page count and requested content. Render affected pages when appearance matters. Form edits also need the validation steps in `forms.md`.
- State an unavailable operation or unverified rendering clearly. A successful write is not proof of visual correctness.
