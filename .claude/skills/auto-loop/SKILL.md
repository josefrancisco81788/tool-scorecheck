---
name: auto-loop
description: Reviews feature results for recurring mistakes and appends confirmed rules to program.md Learned rules. Use after a feature is complete, or when the user asks to improve the build workflow. Does not edit approved checks.
---

# Auto loop

Improve the next feature's method. Do not rebuild the feature, and do not change what "done" means.

## Read

- `results/` for the feature that just finished, and earlier features when they exist
- `program.md` Learned rules, so you do not propose a duplicate

Classify each real failure with [references/failure-taxonomy.md](references/failure-taxonomy.md).

## What you may change

After the user confirms a proposed rule, append it under `program.md` → Learned rules. Nothing above that section.

## What you must not change

- `checks/approved/**`
- `scripts/lock_checks.py`
- `scripts/verify_checks.py`
- `scripts/refresh_check_manifest.py`
- Any check file in `checks/draft/`

A failing check is never fixed by editing the check.

## Procedure

1. List recurring patterns: same implementation mistake, same missed integration, same failed check type, same misunderstood convention.
2. One-off implementation slips stay in the results file. A pattern that already appears, or will obviously recur on the next feature, becomes a proposed rule.
3. Show the rule in one or two sentences and name the result rounds that justify it.
4. If the user confirms, append it under Learned rules as `- <rule>`.
5. If the pattern is a missing requirement or a wrong check, stop and ask the user to revise the evaluation. Do not encode that into `program.md` as a way to skip the check.

## Examples of rules that belong here

- Connect the feature to the application in the same round that makes its checks pass.
- When changing a behavior the app already has, update every place that still performs that job.
