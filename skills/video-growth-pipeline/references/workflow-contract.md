# Workflow Contract

Use these lightweight artifact shapes when passing work between video skills.

## topic_brief

```yaml
topic: ""
angle: ""
target_viewer: ""
viewer_pain: ""
promise: ""
evidence:
  - source: ""
    signal: ""
why_now: ""
format_fit: "short|long|thread|carousel|webinar"
risk_notes: []
```

## script_pack

```yaml
runtime_seconds: 45
format: "short|long"
hook: ""
voiceover:
  # `speaker` is optional: "host" | "guest". Omit for solo scripts (defaults to host).
  # Dialogue/podcast scripts alternate speakers; the voice orchestrator maps speaker -> voice model.
  - { time: "0-3s", speaker: "host", text: "" }
on_screen_text: []
storyboard:
  - time: "0-3s"
    visual: ""
    narration: ""
    text: ""
cta: ""
asset_needs: []
```

## voice_pack

Produced by the voice orchestrator (local Style-Bert-VITS2). Sits between `script_pack` and
`production_pack`; consumed by both the video track (as the narration asset layer) and the
audio-first podcast track. Local generation is free, so `segments[]` are cached by `cache_key`.

```yaml
voice_pack:
  script_pack_ref: ""
  profile: "solo"            # solo = user voice only; dialogue = user + a second local speaker
  engine: "style-bert-vits2"
  voices:
    host:  { provider: "style-bert-vits2", model_id: "", style: "Neutral", role: "user" }
    guest: { provider: "style-bert-vits2", model_id: "", style: "Neutral", role: "co-host" }  # dialogue only
  segments:                  # 1:1 with script_pack.voiceover[]
    - id: "vo-0"
      speaker: "host"
      time: "0-3s"
      text: ""
      audio: ""             # path to the rendered segment wav/mp3
      duration_s: 0
      status: "ok"          # ok | cached | error
  full_mix: ""              # concatenated narration file (feeds HeyGen intro + podcast master)
  cache_key: ""             # sha256(model_id + style + normalized_text) per segment
```

## avatar_pack

Produced by the HeyGen orchestrator. Track A (vertical shorts) only, and in the hybrid layout
only the **intro** segment of `full_mix` drives the avatar; the body is faceless slides. Async:
submit returns a job id, collect downloads the clip. Fails open to a still/motion intro.

```yaml
avatar_pack:
  voice_pack_ref: ""
  mode: "audio_driven"       # feed our full_mix as the driving audio; voice stays the user's clone
  segment: "intro"           # "intro" (hybrid) | "full"
  audio_span_s: [0, 6]       # which slice of full_mix drives the avatar
  avatar_id: ""
  aspect: "9:16"
  provider_job_id: ""
  status: "queued"           # queued | processing | completed | failed
  clip: ""                   # downloaded mp4 path; empty when status=failed (fail open to still image)
  fallback: "still"          # still | motion — used when status=failed
  duration_s: 0
  polled_at: ""
```

## production_pack

```yaml
project_path: ""
composition_path: ""
asset_paths:            # for the hybrid short, populated from the two packs above
  - { role: "avatar",    path: "" }   # from avatar_pack.clip (intro only)
  - { role: "narration", path: "" }   # from voice_pack.full_mix (whole video)
  - { role: "captions",  path: "" }   # per-segment timings for burned-in captions
  - { role: "bgm",       path: "" }
preview_command: ""
render_command: ""
render_output: ""
verification:
  lint: ""
  render: ""
  visual_check: ""
```

## publishing_pack

```yaml
primary_channel: ""
secondary_channels: []
title_options: []
description: ""
hashtags: []
thumbnail_brief: ""
caption_file: ""
approval_required: true
scheduled_time: ""
```
