# feature-004 — round 001

Status: kept

## Attempt

Built the experiment package `src/scorecheck/experiment/`, the vendor and models regime refits (`vendor/regime.py` with `read_published`, `Refitter`, and write/read; `models/regime.py` with `woe_transform` and the challenger refit), the CLI wiring, and the tests.

Midway, the first default-book run used a fixed 0.0185 cutoff. Overall it declined 58.0% of applicants. Windows after the first refit declined 79.6%, 87.6%, and 86.9%. The cause is that the refit vendor predicts the 6-month bad rate (about 4% to 7%), while the published ledger is on about 1.5%. The user decided to re-pin. The cutoff is now 0.0185 until the first vendor refit, then the 80th percentile of the refit model's scores on the next window's applicants (scores only). The E2 wording in the locked check was edited by the human's decision and the manifest was refreshed. That was a deliberate check edit, recorded here.

Default-book results (seed 20261024, 50,000 households):

- Overall decline 20.3%.
- Windows (applications, declined share, cutoff, test-cell count): months 1–4: 15,541, 22.4%, 0.0185, 133; months 5–8: 20,598, 19.6%, 0.0185, 182; months 9–12: 20,580, 20.0%, 0.074251, 144; months 13–16: 20,420, 20.0%, 0.104414, 176; months 17–20: 10,198, 20.0%, 0.117408, 82.
- Test cell total 717, which is 5% of 14,222 non-holdout would-be declines.
- Month-24 fit: 56,365 accounts, 2,912 bad. Holdout: 17,467 accounts, 1,305 bad.

AUC gap (vendor minus challenger, LightGBM line, 95% CI):

| Regime | m4 | m8 | m12 | m16 | m20 | m24 |
|---|---|---|---|---|---|---|
| vendor_only | 0.0524 [0.0420, 0.0629] | -0.0275 [-0.0429, -0.0121] | 0.0479 [0.0381, 0.0577] | 0.0574 [0.0483, 0.0666] | 0.0608 [0.0523, 0.0694] | 0.0605 [0.0518, 0.0692] |
| data_owner | 0.0524 [0.0420, 0.0629] | 0.1205 [0.1075, 0.1334] | 0.0692 [0.0598, 0.0785] | 0.0609 [0.0525, 0.0694] | 0.0561 [0.0483, 0.0640] | 0.0561 [0.0482, 0.0641] |

Log-loss and Brier gaps are negative at every point after month 4 in both regimes, so the challenger is better calibrated there.

The hypothesis (the vendor leads early, and the gap narrows only where the data owner keeps outcomes) is only partly visible. At month 24 the gap is about 0.056 AUC in `data_owner` against 0.061 in `vendor_only`. The `data_owner` gap is wider at month 8 (0.121 against -0.028), and the two regimes' curves are not the same shape. The curves are reported as they came out. Nothing was tuned.

## Checks

- E1: pass
- E2: pass
- E3: pass
- E4: pass
- E5: pass
- E6: pass
- E7: pass
- E8: pass
- E9: pass
- E10: pass
- E11: pass
- Integration: pass
- Regression: pass
- Completeness: pass

Check tests, from the Test plan table in `docs/choices/feature-004.md`:

- E1: regime names and checkpoints; no refit at month 4; `vendor_only` challengers frozen (`tests/unit/test_experiment_regimes.py`).
- E2: `approve` at the cutoff edges; test-cell share about 5% on the 2,000-household book (`tests/unit/test_experiment_approval.py`); flipping every `true_default` leaves month-4 approvals and the test cell unchanged; cutoff decline share between 15% and 25% on the default book (unit and `tests/integration/test_cli_run.py`). The E2 wording was edited by the human's decision (see Attempt).
- E3: fit ids are approved or test cell, non-holdout, open 6 months; labels equal the 6-month bad (`tests/unit/test_experiment_labels.py`).
- E4, E5: no holdout id in any fit; holdout set and labels identical at every checkpoint, including would-be declines (`tests/unit/test_experiment_holdout.py`).
- E6: curve table shape (2 × 6 × 7); metrics match sklearn on the fixture at 1e-12; negative gaps kept (`tests/unit/test_experiment_gap.py`, `tests/fixtures/golden/`).
- E7: count columns equal the fits' actual sizes; DeLong interval matches a hand-checked fixture; each interval contains its gap (`tests/unit/test_experiment_intervals.py`).
- E8: hypothesis text written; no code path reads it (`tests/unit/test_experiment_hypothesis.py`).
- E9: outcomes rows, hidden-label rule, test-cell flag; `application_features` logical hash unchanged (`tests/unit/test_experiment_outcomes.py`).
- E10: no import of `vendor._private` outside `vendor/` and Feature 002 and 003 directories unchanged after `run` (`tests/unit/test_experiment_boundary.py`); vendor batch reader and refits (`tests/unit/test_vendor_regime.py`); challenger refit and `woe_transform` (`tests/unit/test_models_regime.py`).
- E11: two subprocess runs give equal curves, intervals, test cell, and outcomes (`tests/evals/test_experiment_repeat.py`).
- Integration: default command within 600 s and files present (`tests/integration/test_cli_run.py`).
- Regression: Feature 001 to 003 tests are inside the 219 passing. Feature 002 rule V3 is narrowed as agreed, to allow `vendor.regime.read_published`.

`verify_checks.py`: pass. Output: `Locked checks verified (4 file(s)).`

## Test run

Command: `python -m pytest` from the repo root.

```text
219 passed in 530.49s (0:08:50)
```

The integration test `tests/integration/test_cli_run.py::test_cli_default_run` is inside the 219. It runs the default command under the 600 second limit. Timed separately, the default command took 1m59s.

## Failure

Two items came up, both recorded here.

1. Evaluation: the fixed 0.0185 cutoff declined 58.0% of applicants overall, far from the about 20% target, because the refit vendor is on the 6-month bad scale. Fixed by the human's re-pin decision described in Attempt. The E2 wording was edited by that decision and the manifest refreshed.
2. Environment: `tests/fixtures/golden/panel.json` had CRLF line endings from the local `core.autocrlf=true` setting, which made `test_golden_script_stops_at_from_panel` fail locally. The working copy was normalised to LF. Git shows no content change, and the test passed. No test was changed.

Failure type: evaluation (the CRLF item is environment).

## What changed

- `src/scorecheck/experiment/` is the outcomes-ownership experiment package. `run` writes `data/experiment/<run id>/`, through a staging directory renamed into place.
- `src/scorecheck/vendor/regime.py` adds `read_published`, `Refitter`, and write/read for the regime ledgers.
- `src/scorecheck/models/regime.py` adds `woe_transform` and the challenger refit. `models._fit_challengers` and the private fitters take an optional score matrix; default output is unchanged.
- `src/scorecheck/cli.py` is wired to the experiment.
- `checks/approved/feature-004.md` E2 wording edited by the human; `MANIFEST.sha256` refreshed.
- `docs/choices/feature-004.md` records the cutoff re-pin and the findings.
- Unit, eval, and integration tests named in the Test plan table.
- `features.md`: Feature 004 is Complete.

Outputs, default run `data/experiment/31a32519f30491a4/`: `curves.parquet` (84 rows), `fits.parquet`, `outcomes.parquet`, `heldout_scores.parquet`, `hypothesis.txt`, and both regime directories.

## Why kept or undone

The `python -m pytest` run passed all 219 tests, including the default-command integration test. `verify_checks.py` reports 4 locked check files verified. The default command produces the curves, fits, outcomes, and hypothesis files. The decline share is 19.6% to 22.4% in each window on the default book. The result is kept with the findings above reported as measured.

## Lesson

A fixed numeric cutoff chosen on one model's scale does not carry to a refit model; check the decline share per window early. Candidate for `program.md` Learned rules, not appended; to be confirmed by the human.

## Completeness

A person runs `python -m scorecheck` from the repo root. The default command was run, and `data/experiment/31a32519f30491a4/` holds `curves.parquet` (84 rows), `fits.parquet`, `outcomes.parquet`, `heldout_scores.parquet`, `hypothesis.txt`, and both regime directories. The directory layout is as listed in the Attempt and What changed sections.
