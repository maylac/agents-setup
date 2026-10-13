# slack-bridge

Mac mini daemon for the `Autonomous Operation: Slack → Dots → Mac mini` flow in `home/AGENTS.md`.
It polls one Slack channel, accepts task contracts only from allowlisted senders, runs `claude -p` (permission mode `auto`) or `agy --print` (`accept-edits`) in a fresh git worktree of an allowlisted repo, and replies in the thread. It never bypasses agent permissions. Python 3 stdlib only.

## Contract

```
agent: claude
repo: /Users/gotasasaki/workspace/maylac/some-repo
model: claude-opus-5-5   # optional; agy defaults to Gemini 3.5 Flash (Low)

Goal, owned files, acceptance criteria as runnable checks, time budget.
```

## Setup (one-time, user-owned: Slack app and tokens are Hard Stops)

1. Create a Slack app with a bot token (`xoxb-…`) and scopes `channels:history`, `chat:write` (add `groups:history` for a private channel). Invite it to a dedicated channel such as `#agent-tasks`, and let Dots post there.
2. Write `~/.config/slack-bridge/env` (chmod 600):

   ```
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   BRIDGE_ALLOWED_SENDERS=U_YOUR_ID,B_DOTS_BOT_ID
   BRIDGE_ALLOWED_REPOS=/Users/gotasasaki/workspace/maylac/repo-a,/Users/gotasasaki/workspace/maylac/repo-b
   ```

   Optional: `BRIDGE_POLL_SECONDS` (20), `BRIDGE_TASK_TIMEOUT_SECONDS` (3600), `BRIDGE_CLAUDE_PERMISSION_MODE` (auto), `BRIDGE_AGY_DEFAULT_MODEL`.
3. Install: `mkdir -p ~/.local/state/slack-bridge && sed "s#\$HOME#$HOME#g" launchd/com.maylac.slack-bridge.plist.template > ~/Library/LaunchAgents/com.maylac.slack-bridge.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.maylac.slack-bridge.plist`

### GitHub transport (no Slack token needed)

If Dots is connected to Slack and GitHub but you do not want a separate Slack bot, set `BRIDGE_TRANSPORT=github`. Dots opens an issue labelled `agent-task` whose body is the contract; the bridge (using the existing `gh` login) removes the label, comments progress and results, and closes the issue; Dots relays the result to Slack.

```
BRIDGE_TRANSPORT=github
BRIDGE_GITHUB_REPO=maylac/agent-tasks
BRIDGE_ALLOWED_SENDERS=maylac
BRIDGE_ALLOWED_REPOS=/Users/gotasasaki/workspace/maylac/repo-a
```

Missing config makes the daemon exit (fail closed). The first run records "now" and never executes older channel history. Logs: `~/.local/state/slack-bridge/err.log`.

## Test

`python3 -m unittest slack-bridge/test_bridge.py` (or `tests/slack-bridge.test.sh`).
