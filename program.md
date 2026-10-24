# program.md — Tool - ScoreCheck

Operating manual for the feature loop. The feature builder follows this file. The auto-loop skill may append under Learned rules after the user confirms a rule. A human owns every section above that.

## Objective

Build the next feature in `features.md` until its locked checks pass and the user-facing behavior exists and is connected to the app.

## Allowed modifications

- Application source and tests that implement the current feature
- Docs that describe that feature
- `results/<feature-id>/`
- The current feature's status lines in `features.md`

## Forbidden modifications

- `checks/approved/**`
- `scripts/lock_checks.py`
- `scripts/verify_checks.py`
- `scripts/refresh_check_manifest.py`
- This file, above Learned rules
- Immutable zones:

- Vendor score internals: the vendor model module may only be reached through its score + three reason codes API; downstream code never reads inside it
- Canonical behavioural-data schema (documented contract the validation layer depends on, so it can later run on other models)
- Approved reason-code list and policy text used by the Layer 4 agent
- checks/approved/ and MANIFEST.sha256

Run `python scripts/lock_checks.py` only from the build skill, after the user has approved the drafts.

Run `python scripts/refresh_check_manifest.py` only when the user explicitly says they changed an approved check. Never run it to make a failing verification pass.

## How to run an iteration

From the project root, with Python 3 (standard library only for the loop scripts):

1. `python scripts/verify_checks.py`
2. Run this project's tests. Stack at init: Python 3 with pandas and numpy for the panel, scikit-learn plus a GBM library with monotonic constraints (TODO confirm LightGBM or XGBoost) for vendor and challenger, a points-scorecard implementation, an LLM API for Layer 4, and a PDF report generator (TODO confirm). Use the command documented in `docs/testing-standards.md` once the project has one. If no test command exists yet, write that in the results file. A missing test run is not a pass.
3. Mark each item in the feature's approved check file from behavior you actually observed.

## Keep or undo

- Undo a round that breaks a check this feature already passed.
- If `verify_checks.py` fails, stop and ask the user. Do not keep editing product code against a broken evaluation.
- Keep a round when it reduces real failures without breaking a previous pass.
- Record every round as kept or undone.

## Correctness and completeness

Correctness: the locked checks pass and `verify_checks.py` exits 0.

Completeness: a person can do what the feature describes, the behavior is wired into the app, and older code that already did this job follows the new rules.

Both are required. Record completeness in the results file for the closing round.

## Learned rules

<!-- auto-loop may append below this line after the user confirms. Do not edit anything above. -->
