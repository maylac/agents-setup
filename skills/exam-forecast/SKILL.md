---
name: exam-forecast
description: >
  Analyze past mock/practice exams for the same certification to surface patterns
  — domain weighting, recurring trap types, favored question styles, scenario-vs-recall
  mix — and forecast likely emphases for the upcoming exam. Use when the user says
  "what's on the exam", "analyze past exams", "predict the exam", or shares past
  mock exams.
argument-hint: "[exam name, with past mock exams shared or paths to them]"
---

# /exam-forecast

1. Load `~/tasks/study/profile.md` if it exists (target exam, exam date, weak domains); otherwise ask which exam.
2. Apply the workflow below.
3. Intake past mock exams (PMI Study Hall exports, Udemy mock-exam exports, PDF, paste, or paths). Confirm sample size.
4. Analyze each: format, domain coverage, question style, scenario density, recurring traps.
5. Cross-exam pattern analysis — what's stable, what varies.
6. Combine with the exam content outline to produce forecast: domain weights, format, recurring emphases, study emphasis.
7. Write `~/tasks/study/exam-forecasts/[exam]/forecast-[YYYY-MM-DD].md`. Framed as weighting heuristic, not prediction.

---

## Purpose

Every certification exam's question bank has fingerprints. The same scenario structures recur. The same traps come back. The same domain ratios repeat. Learners who study prior mock exams study smarter. This skill analyzes the prior mock/practice exams you have and surfaces the patterns.

Not magic. A forecast, not a prediction. The skill cannot tell you what's on the exam — it can tell you what's been on past mock exams and what's likely to recur based on the exam content outline.

## Confidence discipline

- Pattern analysis (which domains appeared, how many questions per topic, how often scenario vs. recall) — confident where the exams are clearly in front of me.
- Inference about likely emphasis on the upcoming exam — `[UNCERTAIN]` is the default; these are forecasts, not certainties. Explicitly frame as "based on the [N] past mock exams you shared, [topic] appeared in [M]. Your upcoming exam may emphasize it, or the item bank may rotate — use this as a weighting for review time, not a prediction."
- If only 1-2 past mock exams are available, say so explicitly — any pattern inferred from 1 exam is noise.
- If no past mock exams are available, the skill can't forecast. Say so; fall back to exam-content-outline-based "these are the domains covered" only.

## Load context

- User-provided past mock exams (Study Hall exports, Udemy mock-exam exports, PDF, pasted text, paths)
- Optional: the exam content outline for the current certification (for "what's officially in scope")

## Workflow

### Step 1: Intake

- Which certification are we forecasting for?
- Which mock-exam sets are available (paths under `~/workspace/udemy-transcripts/` or Study Hall export files)?
- Are they from official practice material, or third-party question banks?
- Are any of them a different format/length vs. the real exam?
- The exam content outline for the target certification?

If fewer than 3 past mock exams: flag as thin sample. Pattern inference is weaker.
If exams are from different question banks: some patterns transfer (question style, scenario vs. recall ratio); bank-specific patterns don't.

### Step 2: Read each past mock exam

For each past mock exam:

- Format (number of questions, length, time limit)
- Domain coverage (which domains tested, in what proportion)
- Question style (scenario-based, single-fact recall, "select all that apply", drag-and-drop, mix)
- Scenario density (fact-heavy situational questions, sparse definitional questions, or calculation prompts)
- Recurring traps (e.g., always hides a distractor that's true-but-not-the-best-answer; always tests the exception rather than the rule)
- Scenario vs. recall ratio
- Unusual structures (multi-select, hotspot, ordering, etc.)

### Step 3: Cross-exam pattern analysis

Roll up what's consistent across exams:

**Stable patterns (appeared in most/all past exams):**
- Domain weights (e.g., "risk management accounts for ~30% of questions consistently")
- Question style (e.g., "mostly scenario-based, few pure-recall")
- Recurring emphases (e.g., "always tests stakeholder engagement even when it's a minor domain")

**Variable patterns (appeared in some but not all):**
- Calculation-heavy questions (e.g., "EVM math appeared in 2 of 4 mock sets")
- Format differences between banks

**Absent patterns worth noting:**
- Topics in the exam content outline that never appear in these mock sets — don't skip them, but don't over-weight either
- Topics tested in mock sets that aren't in the current outline — probably third-party noise

### Step 4: Forecast for the upcoming exam

Combine pattern analysis with the exam content outline:

```markdown
# Exam Forecast — [certification] — [date]

**Past mock exams analyzed:** [N]
**Sample confidence:** [thin (<3) / moderate (3-5) / strong (6+)]
**Caveats:** [e.g., "two mock sets were third-party banks; the real exam weights domains per the official ECO. Pattern transfer is partial."]

---

## Domain weighting (historical)

| Domain | Mock exam weight (avg) | In official outline? | Forecast weight |
|---|---|---|---|
| [domain 1] | [%] | [yes/partial/no] | [heavier / stable / lighter] |

## Question-style forecast

- **Format likely:** [X scenario + Y recall + Z multi-select, or similar]
- **Scenario density:** [fact-heavy / sparse / mixed]
- **Question framing:** [best-answer selection / select-all / ordering]

## Recurring emphases to watch

- [topic A] — appeared in [M of N] mock sets. Weighted 3-5x its outline share.
- [topic B] — [pattern]
- [trap pattern] — e.g., "true-but-not-best-answer distractors"

## Topics in the outline but rarely in these mock sets

[list — don't skip, but don't over-weight]

## Study emphasis recommendation

Based on mock-exam patterns AND the official outline:

**Heavy:** [domains likely to anchor the exam — 40-50% of study time]
**Moderate:** [supporting domains — 30-40%]
**Sanity check:** [domains covered but historically under-represented — 10-20%, just in case]

## [UNCERTAIN — framing]

This forecast is derived from [N] past mock exams. Item banks rotate. Topics emphasized in these mock sets can be de-emphasized on the real exam. Treat this as a weighting heuristic for study time, not a prediction. The exam will include surprises.
```

### Step 5: Output location

Write to `~/tasks/study/exam-forecasts/[exam]/forecast-[YYYY-MM-DD].md`. Versioned — if you get another mock exam mid-prep, re-run and append.

## Integration

- Feed forecast weights into study-plan subject priorities and flashcards `--generate` topic selection.

## What this skill does not do

- **Predict specific questions.** Past mock exams show patterns; they don't show you tomorrow's item.
- **Work without past mock exams.** If you don't have prior mock exams, the skill can't forecast — it falls back to "here's what the outline covers, study that."
- **Replace studying the full outline.** Forecast is weighting, not elimination. Skipping a domain because it's historically under-represented is how learners get burned.
- **Account for bank rotation you don't know about.** If the item bank shifted this year, the skill doesn't see that unless the mock sets reflect it.
- **Work reliably with 1-2 past mock exams.** Thin sample. Flag as such.
