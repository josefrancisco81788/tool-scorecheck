# Engineering choices — feature-005

Owned by the agent. Not locked. Change a choice when it is wrong, and add a line saying what changed and why. Plain-language outcomes are locked in `checks/approved/feature-005.md` once approved.

## Measured on the default book (run 31a32519f30491a4, seed 20261024, 2026-11-05)

- Month 24 holdout: 17,467 applicants, 1,577 bad on the 6-month label (9.0%). Same set in both regimes.
- AUC: vendor 0.797; LightGBM 0.741 (data_owner) and 0.737 (vendor_only); scorecard 0.746 and 0.741.
- Thin (<=6 months) 6,210 / 584 bad: vendor 0.786, scorecard 0.729. Thick 11,257 / 993 bad: vendor 0.804, scorecard 0.758.
- At 80% approval: vendor 4.82% bad; LightGBM 5.93%; scorecard 5.83%. Swap-ins (LightGBM, 1,111) 21.5% bad; swap-outs 7.7%.
- Test cell: 717 accounts, 21.8% bad (all month-24 matured). Close to the 21.5% swap-in bad rate.
- Same-cutoff 0.117: vendor approves 80.3%, scorecard 86.5%.
- Vendor leads in every segment. Smallest groups have 32 bad (CAR), 36 (Zamboanga).

## Choices

| Choice | Why | How to undo |
|---|---|---|
| New package `src/scorecheck/report/` with `run(run_dir)`, called from `cli.main` after `experiment.run` | design.md module map | none |
| Inputs: `heldout_scores.parquet` (checkpoint 24), `outcomes.parquet`, `application_features`, `person`, `household`. No `vendor.score`, no Feature 003 `scores.parquet` | Issue JOS-27 and R1 | none |
| Report is written for both regimes; headline tables use `data_owner`, `vendor_only` repeats the same tables with a `regime` column | Cheap; shows the gap with and without outcomes | Drop the `vendor_only` rows |
| Rank lift = vendor AUC minus challenger AUC on the group, with a paired DeLong 95% interval (reuses `experiment/_metrics.py`); group marked `sparse` below 50 bad | Same method as Feature 004 | Drop the interval |
| Verdict wording per group: "vendor leads" when the interval's low end is above 0; "caught up" when it contains 0; "challenger ahead" when the high end is below 0 | Plain words from the interval | none |
| Equal approval rate: approve the lowest-scoring share by rank (ties broken by `application_id`), so the approval rate is exact | Exact equal rate | none |
| Expected loss: sum of bad x `credit_amount` x 0.60 over approved; shown per applicant and as share of approved loan value. `LOSS_GIVEN_DEFAULT = 0.60` | Product answer | Change the constant |
| Phased switch: a deterministic subset of the holdout of share p goes to the challenger (rank of `application_id` hashed with a fixed salt via `Streams(seed,"report")`), the rest stays with the vendor; probability cutoff is the same number for both. Reported: approval rate and expected loss, change versus vendor alone | R3 | none |
| Swap sets use the scorecard as the primary challenger; the other six lines in `full_lines.csv` | Product answer | none |
| Test cell cross-check: realised bad rate of `test_cell` applicants at checkpoint 24 with a Wilson 95% interval; the test cell has no held-out challenger score, so it is not scored | Test-cell accounts are in the challenger fit | none |
| Outputs: `lift_by_group.csv`, `phased_switch.csv`, `swap_sets.csv`, `equal_approval.csv`, `full_lines.csv`, `summary.md`. Written through a staging directory renamed to `data/experiment/<run id>/report/` | Same pattern as the other stages | none |
| `results/feature-005/` holds a copy of the default-book report plus `round-001.md` | Task requirement | none |

## Test plan

Test command: `python -m pytest`.

| Check | Tests (file) |
|---|---|
| R1 | report reads only the named files; no import of `vendor._private`; Feature 003 `scores.parquet` is not opened (`tests/unit/test_report_inputs.py`) |
| R2 | group sizes and bad counts add up to the holdout; AUC lift matches sklearn on a fixture; sparse flag below 50; thin cut is 6 (`tests/unit/test_report_lift.py`) |
| R3 | phased switch at p=0 equals vendor alone; p=1 equals the challenger alone; approval rate and expected loss deltas on a small hand-checked fixture (`tests/unit/test_report_switch.py`) |
| R4, R5 | swap-in and swap-out sizes equal at equal approval rate; counts and bad rates on a hand fixture; test-cell interval (`tests/unit/test_report_swap.py`) |
| R6 | equal approval is exact; expected loss against a hand computation (`tests/unit/test_report_equal_rate.py`) |
| R7 | summary text has no "beats" claim for a real vendor, states synthetic and simulated, and reports a negative lift unchanged (`tests/unit/test_report_summary.py`) |
| R8 | two subprocess runs give equal tables (`tests/evals/test_report_repeat.py`) |
| R9, Integration, Completeness | default command writes the files and finishes within 600 s (`tests/integration/test_cli_run.py`) |
| Golden | the 2,000-household report tables in `tests/fixtures/golden/` with a changelog line (`tests/unit/test_report_golden.py`) |

Test kinds from `docs/testing-standards.md`: unit, golden, eval (same-machine repeat run) all apply. The eval is not asserting any model beats a real vendor.

## Change log

- 2026-11-05: Draft written after measuring the default book and the user's answers (thin = 6 months or less, 60% loss-given-default, scorecard named, both cutoff views).
- 2026-11-07: Built. Changes from the draft:
  - Added a `segment` named `all` (whole holdout) and used `history` for the thin or thick segment; both are rows in `lift_by_group.csv`.
  - `phased_switch.csv` carries the scorecard only; the other six lines appear in `full_lines.csv` (lift, equal-approval gap, swap-in and swap-out sizes and bad rates) and in `equal_approval.csv`.
  - `swap_sets.csv` also lists the two groups both models agree on (`both_approve`, `both_decline`) for context, plus a `test_cell` row with a Wilson 95% interval. The test cell uses only accounts with a matured 6-month outcome.
  - Phased-switch subset: one `Streams(seed, "report")("phased_switch")` uniform draw per holdout applicant (in `application_id` order); the lowest `round(share x n)` draws go to the challenger, so the subsets nest (25% inside 50% and so on). Why: deterministic and needs no extra hashing.
  - Tables are rounded to six places before writing and CSVs use LF line endings, so repeat runs are byte-equal. Why: R8 compares files.
  - Golden: `tests/fixtures/golden/report_2000.json` holds headline numbers (exact counts, rates to 1e-6) rather than a file hash, so a library patch version does not break it. Changelog line added.
  - Test plan: added `tests/support/report.py` (hand fixtures) and a `report_2000` session fixture in `tests/conftest.py`; `tests/unit/test_report_golden.py` and `tests/evals/test_report_repeat.py` as planned.
  - Finding, reported as it came out: on the default book the vendor leads the scorecard overall (AUC 0.797 against 0.746) and in 29 of 32 groups; the scorecard has caught up in three regions (Central Visayas, Eastern Visayas, Northern Mindanao); no group has the challenger ahead. A full switch at the same cutoff approves more and loses more. At an equal 80% approval rate the scorecard lets in 141 more defaults and 24.5% more expected loss than the vendor.
