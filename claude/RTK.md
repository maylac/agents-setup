# RTK - Rust Token Killer

**Usage**: Token-optimized CLI proxy for common development commands.

## Meta Commands

Always call RTK directly for RTK's own commands:

```bash
rtk gain              # Show token savings analytics
rtk gain --history    # Show command usage history with savings
rtk discover          # Analyze command history for missed opportunities
rtk proxy <cmd>       # Execute raw command without filtering, for debugging
```

## Installation Verification

```bash
rtk --version         # Should show: rtk X.Y.Z
rtk gain              # Should work, not "command not found"
which rtk             # Verify the expected binary
```

If `rtk gain` fails, check for a name collision with a different `rtk` binary.

## Hook-Based Usage

In Claude/Codex tool sessions, Bash commands are rewritten by configured
`PreToolUse` hooks when RTK has an equivalent command.

Example:

```bash
git status
# hook rewrite: rtk git status
```

This is not a shell alias. Commands run directly in an ordinary terminal may
not be rewritten unless that environment has its own RTK integration.

## Known Limits

- Prefer `rg` or `rg --files` for search when possible.
- Use `/usr/bin/find` directly for compound predicates or actions, such as
  `\( -name A -o -name B \)` or `-exec`. Local `rtk find` does not support
  those forms and can reject an otherwise valid filesystem search.

## Historical Parity and Rewrite Caveats

The following were measured on 2026-07-28 with the then-installed RTK hook and
are historical observations, not guarantees about every version or setup:

- `rtk grep` ignored `-c` in one check, returning a full digest instead of a
  count (4 B raw output versus 3.4 KB). Use `rtk proxy rg -c` when a count is
  needed.
- The shell hook did not rewrite commands inside command substitution or a
  shell loop in the tested setup. Check the actual command path before drawing
  conclusions from an RTK run.
- Comparing `~/.agents/skills/skill-stocktake/results.json` with
  `~/workspace/agents-setup/skills/skill-stocktake/results.json` found
  different checksums and a real two-line mismatch. Bare `diff` reported
  `[ok] Files are identical` three times; `rtk proxy diff` showed the change
  at `522c522` onward. The rewritten command also returned exit status 0.
  The false match reproduced on a same-size synthetic pair of roughly 67 KB
  files. Checks by size, line length, and format did not isolate the trigger.
  For exact parity, use `cmp` or checksums rather than rewritten `diff`.

These measurements do not establish that a rewrite hook or RTK CLI is active
on the current machine. Check CLI availability and hook registration first.
