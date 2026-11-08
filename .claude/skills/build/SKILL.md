---
name: build
description: Runs one feature through the agent loop — clarify it, write checks, get human approval, lock the checks, implement, evaluate, and record results. Use when the user asks to build a feature, start the next feature, or run the build loop.
---

# Build

Control one feature from `features.md` through a finished result. Do not build the whole app in one loop.

Degrees of freedom differ by step. Follow the low-freedom steps exactly.

## Progress

Copy this checklist and keep it updated:

- [ ] Feature chosen in `features.md` (one feature only)
- [ ] Requirements clear enough to test
- [ ] Product questions asked in one plain-language batch, with recommendations (or none needed)
- [ ] Checks drafted with the write-checks skill into `checks/draft/`, engineering choices in `docs/choices/`
- [ ] Human reviewed the checks in plain language
- [ ] Drafts revised if the human added or rejected anything, then reviewed again
- [ ] Checks locked
- [ ] Human committed `checks/approved/`
- [ ] Feature builder implemented the feature in a fresh context
- [ ] Locked checks pass and `python scripts/verify_checks.py` passes
- [ ] Completeness confirmed (the user-facing behavior exists and is wired in)
- [ ] Results recorded
- [ ] Project-context updated in both skill copies
- [ ] Auto-loop reviewed results before the next feature

If a review or check fails, return to the step that produces that artifact. Do not mark the feature complete while a step is failed.

## Steps

### 1. Choose the feature — high freedom

Pick the next feature whose status is `Not started`, or the one the user named. Read its requirements in `features.md` and the project facts in the project-context skill. Set status to `Checks in draft`.

### 2. Draft checks — medium freedom

Use the write-checks skill. Checks land in `checks/draft/` only.

### 3. Human review — low freedom

Stop and show the checks in plain language. Ask whether they cover what the user cares about. Wait for an answer.

The user approves outcomes, not engineering. Do not ask them to review `docs/choices/`, test tables, column lists, or call counts. Mention a test kind marked "not applicable" in one line with its reason.

If the user changes a requirement, update `features.md`, revise the draft, and review again. Follow "When to stop and ask" in `program.md`: after 3 revision rounds, stop and say in plain words what is unresolved.

If a check locked by an earlier feature blocks this one, propose the smallest edit to it in plain words with a recommendation. Only after the user says yes, edit it and run `python scripts/refresh_check_manifest.py`.

### 4. Lock — low freedom

After approval, run exactly:

```bash
python scripts/lock_checks.py
```

Do not add flags. Do not copy files into `checks/approved/` by hand.

Then stop and ask the user to commit `checks/approved/` (the check files and `MANIFEST.sha256`) before implementation. Set the feature status to `Checks locked`.

### 5. Implement — medium freedom

Hand the feature to a fresh feature-builder context with:

- the project-context skill
- `program.md`
- this feature's section in `features.md`
- the locked check file
- `docs/choices/<feature-id>.md`
- the feature-builder skill

Do not carry earlier features' conversation into that context.

### 6. Close — high freedom for the report, low freedom for the gate

The feature is complete only when both are true:

- every locked check for it passes, shown by the test output in its results file, and `python scripts/verify_checks.py` exits 0
- completeness holds: a person can do the thing the feature describes, and it is connected to the app

Run the test command and `python scripts/verify_checks.py` yourself rather than relying on the feature builder's report.

Update `features.md` status to `Complete` and point at the results folder.

Update the project-context skill's `references/project.md` with what this feature settled: the test command, where new modules live, dependencies added, conventions adopted, and any change to architecture or non-goals. Make the identical edit in both `.claude/skills/` and `.cursor/skills/`. If nothing changed, say so in the results file.

Update Linear as `docs/linear-conventions.md` describes: the merged PR moves the feature issue, and one project update records the findings and the PR link. Delegate this to a Haiku subagent. Do not edit Linear descriptions for status.

Then use the auto-loop skill before starting another feature.
