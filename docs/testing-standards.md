# Testing Standards — Global

> Stage 3 of the Project Initiation Pipeline. Write once, reference from every project. Mirrored into each repo as the top half of `docs/testing-standards.md` — the bottom half is the project-specific supplement generated per project from PRD §5.

---

## Coverage Thresholds

- Core business logic / core functions: **80% line coverage minimum**, enforced in CI.
- Glue code, CLI wrappers, config loading: no hard threshold, but must have at least one smoke test.
- Coverage drop on a PR (vs. main) is advisory, not blocking, unless it drops a core module below 80%.

## Golden-Dataset Policy (financial / ML code)

Required for any function that produces a financial calculation, an ML prediction, or otherwise-deterministic business-logic output that downstream systems depend on.

- Store fixed input → expected-output pairs in `tests/fixtures/golden/`.
- A change that alters a golden output must come with an explicit changelog line explaining why the expected value changed — silent golden-file updates are not allowed.
- Golden test failures block merge. No exceptions without a documented sign-off in `docs/reviews/`.

## Eval Suite Conventions (non-deterministic / LLM-backed features)

- Store eval cases in `tests/evals/*.json` — one file per capability/feature, not one giant file.
- Each case: `{ "input": ..., "expected": ..., "rubric_or_match_type": "exact | semantic | contains | custom" }`.
- "Regression" for non-deterministic output means: output falls outside the documented acceptable variance (e.g., semantic similarity threshold, rubric score threshold) — not "differs from a previous run token-for-token."
- Eval suite failures are CI-blocking once a feature ships past MVP; advisory while still in the MVP feature list (see PRD §2).

## What Counts as "Regression"

- Deterministic code: any output that differs from the golden/fixture value.
- Non-deterministic code: any output that falls outside the declared acceptable variance/rubric for that eval case. Define the variance/rubric per eval case — don't leave it implicit.

## Test Data Policy

- Small, anonymized samples only in `tests/fixtures/`.
- Real or large data stays out of the repo — gitignore `data/raw/`.
- No real credentials, PII, or production data in any test fixture, ever.

## CI Pipeline (baseline, every repo)

- Lint + unit tests run on every PR.
- Coverage reporting on every PR (informational unless it breaches the 80% core-module threshold above).
- Merge is blocked on: unit test failure, golden/regression test failure, or (post-MVP) eval suite failure.
- Merge is NOT blocked on: coverage dips outside core modules, eval failures while a feature is still MVP-stage.

## Review Gate

The reviewing agent checks test coverage and eval results against this document during diff review (per the Dual-Agent Daily Workflow's review gate step) — not against ad hoc judgment.

---

## Project-Specific Supplement — Tool - ScoreCheck

> Generated on 2026-10-24 from PRD §5 answers.

- Golden-dataset / regression tests required: Yes
- Eval suite required (non-deterministic/LLM-backed features): Yes
- CI blocking vs. advisory for this project: Unit tests, approved checks (verify_checks.py) and generator determinism tests block merge; eval harness scores and validation-pack metrics are advisory until v1.
- Compliance flag: No

Test commands, from the repo root after `pip install -r requirements.txt`:

- Everything: `python -m pytest`
- Unit suite, which blocks merge: `python -m pytest tests/unit`
- Eval suite, advisory until v1: `python -m pytest tests/evals`
- Integration suite, which runs the 50,000-household default command: `python -m pytest tests/integration`
- Core-module coverage: `python -m pytest tests/unit --cov=scorecheck.panel --cov=scorecheck.features --cov-report=term-missing`

Regenerate the golden panel with `python scripts/write_golden_panel.py`, and add a line to `tests/fixtures/golden/CHANGELOG.md` saying why any hash changed.

Per-feature test needs (fill in as features move from MVP list to implementation):

- Synthetic behavioural panel: unit test required; golden dataset required; eval case required
- Black-box vendor score API: unit test required; golden dataset required; eval case required
- In-house challenger in shadow mode: unit test required; golden dataset required; eval case required
- Outcomes-ownership experiment: unit test required; golden dataset required; eval case required
- Champion and challenger decision report: unit test required; golden dataset required; eval case required
- Lender validation pack: unit test required; golden dataset required; eval case required
- Constrained decline-explanation agent: unit test required; golden dataset required; eval case required
