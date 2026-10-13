---
name: opus-task-loop
description: Apply a stop-or-continue verification loop after a failed approach, repeated tool failure, uncertain completion claim, or costly stopping decision. Do not trigger for ordinary multi-step work with clear acceptance criteria.
license: MIT
---

# Opus Task Loop

Use this recovery loop when progress has become uncertain. Its purpose is to replace an unsupported completion claim with evidence or a clear next action.

1. **Reframe:** restate the acceptance criterion and identify the specific failed assumption or unresolved decision. Resolve ordinary implementation details from the request and local conventions; ask only when a missing choice materially changes scope, safety, destination, or an irreversible result.
2. **Act:** make the smallest next change or observation that can distinguish the leading explanations.
3. **Verify:** use a check independent of the action itself. Exercise the edge case being claimed, compare against a separately derived expected result, inspect the actual artifact, or run the relevant deterministic validator.
4. **Decide:** continue when evidence exposes a gap. Stop only as **verified done**, **scoped incomplete** with named leftovers, or **blocked** with the information or change needed.

Running without an error and a plausible-looking output do not establish correctness. Choose the check most likely to falsify the claim, proportionate to the task's risk.

`karpathy-guidelines` covers the default implementation discipline. Use this loop after a failed approach or uncertain stopping point. If the task required a real pivot and produces a reusable technical lesson, record it through `extract-approach`; if it becomes an irreversible system-wide decision, apply the active harness's appropriate escalation process.
