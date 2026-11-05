# Engineering choices — feature-004

Owned by the agent. Not locked. Change a choice when it is wrong, and add a line saying what changed and why. Plain-language outcomes are locked in `checks/approved/feature-004.md` once approved.

`feature-004-old-draft.md` beside this file is the earlier 252-line check draft. It is reference material for file layouts and training arguments, not a contract. Its 0.5 cutoff, "defaulted by checkpoint C" label, and on-book-only holdout are superseded.

## Measured on the default book (seed 20261024, 50,000 households, 2026-11-05)

- 87,337 applications. Origination months 2–18, about 5,100 per month, so a 6-month window matures for every account by month 24.
- `true_default` never goes from 1 back to 0. `default_label` (1.47%) is exactly "already in default at origination".
- Vendor probability: mean 0.0148, 80th percentile 0.0185, max 0.869.
- 6-month bad rate 7.3%. Approved accounts 4.0% bad, declined accounts 19.9% bad.
- Training accounts (approved, non-holdout, open 6 months) and bads, before the test cell: month 8 3,163 / 133; month 12 16,221 / 646; month 16 29,576 / 1,202; month 20 42,916 / 1,720; month 24 55,813 / 2,207.
- Holdout: 17,467 accounts, 1,305 bad. 3,448 of them would be declined, and 697 of those are bad.

## Choices

| Choice | Why | How to undo |
|---|---|---|
| Bad = first month with `true_default` 1 is no later than `origination_month + 6`. An account already in default at origination counts as bad | User's 6-month window. Leaving already-defaulted accounts out would call them good | Change the window constant `BAD_WINDOW_MONTHS` |
| An account enters a fit at checkpoint C only when `origination_month + 6 <= C` | The outcome must be fully matured | none |
| Month 4: no refit in either regime; points use the starting models (published vendor ledger, origination-fit challengers) | Nothing has matured by month 4 | Shorten the window |
| Evaluation target: every holdout application, approved or not, labelled with the 6-month bad, at every checkpoint | User's fixed-target rule. Truth is known for all in a simulation | none |
| Batch reader `vendor.regime.read_published` inside `vendor/`: one hash and one read for the whole book | `vendor.score` re-hashes the feature table on every call, about 12 hours across the default book | Replace with a cache inside `vendor.score` |
| Cutoff constant `APPROVAL_MAX_PROBABILITY = 0.0185`, approve when strictly below | User chose about 20% declined | Change the constant and re-measure |
| Test cell: each would-be-declined, non-holdout applicant is approved with probability 0.05, drawn from `Streams(seed, "experiment")("test_cell")`. The draw is made once per application and is the same in both regimes | User chose 5%. One draw keeps the regimes comparable | Set `TEST_CELL_SHARE = 0` |
| Test-cell outcomes flow to the same models as any approved loan: the vendor in both regimes, the challengers only in `data_owner` | They are real loans the lender made | none |
| At checkpoint C, approval uses the model from the previous checkpoint (the published ledger at C = 4); the curve scores the model just refit at C | A lender decides with the model it already has | Score the curve with the previous model |
| `vendor_only` challengers are fit once on origination `default_label`, excluding the holdout, and never updated | That regime's data owner never sees repayment | none |
| Confidence intervals: 95%. AUC gap uses the paired DeLong method on the holdout. Log-loss and Brier gaps are means of per-applicant differences, so they use a normal interval on those paired differences | Exact enough and fast. A bootstrap over 84 points on 17,467 rows would cost minutes against the 600-second limit | Switch to a seeded paired bootstrap |
| Curve columns add `vendor_fit_n`, `vendor_fit_bads`, `line_fit_n`, `line_fit_bads`, `fit_test_cell_n`, `holdout_n`, `holdout_bads`, and `<metric>_gap_low` / `<metric>_gap_high` for each metric | E7 | none |
| Vendor refits reuse the Feature 002 LightGBM arguments and seed; challenger refits reuse the Feature 003 arguments, seeds, and scorecard | Keeps the gap about data, not tuning | none |
| A refit whose labels have only one class does not train; it keeps the previous model's scores | Boosters cannot fit one class | none |
| Outputs under `data/experiment/<run id>/`: `<regime>/` (vendor ledger, `challengers/`), `outcomes.parquet` (with a `test_cell` flag), `heldout_scores.parquet`, `curves.parquet`, `fits.parquet`, `hypothesis.txt` | Keeps the Feature 002 and 003 directories untouched | none |
| No stored booster learning curve as a golden file; the golden numbers are a small sklearn metrics fixture (`feature-004-fixtures.py`) plus a DeLong fixture | Booster scores differ across machines, as in Feature 003 | Store a curve golden per machine |
| `experiment.run` never calls `vendor.score` and never reads `data/models/<run id>/scores.parquet` | Speed, and the Feature 003 vendor column is a constant 0.5 on books over 300 | none |

## Test plan

Test command: `python -m pytest`.

| Check | Tests (file) |
|---|---|
| E1 | regime names and checkpoints; no refit at month 4; `vendor_only` challengers frozen (`tests/unit/test_experiment_regimes.py`) |
| E2 | `approve` at the cutoff edges; test-cell share about 5% of would-be declines on a 300-household book with a fixed seed; flipping every `true_default` leaves month-4 approvals and the test cell unchanged; cutoff decline share between 15% and 25% on the default book (unit + `tests/integration/test_cli_run.py`) |
| E3 | every fit id is approved or test cell, non-holdout, and open 6 months; labels equal the 6-month bad (`tests/unit/test_experiment_labels.py`) |
| E4, E5 | no holdout id in any fit; every checkpoint's holdout set and labels are identical, including would-be declines (`tests/unit/test_experiment_holdout.py`) |
| E6 | curve table shape (2 × 6 × 7); metrics match sklearn on the fixture at 1e-12; negative gaps kept (`tests/unit/test_experiment_gap.py`, `tests/fixtures/golden/`) |
| E7 | count columns equal the fits' actual sizes; DeLong interval matches a hand-checked fixture; each interval contains its gap (`tests/unit/test_experiment_intervals.py`) |
| E8 | hypothesis text written; no code path reads it (`tests/unit/test_experiment_hypothesis.py`) |
| E9 | outcomes table rows, hidden-label rule, test-cell flag; `application_features` logical hash unchanged (`tests/unit/test_experiment_outcomes.py`) |
| E10 | no import of `vendor._private` outside `vendor/`; Feature 002 and 003 directories unchanged after `run` (`tests/unit/test_experiment_boundary.py`) |
| E11 | two subprocess runs give equal curves, intervals, test cell, and outcomes (`tests/evals/test_experiment_repeat.py`) |
| Integration, Completeness | default command within 600 s, files present (`tests/integration/test_cli_run.py`) |

Test kinds from `docs/testing-standards.md`: unit, golden (the sklearn and DeLong fixtures), and eval (the same-machine repeat run) all apply.

## Change log

- 2026-11-05: Replaced the 252-line draft with a one-page outcomes draft; cutoff 0.5 → 0.0185 on the user's 20% decline answer.
- 2026-11-05: Added the 6-month bad definition, the fixed whole-holdout evaluation target, the counts and confidence intervals behind each point, and a 5% random test cell, on the user's review.
