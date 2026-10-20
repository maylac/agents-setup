# slack-bridge

Mac mini daemon for the `Autonomous Operation: Slack → Dots → Mac mini` flow in `home/AGENTS.md`.
It polls one Slack channel, accepts task contracts only from allowlisted senders, runs `claude -p` (permission mode `auto`), `codex exec` (`--sandbox workspace-write`) or `agy --print` (`accept-edits`) in a fresh git worktree of an allowlisted repo, and replies in the thread. It never bypasses agent permissions. Python 3 stdlib only.

## Contract

```
agent: claude            # or codex / agy / grok (grok needs BRIDGE_GROK_ENABLED=1)
repo: $HOME/workspace/maylac/some-repo
model: claude-opus-5-5   # optional; codex e.g. gpt-6-luna; agy defaults to Gemini 3.5 Flash (Low)

Goal, owned files, acceptance criteria as runnable checks, time budget.
```

## Setup (one-time, user-owned: Slack app and tokens are Hard Stops)

1. Create a Slack app with a bot token (`xoxb-…`) and scopes `channels:history`, `chat:write` (add `groups:history` for a private channel). Invite it to a dedicated channel such as `#agent-tasks`, and let Dots post there.
2. Write `~/.config/slack-bridge/env` (chmod 600):

   ```
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   BRIDGE_ALLOWED_SENDERS=U_YOUR_ID,B_DOTS_BOT_ID
   BRIDGE_ALLOWED_REPOS=$HOME/workspace/maylac/repo-a,$HOME/workspace/maylac/repo-b
   ```

   Optional: `BRIDGE_POLL_SECONDS` (20), `BRIDGE_TASK_TIMEOUT_SECONDS` (3600), `BRIDGE_CLAUDE_PERMISSION_MODE` (auto), `BRIDGE_AGY_DEFAULT_MODEL`, `BRIDGE_CODEX_BIN` (default `codex`; on this Mac the ChatGPT-bundled CLI is `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`, so either point `~/.local/bin/codex` at it or set this), `BRIDGE_APPROVAL_LABEL` (`needs-approval`).

### Outcomes

- `done` / `failed (exit N)` / `failed (timeout Ns)`: the result comment includes the output tail and the branch; the issue is closed.
- `blocked (rate limit)`: a non-zero exit whose output mentions a 429, rate limit, usage limit or reset time. The matching line is quoted so the dispatcher can relay the reset time and re-file the task for another agent (for example `agent: codex`).
- `needs-approval`: the agent printed a line starting with `NEEDS-APPROVAL:` (a Hard Stop such as a force push or a deploy). The issue gets the `needs-approval` label and stays open; the dispatcher collects the approval and files a follow-up contract.
3. Install: `mkdir -p ~/.local/state/slack-bridge && sed "s#\$HOME#$HOME#g" launchd/com.maylac.slack-bridge.plist.template > ~/Library/LaunchAgents/com.maylac.slack-bridge.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.maylac.slack-bridge.plist`

### Shared harness and routing policy

`harness.py` + `routing.json` are the one place all three agents share:

- **Preamble.** Every task is prefixed with the same rules (AGENTS.md, Hard Stops, `NEEDS-APPROVAL:`, report format) and runs with `CROSS_HARNESS_PEER=1`, so no agent re-delegates.
- **Chains.** `chains[agent]` lists routes (`agent:model`) in order, e.g. `claude` → opus → sonnet → `codex:gpt-6-luna`. Edit `routing.json` to change policy; it is validated at startup.
- **When it falls back.** Only when a non-zero exit shows the route itself is unusable (rate/usage limit, auth, overloaded or missing model, missing binary). Ordinary task failures, timeouts and `NEEDS-APPROVAL` stop the run. Before the next route starts, the bridge's own worktree is reset to `HEAD`.
- **Cooldowns.** An unavailable route is skipped for `cooldown_seconds[kind]` (state: `cooldowns.json`). Reset times are not parsed; the quoted line is relayed instead.
- **Never silent.** The result comment has a `route:` line listing each hop. If every route is cooling down or dead the status is `blocked (no route)`.
- **Pinning.** A contract `model:` pins the run to that one route; `fallback: allow` re-enables the chain after it, `fallback: off` pins the default route.

- **Grok subscription (SuperGrok / X Premium+).** `grok` is a fourth agent (Grok Build CLI, `grok -p`, signed in with the subscription) and the last resort in every chain. It is off until `BRIDGE_GROK_ENABLED=1`. Verified against grok 1.0.62: `grok -p <task> --permission-mode acceptEdits [-m model]`; override the args with `BRIDGE_GROK_ARGS` (the bridge never adds a bypass flag such as `--always-approve`), and `BRIDGE_GROK_BIN` if it is not on PATH. Headless sign-in is `grok login --device-code` or `XAI_API_KEY`; a run that prints `Not signed in` is classified as an `auth` outage and falls through to the next route. The Grok Bot Dispatcher and Grok Build probably draw on one subscription, so Grok stays last to protect the Dispatcher's weekly allowance (unverified; if Grok Build reports a limit it is cooled down like any other route).

Env: `BRIDGE_ROUTING_FILE`, `BRIDGE_COOLDOWN_FILE`, `BRIDGE_GROK_ENABLED`, `BRIDGE_GROK_BIN`, `BRIDGE_GROK_ARGS`.

### GitHub transport (no Slack token needed)

If Dots is connected to Slack and GitHub but you do not want a separate Slack bot, set `BRIDGE_TRANSPORT=github`. Dots opens an issue labelled `agent-task` whose body is the contract; the bridge (using the existing `gh` login) removes the label, comments progress and results, and closes the issue; Dots relays the result to Slack.

```
BRIDGE_TRANSPORT=github
BRIDGE_GITHUB_REPO=maylac/agent-tasks
BRIDGE_ALLOWED_SENDERS=maylac
BRIDGE_ALLOWED_REPOS=$HOME/workspace/maylac/repo-a
```

Missing config makes the daemon exit (fail closed). The first run records "now" and never executes older channel history. Logs: `~/.local/state/slack-bridge/err.log`.

## Test

`python3 -m unittest slack-bridge/test_bridge.py` (or `tests/slack-bridge.test.sh`).
