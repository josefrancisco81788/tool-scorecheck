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
- Behavioural-data schema (documented, with a fixed seed so every result can be reproduced)
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

## Who decides what

The human is not expected to judge engineering detail. Split every feature's decisions in two:

- **Product questions go to the human.** What result the feature must show, how much, for whom, and any threshold that changes money, risk, or who is affected (for example, what share of applicants the lender declines). Ask them in plain words, in one batch, before drafting checks. Give a recommended answer and, where one can be measured, the measured number behind it.
- **Engineering choices belong to the agent.** File layout, column order, function names, training arguments, hashing, call counts, test design, tolerances. Make the choice, write it in `docs/choices/<feature-id>.md` with one line of why and how to undo it, and move on. Do not ask the human to approve these and do not lock them.

The locked check file holds only the product outcomes, in plain language, about one page. A check a person cannot read and say "yes, that's what I want" does not belong in it.

If a check locked by an earlier feature blocks a sensible engineering choice, do not work around it silently. Propose the smallest edit to that check in plain words with a recommendation. After the human says yes, edit it and run `python scripts/refresh_check_manifest.py`.

## When to stop and ask

Count these as blocked, and tell the human in plain words what is unresolved and what you recommend:

- A check draft has had 3 revision rounds without being approved. A reviewer (`/interrogate`, a swarm, or a second agent) may only raise a check that cannot be measured, a check that contradicts the requirement, or a requirement with no check. Loopholes that only a deliberately dishonest implementation could use are not review findings.
- A feature has run more than 2 hours without a new check lock, a passing round, or a merge.
- A locked check, from this feature or an earlier one, is wrong or blocks the feature.

Post each review verdict on the feature's PR before locking or merging, so the reason a feature passed can be found later.

## Learned rules

<!-- auto-loop may append below this line after the user confirms. Do not edit anything above. -->
