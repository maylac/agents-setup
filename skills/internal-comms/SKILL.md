---
name: internal-comms
description: Draft internal company communications such as status reports, leadership updates, 3P updates, newsletters, FAQs, incident reports, and project updates. Use when the user explicitly asks for an internal communication or names one of these formats.
license: Complete terms in LICENSE.txt
---

## When to use this skill
To write internal communications, use this skill for:
- 3P updates (Progress, Plans, Problems)
- Company newsletters
- FAQ responses
- Status reports
- Leadership updates
- Project updates
- Incident reports

## How to use this skill

To write any internal communication:

1. **Identify the communication type** from the request
2. **Load the appropriate guideline file** from the `examples/` directory:
    - `examples/3p-updates.md` - For Progress/Plans/Problems team updates
    - `examples/company-newsletter.md` - For company-wide newsletters
    - `examples/faq-answers.md` - For answering frequently asked questions
    - `examples/general-comms.md` - For anything else that doesn't explicitly match one of the above
3. **Follow the specific instructions** in that file for formatting, tone, and content gathering

If the communication type or audience is blocking and cannot be inferred, ask a concise clarification. Otherwise draft with explicit assumptions and include optional questions the user can answer to refine it.

## Keywords
3P updates, company newsletter, company comms, weekly update, faqs, common questions, updates, internal comms
