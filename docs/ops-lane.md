# Ops lane template

Use this Remote Control template for one operator-approved maintenance action at a time. Examples include updating a selected settings file or plist, replacing an idle service, and merging a reviewed pull request.

The public LaunchAgent template is [`launchd/local.claude.remote-control-ops.plist.template`](../launchd/local.claude.remote-control-ops.plist.template). Its arguments refer to a separately reviewed settings profile at `$HOME/.claude/remote-control/ops-settings.json`. Workspace trust and approval for each operation require separate checks.

## Review before use

Inspect the installed CLI options with `claude remote-control --help`. Lint the rendered plist with `plutil -lint <plist-path>`. The template has `RunAtLoad` set to false.

Use a read-only `launchctl print` request to check connectivity. After the reviewed rules put `gh pr merge` in `ask`, request `gh pr merge --help` in an interactive session. Reject the first request and verify that the command stops. Repeat it, approve on the phone, and verify that the help text appears only after approval.

## State and removal

The permission profile and service registration are pending. This repository supplies the inactive template and its verification procedure.

To remove a registered instance, first confirm that it has no active sessions. Then unload and remove only the `local.claude.remote-control-ops` label.
