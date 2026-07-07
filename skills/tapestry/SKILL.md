---
name: tapestry
description: Extract content from a URL and turn it into an action plan. Handles articles, YouTube, PDFs, and similar sources.
allowed-tools: Bash,Read,Write
---

# Tapestry: Content Extraction + Action Planning

Extract the content behind a URL, then turn it into a short, shippable action plan.

## When to Use This Skill

Activate when the user says "tapestry [URL]", "weave [URL]", "help me plan [URL]", "extract and plan [URL]", "make this actionable [URL]", "turn [URL] into a plan", or provides a URL and asks to "learn and implement from this".

**Keywords**: tapestry, weave, plan, actionable, extract and plan, make a plan, turn into action.

## Step 1: Extract the content by type

- **YouTube URL** → use the `youtube-transcript` skill.
- **`.pdf` URL** → `curl -sL "URL" -o /tmp/tapestry.pdf`, then read it with the Read tool.
- **Any other article/page** → fetch clean text via WebFetch (or Exa `web_fetch_exa`). Do not use Jina Reader (`r.jina.ai`) — deprecated 2026-07, API unreliable.

Keep the extracted text in a working file if it's long.

## Step 2: Write the action plan

Always produce an action plan after extracting — this is the point of the skill. Save it as `Action Plan - [Brief Quest Title].md`.

```markdown
# Action Plan - [Quest Title]

## Source
- URL: [URL]

## Key Lessons
- [Actionable lesson, not just a summary point]

## 4-8 Week Quest
[One specific outcome]

## Reps
1. Rep 1 (this week): [small shippable result]
2. Rep 2: [next iteration]
3. Rep 3: [next iteration]
4. Rep 4: [next iteration]
5. Rep 5: [final integration]

## Next Step
[First concrete action and deadline]
```

Plan quality:
- Extract actionable lessons, not summaries.
- Define one specific 4-8 week quest.
- Rep 1 must be shippable this week; Reps 2-5 are progressive iterations.

Close by asking: **"When will you ship Rep 1?"** — a plan without a committed first ship rarely happens.
