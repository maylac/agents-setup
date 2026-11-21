# Attended operations lane

After applying the standard [permission rules](restore.md), use the ops session for one maintenance action at a time, such as updating settings or a plist, replacing an idle service, or merging a reviewed pull request. Require a separate, one-shot phone approval for each operational tool request. Administrator policy can change how local rules apply. Verify both a denied request and an approved request before using the lane. See the [Claude Code permissions reference](https://code.claude.com/docs/en/permissions).

## Validate before maintenance

Preflight with a runtime profile that combines the restrictive permissions rules and `sandbox.enabled: true`. For the project-local copy-absent check, use a throwaway test fixture; do not remove protections from the real project. The project-local `settings.local.json` companion is permissions-only and has no sandbox key. Do not execute a profile with the sandbox disabled during preflight. The final scoped CLI profile combines both reviewed public JSON fragments: [sandbox settings fragment](../templates/claude-remote-control-ops.settings.json) and [restrictive permissions fragment](../templates/claude-remote-control-ops.approvals.json).

If the ops directory has no trust entry, the operator can open an authenticated terminal on their phone and confirm that directory in Claude Code’s native trust prompt. Keep all maintenance requests in this attended ops lane, with no command chaining, delegation, or background work. See the [Claude Code Remote Control guide](https://code.claude.com/docs/en/remote-control).

## Future setup after authorization

Only after the operator authorizes setup, prepare these three installed files:

1. `~/.claude/remote-control/ops-settings.json`, combining both reviewed public JSON fragments linked above. Never install or run either fragment alone.
2. `$HOME/workspace/ops/.claude/settings.local.json`, containing the permissions-only companion fragment linked above, with no sandbox key.
3. `~/Library/LaunchAgents/local.claude.remote-control-ops.plist`, rendered from the [reviewed launchd template](../launchd/local.claude.remote-control-ops.plist.template). Its `WorkingDirectory` is fixed at `$HOME/workspace/ops`.

Validate the files and confirm the dedicated label is idle before registering or starting only `local.claude.remote-control-ops`. Keep its startup disabled until then. See the [Claude Code Remote Control guide](https://code.claude.com/docs/en/remote-control).

## Check each approval

In the attended ops lane, request the generic read-only status check `launchctl print gui/<uid>/<selected-label>`. Reject the first request and confirm it stops. Request it again, approve it once on the phone, and confirm it returns status.

In an ordinary session, test only `gh pr merge --help`, separately from maintenance. Reject the first request and confirm it stops. Request it again, approve it once, and confirm the help text appears only after approval. Do not merge a pull request as part of this check.

## Roll back only this setup

When removing this setup, remove only files created for this lane and its idle `local.claude.remote-control-ops` label. Preserve unrelated sessions and project trust entries. Do not stop or remove another service.
