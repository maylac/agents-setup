---
name: exam-cram-guide
description: Build a per-exam last-day cram guide / field manual (鉄則・選び分け・罠・数字) as a self-contained HTML poster set, render it to PNG pages and a PDF, deliver it to iCloud and ship it inside Vantik's exam guides tab. Sources are the learner's own Vantik misses, the official exam guide, and pass reports. Use for 「直前に詰め込む知識と鉄則をインフォグラフィックに」「受験前インプットをまとめて」「<EXAM>のフィールドマニュアル」 for any certification (AWS SAP/DVA/CLF, IPA, PMP…).
---

# Exam cram guide

Repeated for SAP-C02 (rehearsal tips 10/18, last-day sheet 10/24) and DVA-C02 (field
manual 10/25). The HTML route is the default: text stays verbatim and editable, pages
render deterministically, and the same file ships in the app. Image-generation prompts
were used once; prefer HTML unless the user asks for illustrated posters.

## Inputs (gather first, in this order)

1. **Exam facts** from the official exam guide: question count, time, passing score,
   domain weights, question types, retirement/successor dates. Cite the URL per fact.
2. **Learner evidence** when the exam is already in Vantik: take a snapshot with
   `vantik-prod-verify` and compute latest-result-per-question misses, repeated misses,
   domain miss rates. Numbers in the guide must come from that snapshot; say the
   snapshot date. No Vantik data for a new exam → say the guide is pre-study input.
3. **Pass reports / community**: 3-6 recent write-ups; keep only recurring advice and
   mark it as experience, not spec. Reddit/Qiita/Zenn/note are fine as sources.
4. **Official service docs** for every decision rule, especially where stored answer
   keys look doubtful. Opening a page is not verification; the rule must be stated in it.

## Content rules

- Unit of content is a **decision**: condition → pick X not Y → why (one line) → trap.
  Group misses into transferable rules; never reprint copyrighted question stems.
- Each page has one job: cover/facts, rules of answering, one domain per page,
  numbers & limits table, last-morning checklist. 5-13 pages.
- Use `.rule` (鉄則) and `.trap` (罠) blocks, `.kw` tables for keyword → service mappings,
  and a yellow/orange memorization strip at the bottom of each page when the learner
  asked for "last morning" material.
- Do not invent statistics; the only numbers are official limits/dates and the
  learner's measured results. Flag uncertain stored keys as 「複数解釈あり」.
- Japanese, short sentences, service names in full on first use. Follow the design
  rules in `~/.claude/DESIGN.md` if present; the template palette already matches
  the Vantik paper/ink look.

## Build

1. Copy `assets/page-template.html` to `~/workspace/output/<exam-code>-cram-<YYYYMMDD>/<exam-code>.html`
   and write the pages. Keep every `<section class="page">` at the template size
   (1080×1527) with `.strip` header and `.foot` footer.
2. Render and check overflow (needs Playwright; run from a checkout that has it, e.g.
   reskilling-os, or `npx playwright`):

   ```bash
   node ~/.agents/skills/exam-cram-guide/scripts/render_pages.cjs <exam-code>.html --out . --pdf <EXAM>_field_manual.pdf
   ```

   It prints per-page `slack` (px between last block and footer) and `overflow`; fix any
   page with `overflow:true` or slack < 0 by cutting text, not by shrinking fonts below
   12.5 px. Look at 2-3 PNGs yourself before delivering.
3. Record sources in `sources.md` next to the HTML (URL + which claim it supports).

## Deliver

- **iCloud**: copy the PDF (and `png/`) to the learner's iCloud Drive certification
  folder (`~/Library/Mobile Documents/com~apple~CloudDocs/<資格カテゴリ>/<EXAM>/`); confirm
  the folder exists before writing and report the path.
- **Vantik exam guides** (reskilling-os `backend/reskilling_os/content/exam_guides/`):
  copy the HTML as `<guide_id>.html`, strip the grey body background so it sits in the
  app, append an entry to `manifest.json`
  (`guide_id, exam_code, title, summary, page_count, checked_at, file`), run
  `pytest backend/tests/test_exam_guides.py` and `npx vitest run src/components/ExamGuides.test.tsx`,
  run the full `npm run test:e2e` before pushing (other specs assert labels), push to
  `master`, then confirm with `vantik-prod-verify/scripts/deploy_check.sh`.
  A red CI means the guide is not live; say so.
- Reply in Japanese with: page list (one line each), what the learner should read
  tonight vs. the morning, file paths/links, and the snapshot date behind any numbers.
