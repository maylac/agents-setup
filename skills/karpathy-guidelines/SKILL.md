---
name: karpathy-guidelines
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to keep changes simple and surgical and define verifiable success criteria.
license: MIT
---

# Karpathy Guidelines

Apply these principles while writing, reviewing, or refactoring code. They guide implementation judgment; they do not replace the user's scope or authorize unrelated work.

## Think before coding

State the material assumptions and success criterion before a multi-step change. Resolve ordinary implementation choices from the request, repository conventions, and available evidence. Ask only when an ambiguity materially changes behavior, scope, safety, destination, credentials, or an irreversible action.

For a design with meaningful alternatives, name the tradeoff and choose the simplest approach that satisfies the request. Do not manufacture alternatives for routine details.

## Simplicity first

Write the minimum code and tests that solve the requested problem:

- no speculative features, abstraction for one use, or unrequested configurability;
- no error handling for impossible states;
- no broad cleanup masquerading as part of a narrow task.

If the solution is larger than its acceptance criterion warrants, simplify it before extending it.

## Make surgical changes

Touch only lines that trace to the request. Match local style. Remove imports, variables, functions, or tests made obsolete by your own change, but leave pre-existing dead code for a separately authorized task.

Preserve unrelated working-tree changes and do not overwrite them to obtain a clean diff.

## Drive to evidence

Define checks that demonstrate the requested behavior before claiming completion. For a multi-step task, state a brief plan with a check for each material step. Run the narrowest meaningful verification, then broaden it only to resolve a concrete risk or meet a required gate.

Distinguish verified behavior from assumptions and remaining scope. A successful command proves only what that command actually checked.
