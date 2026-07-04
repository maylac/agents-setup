---
name: video-topic-scout
description: Discover, research, score, and rank high-potential video topics. Not for scripts/storyboards (use video-script-builder), video production (use hyperframes-video-producer), or publishing packages (use video-channel-publisher).
---

# Video Topic Scout

## Workflow

1. **Clarify the target**
   - Audience, business goal, niche, language, desired channel, and format.
   - If missing, infer a practical default and label it as an assumption.
2. **Gather signals**
   - Use current web/platform research when trend recency matters.
   - Look for repeated pain points, contrarian claims, new tools, public data, product launches, community questions, and creator formats already getting traction.
3. **Generate candidates**
   - Produce 10-20 raw topics.
   - Convert each into a specific angle, not a category.
4. **Score candidates**
   - Use the rubric in `references/scoring-rubric.md`.
   - Reject ideas that are vague, unverifiable, too generic, or require unsafe claims.
5. **Recommend concepts**
   - Return 3-5 ranked concepts with hook, target viewer, evidence, difficulty, and best channel.

## Output

Use this shape:

```markdown
## Ranked Topics

| Rank | Topic | Angle | Audience | Score | Best Channel | Why It Can Hit |
| --- | --- | --- | --- | --- | --- | --- |

## Recommended Pick

Topic:
Hook:
Promise:
Evidence:
Risk:
Next script direction:
```

## Search Guidance

- Search recent sources when the request includes "latest", "trend", "hit", "伸びる", "バズる", "今", or platform-specific strategy.
- Prefer primary/platform-visible evidence over vibes: official announcements, search results, channel pages, creator posts, comment patterns, forum questions, and product docs.
- Cite links when using web research.
- Do not invent metrics; say "signal" when exact view counts or engagement are not verified.
