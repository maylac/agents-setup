---
name: twitter-archive-analysis
description: Analyze the local Twitter/X archive in $HOME/Archives/twitter-export for posting tendencies, risk screening, public link checks, personality-style summaries, topic history, or representative tweet examples. Use when the user asks about their tweets, Twitter archive, X archive, flame risk, deleted/public tweet status, or archive-grounded self-analysis.
---

# Twitter Archive Analysis

## Source Order

Start in `$HOME/Archives/twitter-export`. Prefer local archive evidence before public web checks.

Likely files include:

- `data/tweets.js`
- `data/tweets-part1.js`
- `data/deleted-tweets.js`

Discover current files with `rg --files data` before assuming names. Archive JavaScript files usually contain JSON-like arrays after an assignment prefix; parse them structurally instead of grepping isolated text when counts or dates matter.

## Analysis Procedure

1. Identify the user's requested lens: risk, personality-style tendencies, topic history, representative examples, or public liveness.
2. Build a date-aware sample. Compare the full archive with recent slices such as 2020+, 2023+, and 2025+ because early high-volume years can skew all-time counts.
3. Normalize tweet IDs, timestamps, text, URLs, reply/retweet markers, and deletion/public-status fields if present.
4. Use counts to find patterns, then inspect representative tweets manually before drawing conclusions.
5. When giving examples, include direct links as `https://x.com/i/web/status/<tweet_id>` when relevant.
6. For public liveness or deletion checks, use the local archive for discovery, then confirm important current status with the public source only for the selected IDs.

## Output Rules

- Default to Japanese when the user asks in Japanese or asks for self-analysis.
- Frame personality-style conclusions as posting tendencies, not diagnosis.
- Separate archive-grounded facts from interpretation.
- Mention date ranges and sample sizes used.
- Avoid over-weighting 2013-2015 all-time volume when the user asks about current tendencies.
- For risk screening, prioritize concrete resurfacing risk: identifiable targets, strong negative wording, sensitive topics, and whether the tweet appears publicly reachable.

## Verification Checklist

- Current archive file names were discovered, not assumed.
- Counts and date ranges were computed from parsed archive data.
- Representative examples were read in context.
- Any public availability claim was checked against the relevant public source when possible.
