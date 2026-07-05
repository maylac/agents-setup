---
name: apple-shortcuts-builder
description: Build, sign, export, or troubleshoot importable Apple Shortcuts (.shortcut) for iOS, iPadOS, macOS, Siri, and URL schemes.
---

# Apple Shortcuts Builder

## Workflow

1. Clarify only the constraints that affect the generated shortcut:
   - trigger path: manual, Share Sheet, Action Button, Back Tap, automation, URL scheme
   - inputs and outputs
   - apps/services involved
   - whether the deliverable should be an importable `.shortcut` file or just build steps

2. State iOS/macOS constraints before building:
   - Do not claim system behaviors can be overridden unless verified.
   - Do not claim the file imports on iPhone unless the user or a local device test confirms it.
   - If unsure about current Shortcuts behavior, verify from Apple documentation or local `shortcuts` tooling.

3. Design the shortest viable action list. Prefer built-in Shortcuts actions and implicit previous-action input before creating variables or complex wiring.

4. Generate the file with `scripts/build_shortcut.py` when the output is an importable shortcut:

```bash
python3 $HOME/.codex/skills/apple-shortcuts-builder/scripts/build_shortcut.py \
  --config shortcut.json \
  --unsigned-output shortcut.unsigned.shortcut \
  --signed-output "My Shortcut.shortcut"
```

5. Verify locally:
   - `plutil -lint <unsigned.shortcut>`
   - `test -s <signed.shortcut>`
   - `strings <signed.shortcut> | rg '<expected-action-id-or-param>'`
   - `openssl dgst -sha256 <signed.shortcut>`

6. Deliver:
   - link the signed `.shortcut` file
   - summarize the action list
   - tell the user what was verified locally and what still requires iPhone/iPad/macOS import confirmation

## Config Format

Use a JSON config for the generator:

```json
{
  "name": "Screenshot to Clipboard",
  "workflow_types": ["NCWidget"],
  "actions": [
    {"id": "is.workflow.actions.takescreenshot"},
    {"id": "is.workflow.actions.setclipboard", "params": {"WFLocalOnly": true}}
  ]
}
```

Each action needs an `id`. Optional `params` are copied into `WFWorkflowActionParameters`. The script adds a UUID to each action when one is not provided.

For known action IDs, common parameters, and examples, read `references/action-format.md`.

## Signing Notes

Use `/usr/bin/shortcuts sign --mode anyone` for files the user may import on another device. `shortcuts sign` can emit Objective-C runtime warnings to stderr while still exiting `0`; treat exit code, file existence, and nonzero file size as the signing check.

Signed `.shortcut` files are wrapper data and may not parse with `plutil`; inspect the unsigned file with `plutil` and the signed file with `strings`, `file`, and size/hash checks.

## Fallback

If generated files are rejected by Shortcuts, provide manual build steps using the same action list. Apple does not expose a stable public code-generation API for arbitrary Shortcuts, so `.shortcut` generation is best-effort unless imported and tested on the target device.
