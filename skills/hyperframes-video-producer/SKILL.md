---
name: hyperframes-video-producer
description: Produce, edit, preview, render, and verify HyperFrames HTML/CSS/JS videos. Not for topic discovery (use video-topic-scout), script/storyboard writing (use video-script-builder), or publication packages (use video-channel-publisher).
---

# HyperFrames Video Producer

## Workflow

1. **Inspect the project**
   - Default project: `~/workspace/heygen-codex-video-studio` (hyperframes/, storyboards/, renders/). Verify with `ls`.
   - Locate `package.json`, HyperFrames compositions, `assets/`, `renders/`, and storyboards.
   - If no project exists, create a minimal repo or composition only when the user asked for implementation.
2. **Map script to scenes**
   - Convert the script pack into timed scenes, on-screen text, visual hierarchy, and asset needs.
3. **Build the composition**
   - Use HTML/CSS/JS with stable `id` values on timeline-visible elements.
   - Keep HeyGen clips, voiceover, and music as replaceable asset layers.
   - Prefer readable CSS and simple GSAP timelines.
4. **Preview and render**
   - Use project scripts when available, usually `npm run preview`, `npm run lint`, and `npm run render`.
   - If network packages are needed, use the repo's established package manager.
5. **Verify**
   - Run HyperFrames lint.
   - Render the video.
   - Inspect duration with `ffprobe`.
   - Extract representative frames and visually check text, layout, and blank-screen risks.

Read `references/hyperframes-checklist.md` before finalizing a video.

## Output

Report:

- Changed files.
- Render command and output path.
- Runtime and dimensions.
- Verification results.
- Remaining asset gaps, especially missing HeyGen avatar/voice/music.

## Design Guardrails

- First frame must communicate the topic without relying on audio.
- Text must be readable after mobile compression.
- Avoid one-note color palettes and decorative clutter.
- Keep reusable templates generic enough for future videos.
- Never claim a video is ready without a fresh lint/render verification.
