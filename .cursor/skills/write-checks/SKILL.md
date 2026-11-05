---
name: write-checks
description: Turns one feature's requirements into measurable checks before any implementation. Use when drafting, reviewing, or revising checks for a feature that is not locked yet.
---

# Write checks

Produce the evaluation for one feature before any product code is written. The implementation agent does not get to define its own success after seeing its solution.

The locked file says **what the feature must show**, in plain language a non-developer can approve. It does not say how the code is built. Read "Who decides what" and "When to stop and ask" in `program.md` first.

## Freedom

- High — how you phrase each check, as long as a later run can mark it pass or fail from observed behavior
- High — every engineering choice. Make it and log it; do not ask the human
- Medium — file shape. Follow [references/check-template.md](references/check-template.md)
- Low — length, where the file goes, the review-round cap, and when you stop

## Procedure

1. Read the feature in `features.md` and the relevant facts in the project-context skill.
2. List the product questions: anything only the human can decide (what result, how much, for whom, any threshold that changes money, risk, or who is affected). Measure what you can first, for example by running the pipeline on the default seed in a scratch folder. Ask all of them in one batch, each with a recommended answer and the measured number behind it. Skip this step if there are none.
3. Write `checks/draft/<feature-id>.md` from the template. Use the feature's zero-padded id, for example `feature-001.md`. Keep it to about one page (roughly 60 lines). Each check is one or two plain sentences a person can read and agree with. Leave out hash digests, column orders, call counts, argument lists, and internal function names unless the human asked for them.
4. Write `docs/choices/<feature-id>.md`: every engineering choice you made (one line each: the choice, why, how to undo it) and the test plan (which tests prove which check, the test command, and which kinds from `docs/testing-standards.md` apply, with a reason for any kind marked not applicable). This file is not locked. The feature builder may change it and must log why.
5. Review once, yourself or with a reviewer. A finding counts only if a check cannot be measured, contradicts the requirement, or a requirement has no check. Loopholes only a deliberately dishonest implementation could use are not findings. At most 3 revision rounds; after that, stop and tell the human in plain words what is still unresolved.
6. Stop. Do not implement the feature. Do not edit `checks/approved/`. Do not run `scripts/lock_checks.py` here; the build skill does that after the human approves.

## When a draft is rejected

Revise the draft in `checks/draft/` and stop for review again. Missing requirements are a human decision about the evaluation, not an implementation task.
