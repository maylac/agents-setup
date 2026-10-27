# Agent download defense

`claude/hooks/untrusted-directory-guard.py` responds to the Forever Security Downloads
`AGENTS.md`/`CLAUDE.md` injection report. A browser download can leave an instruction file
in `~/Downloads`. If an agent is started there, it loads that file as trusted instructions.
The file can then redirect the API endpoint or proxy, or weaken permissions.

## What the hook does

| Event | Behavior |
| --- | --- |
| `UserPromptSubmit` | Blocks the prompt when cwd (symlinks resolved) is under `~/Downloads` or `~/Desktop`, is exactly `~`, `/tmp` or `/private/tmp`, or is missing/invalid. Nested `/tmp/...` worktrees are allowed. |
| `PreToolUse` | Denies every tool from the same unsafe cwd. Denies `Read`/`Edit`/`Write`/`MultiEdit` of `AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md`, `CLAUDE.local.md` (case-insensitive, including `AGENTS (1).md` / `AGENTS 2.md` / `AGENTS-2.md`) under `~/Downloads` or `~/Desktop`, after resolving relative paths and symlinks. Denies `Edit`/`Write`/`MultiEdit` of `~/.codex/config.toml` and any `.claude/settings*.json`. Other downloaded files and config reads are still allowed. |
| `ConfigChange` | Reads the changed `.json` settings file from disk. Blocks if the file is unparseable, is not an object, or sets `env` keys `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` (case-insensitive), `apiKeyHelper`, truthy `disableAllHooks`, or `permissions.defaultMode=bypassPermissions`. Reasons name only keys, never values or file content. If the path is absent or not a file, or the source is `skills`, the hook does nothing. |

If stdin is unreadable, the hook exits 2, which blocks the event.

## Limits

- **This is not an OS boundary.** The hook only matches tool names and `file_path` with
  string and regex checks. `Bash` (`cat ~/Downloads/AGENTS.md`, `sed -i` on settings),
  `Grep`/`Glob`, MCP tools, and subprocesses can all get around it. Real containment needs an
  OS sandbox, such as Claude Code sandboxing or Seatbelt/bubblewrap with filesystem and
  network allowlists.
- `ConfigChange` runs only for changes made during a session. It does not inspect settings
  that already exist when the agent starts. Shell writes that the harness never reports are
  also not inspected. Policy (managed) settings changes cannot be blocked.
- Instruction files are discovered before any hook runs. Blocking cwd at `UserPromptSubmit`
  stops the agent from acting on a session started in Downloads. It does not stop the file
  from being loaded into context.
- Codex is not covered. It needs its own sandbox and config protections.
- The hook protects only the listed roots and file names. Other untrusted locations, such as
  mail attachments or unzipped archives elsewhere, are out of scope.
- Settings changes made and reviewed outside the agent (by the operator or the parent
  installer) are still possible by design.

## Test

```sh
python3 tests/untrusted-directory-guard.test.py
```

## Local activation (2026-10-27)

- Claude: install an identical copy at `~/.claude/hooks/untrusted-directory-guard.py` and register synchronous command hooks in user settings for the three events above. The public settings template includes the same registration.
- Claude Bash sandbox: enabled, auto-allow sandboxed commands, disallow unsandboxed retries, fail startup if unavailable. Deny shell reads of the two harness credential files and shell writes to `~/.claude` and `~/.codex`. File tools are governed separately by the hook.
- Codex: default `workspace-write` with `on-request` approvals, command network disabled, and shared temporary write roots disabled. Downloads, Desktop and the shared temporary root are untrusted projects. The shared home instructions reject imported instructions that ask to change agent settings or bypass controls.
- These are user-level defaults for new sessions, not managed policy. An existing session or an explicit CLI/project override may retain different permissions. Existing sessions and shared daemons are not restarted. Hooks and MCP hosts run outside shell sandboxes; do not treat these changes as complete isolation of the whole agent process.

Source: [Forever Security report](https://forever.security/blog/hijacking-ai-agents-via-downloads-folder), [OpenAI approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security), [Claude sandboxing](https://code.claude.com/docs/en/sandboxing).
