# Upstream

- Repository: https://github.com/heydamir/unslop
- Commit: 1d13095e4bef6ad6c74f1dd828d84c4ba309a4dc
- License: CC-BY-4.0 (author: Damir Sokolovsky, @heydamir). Keep the credit lines in SKILL.md and references/.
- Installed: 2026-11-01
- Upstream files are byte-identical. Local additions: this provenance note and `.gitignore` for runtime dependencies.

## Local runtime

The ignored `node_modules` symlink points to `$HOME/.local/share/unslop-runtime/node_modules`.
That dedicated package pins Playwright 1.64.1 and ffmpeg-static 5.3.0; `$HOME/.local/bin/ffmpeg`
links to its FFmpeg executable. The scripts can use the existing Google Chrome installation.
Both page snapshots and story-video rendering were smoke-tested on 2026-11-01.
