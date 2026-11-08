# CLAUDE.md — Tool - ScoreCheck

> Seeded by the Stage 4 init script on 2026-10-24. Feeds the Dual-Agent Daily Cadence (Stage 6).

## What this system does

ScoreCheck is an open testbed for the lender's side of an alternative-data consumer credit score: it generates a synthetic Philippine behavioural panel, runs an in-house challenger in shadow mode beside a simulated black-box vendor score, and measures how the value of the model depends on who keeps the repayment outcomes. It produces a validation pack (ranking, calibration, drift, reject inference, fairness) that lets a lender or regulator see how either score behaves, plus a constrained, review-only LLM layer that drafts decline explanations from approved reason codes.

## Complexity tier

Complex

## Immutable Zones

Files/modules below require explicit human approval before any agent touches them:

- [ ] Vendor score internals: the vendor model module may only be reached through its score + three reason codes API; downstream code never reads inside it
- [ ] Behavioural-data schema (documented, with a fixed seed so every result can be reproduced)
- [ ] Approved reason-code list and policy text used by the Layer 4 agent
- [ ] checks/approved/ and MANIFEST.sha256

## Known risk patterns

_(empty at bootstrap — Stage 5 Session 0 dry-run should populate this with real findings before feature work starts)_

## Where to look first

- `docs/PRD.md` — product requirements
- `docs/design.md` — architecture / module boundaries
- `docs/testing-standards.md` — what tests are required and what blocks CI
- `decisions.md` — architecture map + open questions
- `scope.template.md` — explicit non-goals / scope boundaries
- `features.md` — one feature per build loop
- `program.md` — what the feature loop may and may not change
- `docs/linear-conventions.md` — what goes where in Linear, and who updates it
- `.cursor/skills/` and `.claude/skills/` — project-context, build, write-checks, feature-builder, auto-loop

## Agent loop

Build one feature at a time. Ask the human only product questions, in plain words with a recommendation; make engineering choices yourself and log them in `docs/choices/<feature-id>.md` (see `program.md` "Who decides what" and "When to stop and ask"). Checks are written and human-approved before implementation, then locked with `python scripts/lock_checks.py`. Do not edit `checks/approved/` or the check scripts. `python scripts/verify_checks.py` must pass before a feature is done, and the user-facing behavior still has to exist and be wired into the app. Recurring mistakes are appended to `program.md` Learned rules after a human confirms them. Same skills are installed for Cursor and Claude Code; if you edit one copy, edit the other. Update Linear only as `docs/linear-conventions.md` describes: the repo is the source of truth, status reaches Linear through PR links and one project update per finished feature.
