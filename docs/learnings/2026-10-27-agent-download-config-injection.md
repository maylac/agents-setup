# Downloads instruction injection needs a sandbox as well as hooks

- Date: 2026-10-27
- Area: agents-setup / Claude and Codex
- Type: design-tradeoff

## Problem

A downloaded instruction file can persuade an agent to persist an MCP command in user config or redirect an API endpoint in project settings. Legitimate instruction files and shared symlinks must keep working.

## Rejected approaches

- A warning in AGENTS.md alone is model guidance, not an execution boundary.
- A filename watcher has a race between delivery and instruction discovery, and should not silently delete downloaded data.
- A PreToolUse filename check alone can be bypassed with shell commands, MCP tools or other file tools.
- SessionStart and InstructionsLoaded hooks cannot block Claude execution; use UserPromptSubmit to block the prompt and PreToolUse to deny tools.

## Working approach

Keep shared instruction symlinks intact, block Claude prompts/tools from download-style roots, inspect reported live settings changes, and enable the OS shell sandbox with no unsandboxed fallback. Codex uses workspace-write, on-request approvals, no command network, no shared temporary write roots, and untrusted download roots. Preserve these settings in backup templates as well as live files.

## Why it works and evidence

The prompt guard stops Claude before inference in Downloads: the native print-mode result reported UserPromptSubmit blocked with zero API time and zero turns. Both runtimes produced an actual PermissionError when a shell tried to create a harmless probe in the Codex config directory. Codex permitted a workspace write and denied a direct network connection. Fourteen guard regression tests and the backup sanitizer passed. Native Codex config/read and a fresh ephemeral thread returned the intended workspaceWrite policy. The broader sync audit still reports the pre-existing missing Claude RTK hook; its absence is present in the pre-change settings backup.

## General rules

Verify native runtime policy and real denied operations, rather than inferring protection from valid JSON. User-level defaults affect new sessions and can be overridden; hooks and MCP hosts remain outside shell sandboxes. Do not restart shared agent daemons merely to make a configuration change immediate.
