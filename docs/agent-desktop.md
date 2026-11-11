# agent-desktop

`agent-desktop` is installed on the Mac as `agent-desktop@1.0.2` under the
user-owned `~/.local` npm prefix. The executable resolves from `~/.local/bin`.
The retained vendor skill is pinned to upstream commit
`9eb9b296192fcb70bda25e918cd6dd66abfa3d0d` in
[`skills/agent-desktop`](../skills/agent-desktop/).

## Use

Start with `agent-desktop status`, then load the guidance that ships with the
installed binary:

```sh
agent-desktop skills get desktop
agent-desktop skills get platform
```

The shared skill is linked into the installed agent homes. A new session can
discover it there; an already-running session may need to be restarted before
it sees the newly linked skill.

The current `.agents`, `.claude`, and `.codex` links point into the retained
task worktree. After merge, inspect their targets and update only links that
still point to `$HOME/workspace/desktop-cursor-team/repo/skills/agent-desktop`
so they point to `$HOME/workspace/maylac/agents-setup/skills/agent-desktop`.
The Gemini link resolves through `.agents` and follows that update.

## Local handling

- Treat snapshots, screenshots, clipboard data, window names, and command
  output as private desktop content. Keep raw captures outside the repository
  with owner-only permissions; share only the fields needed for verification.
- Use accessibility actions in headless mode. Do not use `--headed` or physical
  input unless the user explicitly permits that action.
- Retry an action only when its returned disposition says `retry: safe`. For
  other outcomes, inspect the live state before deciding what to do next.
- Check `permissions` before GUI work. If a required macOS permission is
  missing, stop and report the responsible app and required user action. Do
  not invoke `permissions --request` or `permissions --guide`.
- Do not use the tool to change user data, submit forms, send messages, or
  publish content unless the user has explicitly authorized that operation.

## Install and verify

The package was installed from a locally inspected npm tarball whose SHA-512
integrity matched npm metadata. For a future install, pin the version and use
the active user-local command prefix:

```sh
npm install --global --prefix "$HOME/.local" agent-desktop@1.0.2
agent-desktop version
```

The upstream skill file hashes are recorded in
[`skills/agent-desktop/SHA256SUMS`](../skills/agent-desktop/SHA256SUMS).
