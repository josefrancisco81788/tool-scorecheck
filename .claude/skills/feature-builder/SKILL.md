---
name: feature-builder
description: Implements exactly one feature against checks that are already locked, and records every round. Use when checks/approved is locked and the user wants that feature built or fixed.
---

# Feature builder

Implement one locked feature. Start from this skill, `program.md`, the project-context skill, `features.md`, and the approved check file. Ignore accumulated discussion from other features.

## Freedom

- High — how you implement, within `program.md` and the project conventions
- Medium — the results write-up. Use [references/result-template.md](references/result-template.md)
- Low — the evaluation boundary and the iteration gate below

## Do not touch

- `checks/approved/**`
- `scripts/lock_checks.py`
- `scripts/verify_checks.py`
- `scripts/refresh_check_manifest.py`
- `program.md`, except you may not edit it at all in this skill (the auto-loop skill owns Learned rules)
- Immutable zones listed in the project-context skill, unless the user explicitly approved that edit in this session

## Iteration

Copy and update:

- [ ] `python scripts/verify_checks.py` passes before you change product code
- [ ] The test command named in the test plan runs. If the plan says the feature creates it, set it up first
- [ ] Every test that proves a locked check is written, and each one fails for the reason you expect, before any product code for it exists
- [ ] Implement one coherent attempt
- [ ] Run the project's tests and compare behavior to the approved checks
- [ ] Write `results/<feature-id>/round-NNN.md`
- [ ] Keep the attempt if failures went down and nothing previously passing broke; otherwise undo it
- [ ] Repeat until the approved checks pass
- [ ] Confirm completeness
- [ ] Stop

If `verify_checks.py` fails, stop immediately. The checks or the manifest changed. Ask the human. Do not edit checks and do not refresh the manifest to make the failure go away.

If a check fails because the check is wrong, or because the requirement was never written down, stop and say so. That is an evaluation problem for the human, not a prompt to weaken the check.

## Tests

Features 001–003 name their tests in an Executable tests table inside the locked check file. For those, the table is part of the evaluation: write the tests as it describes, and if a listed test is wrong, stop and say so.

From Feature 004 on, the test plan lives in `docs/choices/<feature-id>.md`. You own it. You may change a planned test when it is wrong, and you log the change and the reason there. Every locked check still needs at least one test that proves it, as the plain-language check reads.

Either way, never loosen a tolerance, skip, mark as expected-to-fail, or delete a test only to make it pass. You may add tests.

Engineering choices are yours. Make them, log them in `docs/choices/<feature-id>.md`, and keep going. Stop for the human only for the cases in "When to stop and ask" in `program.md`.

Mark a check as passing only when a test that proves it was seen passing in this round, or, for completeness, when you watched the behavior happen. Reading the code is not evidence. Paste the test output into the round's results file.

## Completeness

Checks passing means the measured rules passed. Before you call the feature done, also confirm:

- [ ] The user-facing behavior exists
- [ ] It is wired into the application
- [ ] Older code that already did this job follows the new behavior

If any item fails, fix it and run the checks again.
