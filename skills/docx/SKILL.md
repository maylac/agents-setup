---
name: docx
description: "Standalone DOCX tooling: inspect or edit OOXML, tracked changes, and docx-js output when a document plugin is unavailable or low-level control is needed."
license: Proprietary. LICENSE.txt has complete terms
---

# DOCX creation, editing, and analysis

## Choose the workflow

Use an explicitly requested tool or document skill. For ordinary Word creation and visual QA, prefer the installed `documents:documents` skill when available. This skill supplies standalone scripts and low-level OOXML guidance; load it when those are needed.

Resolve `scripts/` from this skill's directory, not the task directory. Check the dependencies for the chosen operation; LibreOffice, Pandoc, and Poppler are optional installations, not guaranteed host capabilities. Preserve the user's template, page format, and authorship conventions.

## Quick Reference

| Task | Approach |
|------|----------|
| Read/analyze content | `pandoc` or unpack for raw XML |
| Create new document | Use `docx-js` - see [creation guide](references/docx-js.md) |
| Edit existing document | Unpack → edit XML → repack - see [editing guide](references/editing.md) |

### Converting .doc to .docx

Legacy `.doc` files must be converted before editing:

```bash
python scripts/office/soffice.py --headless --convert-to docx document.doc
```

### Reading Content

```bash
# Text extraction with tracked changes
pandoc --track-changes=all document.docx -o output.md

# Raw XML access
python scripts/office/unpack.py document.docx unpacked/
```

### Converting to Images

```bash
python scripts/office/soffice.py --headless --convert-to pdf document.docx
pdftoppm -jpeg -r 150 document.pdf page
```

### Accepting Tracked Changes

To produce a clean document with all tracked changes accepted (requires LibreOffice):

```bash
python scripts/accept_changes.py input.docx output.docx
```

---

## Operation-specific guidance

- For new documents using docx-js, read [creation and layout rules](references/docx-js.md).
- For existing documents, comments, or tracked changes, read [package editing](references/editing.md).
- Open only the guide needed for the current operation. Validate the resulting package, and render pages for visual inspection when layout or formatting changed.

## XML Reference

OOXML patterns for hand-editing `word/document.xml` (runs, formatting, comments, tracked changes) are in [references/xml-reference.md](references/xml-reference.md).

## Dependencies

- **pandoc**: Text extraction
- **docx**: `npm install -g docx` (new documents)
- **LibreOffice**: PDF conversion (auto-configured for sandboxed environments via `scripts/office/soffice.py`)
- **Poppler**: `pdftoppm` for images
