---
name: video-script-builder
description: Create publish-ready video scripts, hooks, storyboards, voiceovers, captions, shot lists, and CTAs. Not for topic discovery (use video-topic-scout), rendering videos (use hyperframes-video-producer), or channel packaging (use video-channel-publisher).
---

# Video Script Builder

## Workflow

1. **Lock the brief**
   - Topic, viewer, promise, runtime, channel, tone, proof, CTA, and any forbidden claims.
2. **Choose the format**
   - Read `references/script-formats.md` when deciding between short, explainer, tutorial, case study, or portfolio demo.
3. **Write the script pack**
   - Hook in the first 1-3 seconds.
   - One clear promise.
   - Fast context, then proof or demonstration.
   - On-screen text that supports the voiceover rather than duplicating every word.
   - For Japanese long-form explainer or tutorial narration, read `../cognitive-rhythm-writing/SKILL.md` and apply its tension management（未回収の緊張）and beat design to the voiceover; short-form and non-Japanese scripts skip this.
4. **Create production notes**
   - Visual beats, asset needs, HeyGen avatar directions, HyperFrames motion ideas, caption style, and thumbnail/title hooks.
5. **Self-edit**
   - Remove throat-clearing.
   - Replace abstractions with concrete nouns and actions.
   - Ensure every beat earns its seconds.

## Output

```markdown
# Script Pack

## Brief
- Audience:
- Promise:
- Runtime:
- Channel:
- CTA:

## Hook Options
1.
2.
3.

## Voiceover
[timecode] narration

## On-Screen Text
[timecode] text

## Storyboard
| Time | Visual | Narration | Text | Assets |
| --- | --- | --- | --- | --- |

## Production Notes

## Title/Caption Seeds
```

## Rules

- For HeyGen avatar narration, write speakable lines with natural pauses.
- For short-form video, keep sentences short and avoid long subordinate clauses.
- For portfolio videos, show the workflow and outcome, not just the claim.
- Keep platform-specific metadata draftable but leave final publishing to `$video-channel-publisher`.
