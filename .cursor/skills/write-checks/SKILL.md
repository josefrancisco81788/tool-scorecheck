---
name: write-checks
description: Turns one feature's requirements into measurable checks before any implementation. Use when drafting, reviewing, or revising checks for a feature that is not locked yet.
---

# Write checks

Produce the evaluation for one feature before any product code is written. The implementation agent does not get to define its own success after seeing its solution.

## Freedom

- High — how you phrase each check, as long as a later run can mark it pass or fail from observed behavior
- Medium — file shape. Follow [references/check-template.md](references/check-template.md)
- Low — where the file goes, and when you stop

## Procedure

1. Read the feature in `features.md` and the relevant facts in the project-context skill.
2. Write `checks/draft/<feature-id>.md` from the template. Use the feature's zero-padded id, for example `feature-001.md`.
3. Cover the requirement itself, the integration that makes it real, and a regression check if the feature changes behavior the app already has.
4. Include a completeness check: the user-facing behavior exists, separate from the rule behind it.
5. Fill the Executable tests section. Name every automated test that will prove the Behavior checks: its file, what it asserts with any tolerance as a number, and which check it proves. Name the test command, or say the feature creates it. Follow `docs/testing-standards.md` for which kinds of test are required; mark a kind "not applicable" only with a stated reason, for the human to approve. A Behavior check that no test proves either gets a test or is reworded so a person can observe it.
6. Stop. Do not implement the feature. Do not edit `checks/approved/`. Do not run `scripts/lock_checks.py` here; the build skill does that after the human approves.

## When a draft is rejected

Revise the draft in `checks/draft/` and stop for review again. Missing requirements are a human decision about the evaluation, not an implementation task.
