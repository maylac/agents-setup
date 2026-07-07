---
name: study-plan
description: >
  Build or update a long-term certification/exam prep study plan (PMP, AWS, etc.)
  — phases, subjects weighted by weakness, daily session schedule, adaptive to
  session history in study-plan.yaml. Use when the user says "build a study plan",
  "schedule my studying", or "how should I study for [X]".
argument-hint: "[--build | --update | --status | --cram]"
---

# /study-plan

1. Load `~/tasks/study/profile.md` if it exists → target exam, exam date, weak areas, target study hours/day, prep course.
2. Load `~/tasks/study/study-plan.yaml` if it exists.
3. Apply the framework below.
4. Route by flag:
   - `--build` (default if no plan exists): walk the inputs gate (exam, subjects, hours/week, days off, methods). Build the phase structure + daily schedule for the first two weeks. Write `study-plan.yaml`.
   - `--update` (default if plan exists): re-read `session_history`, adjust subject priorities and weekly_hours, fill in the next stretch of daily schedule.
   - `--status`: what's scheduled today / this week, score trend, subjects slipping, next scheduled session per subject.
   - `--cram`: force cram mode — highest-weight exam domains first, daily practice-question volume, taper last 2-3 days.
5. Before writing: summarize the plan in prose and confirm with the user. Adjust based on their answer.
6. Always sanity-check hours/week against the user's stated life constraints. Over-ambitious plans fail.

---

## Purpose

Sitting down to study and not knowing what to study is how weeks disappear. This skill builds a plan — weeks to exam, sessions per day, subjects per week, session types — and then adapts as the user actually does the sessions. It is a living plan, not a calendar export.

It also gives downstream skills (flashcards, pmi-studyhall-export, exam-forecast) a shared schedule to honor, so the user isn't asked "what do you want to study today" every time they open a session.

## Confidence discipline

A plan is opinion, not doctrine. The skill states clearly what's an estimate:

- **Time-per-topic estimates** are general guidance (based on typical prep-course weightings). Flag them as estimates — the user's real pace will differ.
- **Subject weightings** are derived from the user's own reported weak areas and session history. Confident.
- **High-yield-domain prioritization in cram mode** is based on the exam's published domain weightings and past practice-exam patterns. Flag any "this is definitely on the exam" claim as `[UNCERTAIN — past frequency is not a prediction]`.

## Load context

`~/tasks/study/profile.md`:
- Target exam, exam format, exam date
- Weak domains/areas
- Prep course (Udemy course, PMI Study Hall, self-study, etc.)
- Target study hours/day

`~/tasks/study/study-plan.yaml` if it exists — extend, don't overwrite.

## Workflow

### Step 1: What are we planning for

> What are we building a plan for?
>
> 1. **A certification exam** (PMP, AWS, etc. — you have a target date in mind)
> 2. **A work deadline-driven learning goal** (ramp on a topic/tool by a date)
> 3. **General learning cadence** (steady progress across a course or topic set)

For (1) certification: read exam date from profile, confirm. If no date captured, ask.
For (2) work deadline: ask the topic, the date, and what "done" looks like.
For (3) cadence: ask for an anchor date (course end, quarter end) to pace against.

### Step 2: Inputs — one at a time, wait for each

**Ask and wait.** Do not bulk all questions into one prompt and move on.

- **Exam/target date:** confirmed?
- **Subjects to cover:** read the exam content outline (e.g., PMI ECO domains, AWS exam guide) or ask. Confirm with the user — "any domain I should add or drop?"
- **Strongest areas:** least priority. Still reviewed, not drilled heavily.
- **Weakest areas:** most priority. Get more sessions.
- **Hours per week available:** realistic, not aspirational. "I can do 20 hours" is different from "I will do 20 hours for 8 weeks." Ask what they can actually sustain.
- **Life-context sanity check — force it.** After the user gives a number, ask (one question at a time — do not skip):

  > You said [N] hours per week. Before I build this, tell me what else is in your week — job (hours/week), family (kids, caregiving), commute, workout, anything meaningful. The plan should fit your life, not the other way around. A plan you can't follow is worse than a lighter plan you can.

  Wait for the answer. Then sanity-check the stated hours against their reported load:

  > That's ~[X] hours/day across [N] study days, on top of [job + family + commute + other]. In my experience that's [realistic / tight / unsustainable]. Want to adjust the hours/week target before I build, or keep them and see how week 1 goes?

  Do not skip this step even if profile's target hours number was already captured. The profile captures what the user said; the life-context check captures whether it's sustainable. If the check produces a lower number, use the lower number for the plan and note the adjustment in the `confidence_flags` block.

  If the user declines to share life context ("just build it"), respect that — but add a `confidence_flags` entry: "Life-context check declined; plan assumes [N] hours/week is sustainable. Revisit at end of week 2 if adherence is below [X]%."
- **Preferred study methods:** multi-select. Practice questions / mock exams / flashcards / notes / re-reading / hands-on labs. Weight the schedule toward the methods they say they'll actually do.
- **Days off per week:** rest days matter. Plans that schedule 7/7 days fail in week 3.

### Step 2.5: Supplement vs. replace (prep-course users)

If profile → `Prep course` is a structured prep course (a Udemy course sequence, a PMI Study Hall study plan, or any other day-by-day curriculum — i.e., NOT `self` or `N/A`), the user already has a prep-course sequence. This skill's plan must choose one of two roles — it cannot run a full parallel curriculum alongside the prep course without burning the user out.

Ask, one question, wait:

> Your profile says you're on [prep course]. It already sequences the material. Two ways this plan can work — pick one:
>
> 1. **Supplement.** The prep course is your primary curriculum. This plan fills gaps: extra practice-question drilling on your weak domains, targeted mock exams, flashcard loops on the topics you're missing. I won't rebuild the prep-course sequence; I'll layer on top of it.
> 2. **Replace.** You're not following the prep-course sequence (maybe its pacing doesn't work for your life). I'll build the whole plan — subjects, hours, phases, schedule — and you drop the prep-course sequence.
>
> Don't pick both. Running two full curricula against each other is how learners blow up in week 4.

Wait for the answer. Record it in the yaml as `prep_course_mode: supplement | replace`.

If **supplement**: the plan's daily schedule is lighter — it only adds weak-domain drilling and targeted practice, does not duplicate prep-course coverage. Flag in `confidence_flags`: "Supplement mode — this plan assumes you're on track with [prep course] for primary coverage. If you fall behind, tell me and we'll re-plan."

If **replace**: build the full plan as specified below.

If the prep course is `self` or `N/A`, skip this step — there's nothing to supplement.

### Step 3: Build the schedule

Calculate weeks-to-exam from today's date. Then:

**Normal mode (4+ weeks out):**
- Split weeks into phases:
  - **Learning phase** (first ~60% of time): one domain per ~3-5 days, mixing reading/notes with flashcards and a few practice questions on fresh material.
  - **Drilling phase** (next ~30%): more practice-question volume, more mock exams, simulated conditions, all domains in rotation.
  - **Review phase** (last ~10%): focused on weakest subtopics from session_history, full mock exams, light review of strong areas.
- Weight domains by weakness: weak domains get ~2x the hours of strong domains.
- Schedule day-by-day: which domain, which method, how long. Leave slack for the user's actual life.

**Cram mode (< 4 weeks out):**
- Flag it: "You're less than four weeks out. This is cram mode — the plan prioritizes high-yield domains over full coverage. You will leave gaps. That's the tradeoff at this point."
- Prioritize by the exam's highest-weight domains (from the published domain weightings). Narrower topics get minimum viable coverage.
- Daily schedule: practice-question blocks every day (volume matters now), mock exam every other day, one full simulated exam per week.
- Sleep and taper the last 2-3 days. Do not schedule hard drilling the day before the exam. This is real — people who cram through the night before score worse.

### Step 4: Write it

Write to `~/tasks/study/study-plan.yaml`:

```yaml
plan_type: certification  # or work-deadline or cadence
exam_date: 2026-09-15
exam: PMP
exam_format: domain-weighted
created: 2026-05-08
last_updated: 2026-05-08
weeks_to_exam: 12
hours_per_week: 25
days_per_week: 6
mode: normal  # or cram
phases:
  - name: learning
    start: 2026-05-08
    end: 2026-06-20
    focus: reading, flashcards, introductory practice questions
  - name: drilling
    start: 2026-06-21
    end: 2026-07-18
    focus: practice-question volume, mock exams, simulated conditions
  - name: review
    start: 2026-07-19
    end: 2026-07-27
    focus: weak-subtopic review, full mock exams
subjects:
  people:
    priority: high  # weak
    weekly_hours: 5
    methods: [practice-questions, flashcards, mock-exam]
  process:
    priority: medium
    weekly_hours: 3
    methods: [practice-questions, notes-review]
  # etc.
schedule:
  - date: 2026-05-08
    day: Thursday
    sessions:
      - subject: People
        method: notes-review
        duration_min: 90
      - subject: People
        method: practice-questions
        duration_min: 60
        n_questions: 25
  - date: 2026-05-09
    day: Friday
    sessions:
      - subject: Process
        method: flashcards
        duration_min: 45
      - subject: Process
        method: mock-exam
        duration_min: 60
  # etc.
session_history: []  # appended by flashcards, pmi-studyhall-export as sessions complete
```

### Step 5: Confirm with the user

Summarize the plan in prose (not raw YAML) before saving:

> Here's what I built. [X] weeks to the [exam]. [Y] hours/week across [Z] days. Weak domains (People, Process) get 2x the hours. Three phases: learning through [date], drilling through [date], review the last [N] days. I've scheduled the first two weeks day-by-day. Beyond that it's allocated by week — I'll fill in the daily schedule as you complete sessions, so the plan adapts to where you actually are.
>
> Does this feel right? Too ambitious? Too light? Missing a domain?

Adjust based on the answer. Then write.

## Adapting the plan

After each session (via flashcards, pmi-studyhall-export), the corresponding skill appends to `session_history`:

```yaml
session_history:
  - date: 2026-05-08
    subject: People
    type: mock-exam
    n_questions: 10
    score: 6
    weak_subtopics: [conflict-management, team-development]
```

On the next `--update` run (or when the plan is detected stale):
- Domains with consistently low scores get promoted in `priority` and `weekly_hours`.
- Weak subtopics within a domain get flagged for the next scheduled session on that domain.
- If the user is falling behind (scheduled sessions not appearing in history), adjust: either compress coverage or note the gap and ask.
- If the user is ahead, open up time for deeper weak-domain drilling.

## Modes

`--build` (default) — fresh plan
`--update` — re-read session_history and adjust weightings, fill in upcoming daily schedule
`--status` — what's on deck today / this week, what's the score trend, what's slipping
`--cram` — force cram mode even if more than 4 weeks out (user override)

## Integration

- `flashcards --session <n>` results append to session_history.
- `pmi-studyhall-export` results append to session_history and feed weak-subtopic priorities.
- `exam-forecast` weights can feed the subject priorities here.

## What this skill does not do

- **Guarantee you pass.** The plan is a scaffold. The work is on you.
- **Predict the exam.** Cram mode uses published domain weightings and historical frequency; high-yield ≠ guaranteed-tested.
- **Replace your prep course schedule.** If you're on a structured course, this plan can supplement — don't run two full curricula against each other. Use one as primary.
- **Schedule your life.** Hours available is what you tell me. If you overstate, the plan will break in week 2. Be honest.
