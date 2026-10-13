---
name: oracle
description: Bundle selected files for an Oracle CLI second opinion when explicitly requested or a hard diagnosis needs an independent model.
origin: steipete/oracle
---

# Oracle file-backed consultation

Oracle sends a prompt and selected files to another model. Use it when the requested independent review benefits from that context. Follow the active harness's delegation preferences first; an older model named in a historical example is not necessarily stronger than the current coordinator.

## Verify the installed tool

Check `command -v oracle`, `oracle --version`, and `oracle --help` before constructing a run. This skill does not install Oracle, configure credentials, or establish available models. If the CLI is unavailable and Oracle itself was not required, use an available independent-review tool.

Select only a model and engine that the installed CLI supports. Historical versions could silently fall back for unknown model names; check the effective model in the preview or session metadata. Never substitute a different model silently when the user specified one.

## Prepare a bounded request

For repository diagnosis, include both a prompt and the relevant files. Give the question, acceptance criteria, prior attempts, and each file's role. Add related evidence when needed; do not attach entire unrelated directories by default.

```bash
oracle --dry-run summary -p "Review the relationship between these two modules; check the stated invariant and cite file evidence." \
  --file src/module-a.ts --file src/module-b.ts
```

Use the installed CLI's file report or dry-run to inspect the bundle and its size before sending. Exclude credentials, tokens, `.env` files, private keys, and unrelated personal data. Fit the actual selected model's limits rather than a fixed historical token budget.

## Run within authorization

Select `--engine browser` or `--engine api` explicitly; otherwise environment credentials can change the engine unexpectedly. Confirm the requested run is covered by the user's authorization for the destination and any metered API use. Do not install credentials or request new approval when valid authorization already covers the run.

Use the model spelling verified from the installed CLI. Record the session ID and effective model so the result is traceable. A browser run depends on an authorized signed-in session; an API run depends on an authorized credential and incurs provider charges.

## Resume, then assess

If a run times out, inspect `oracle status` and resume with `oracle session <id>` before retrying. A timeout may leave a detached job running; avoid duplicate submissions or bypassing duplicate guards.

Treat the returned opinion as review evidence. Check material findings against source files and tests, then apply justified fixes within the original scope. Report a mismatched effective model or an incomplete session explicitly.
