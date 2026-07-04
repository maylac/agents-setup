---
name: video-growth-pipeline
description: Orchestrate end-to-end video growth workflows across topic, script, production, and publishing. Not for a single narrow step; use video-topic-scout, video-script-builder, hyperframes-video-producer, or video-channel-publisher directly.
---

# Video Growth Pipeline

## Workflow

Use this skill as the orchestrator. Delegate the detailed work to the specialized skills when the user asks for an end-to-end video workflow.

1. **Define the brief**
   - Audience, offer, goal, language, format, constraints, and publishing risk.
   - If the user gives no niche, infer one from context and state the assumption.
2. **Explore topics**
   - Use `$video-topic-scout` to gather and score topic candidates.
   - Browse current sources when trend freshness matters.
3. **Choose the concept**
   - Present 3-5 ranked concepts with angle, target viewer, proof source, and reason to believe.
   - Recommend one concept unless the user explicitly wants options only.
4. **Write the script**
   - Use `$video-script-builder` to produce hook, narrative beats, voiceover, on-screen text, shot list, and CTA.
5. **Produce the video**
   - Use `$hyperframes-video-producer` for HTML/HyperFrames motion video work.
   - Treat HeyGen avatar or voice assets as replaceable layers unless the user asks to call the HeyGen API.
6. **Select channels and package**
   - Use `$video-channel-publisher` to choose the right channel mix and prepare metadata, thumbnails, captions, and approval checklist.
7. **Publish safely**
   - Do not post to external services unless the user explicitly approves the exact channel, copy, account, and timing.
   - If posting is not approved, prepare a publish-ready package.

## Output Contract

Keep artifacts easy to hand off between steps:

- `topic_brief`: target audience, topic, angle, evidence, promise, risk.
- `script_pack`: runtime, voiceover, on-screen text, storyboard, CTA.
- `production_pack`: project path, composition path, assets, render command, output file.
- `publishing_pack`: selected channels, adapted copy, metadata, thumbnail notes, checklist.

For a complete schema, read `references/workflow-contract.md`.

## Decision Rules

- Favor repeatable formats over one-off video ideas.
- Prefer a sharp niche and concrete outcome over a broad AI-news recap.
- Keep a human approval gate before any external publication.
- Verify every created video with lint/render checks before calling it ready.
