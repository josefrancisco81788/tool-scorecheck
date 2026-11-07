# feature-005 — round 001

Status: kept

## Attempt

Built the report package `src/scorecheck/report/` (`_constants.py`, `_tables.py`, `_summary.py`, `_run.py`) and wired `report.run(run_dir)` into `cli.main` right after `experiment.run`. It reads only `heldout_scores.parquet` (checkpoint 24, both regimes) and `outcomes.parquet` from the experiment directory, plus processed `application_features`, `person`, `household`. It writes `lift_by_group.csv`, `phased_switch.csv`, `swap_sets.csv`, `equal_approval.csv`, `full_lines.csv`, and `summary.md` through a staging directory renamed to `data/experiment/<run id>/report/`.

Default-book results (run 31a32519f30491a4, month-24 holdout 17,467 applicants, 1,577 bad, `data_owner` regime), reported as they came out:

- Vendor AUC 0.797, scorecard 0.746, lift +0.052 (+0.043 to +0.060). Vendor leads in 29 of 32 groups; the scorecard has caught up in Central Visayas, Eastern Visayas (sparse) and Northern Mindanao; no group has the challenger ahead. Thin files: lift +0.057 (6,210 applicants, 584 bad); thick: +0.046 (11,257, 993 bad).
- Phased switch at cutoff 0.10: approval rate 75.97% for the vendor; a full switch gives 82.3% (+6.3 points) and expected loss +58.6%. The same direction (approves more, loses more) at 0.075 and 0.117.
- At 80% approval: vendor 4.82% bad, scorecard 5.83% (141 more defaults, expected loss +24.5%). Swap-ins 1,116 at 20.5% bad; swap-outs 1,116 at 7.9%. Test cell: 717 accounts, 21.8% bad (95% interval 18.9% to 24.9%).

## Checks

- R1: pass
- R2: pass
- R3: pass
- R4: pass
- R5: pass
- R6: pass
- R7: pass
- R8: pass
- R9: pass
- Integration: pass
- Regression: pass
- Completeness: pass

Check tests, from `docs/choices/feature-005.md`:

- R1: only the five named parquet files are opened; no vendor, ledger or Feature 003 scores reference in the package (`tests/unit/test_report_inputs.py`).
- R2: lift against sklearn, verdict words, group sizes and bad counts add to the holdout, sparse flag, thin cut at 6 (`tests/unit/test_report_lift.py`).
- R3: hand-checked phased-switch rows, p=0 and p=1 limits, nested subsets (`tests/unit/test_report_switch.py`).
- R4, R5: hand-checked swap sets, equal swap-in and swap-out sizes, test-cell Wilson interval (`tests/unit/test_report_swap.py`).
- R6: exact approval, 60% loss-given-default, defaults avoided and loss change including a worse challenger (`tests/unit/test_report_equal_rate.py`).
- R7: summary states simulated and synthetic, 60% assumption, no "beat" claim, negative lift kept (`tests/unit/test_report_summary.py`).
- R8: two subprocess runs with different hash seeds give byte-equal files (`tests/evals/test_report_repeat.py`).
- R9, Integration, Completeness: default command writes the six files and finishes within 600 s (`tests/integration/test_cli_run.py`, 209 s in the final timed run).
- Golden: `tests/fixtures/golden/report_2000.json` (`tests/unit/test_report_golden.py`), changelog line added.

`verify_checks.py`: pass. Output: `Locked checks verified (5 file(s)).`

## Test run

Command: `python -m pytest` from the repo root, `PYTHONPATH=<worktree>/src` (the editable install points at the main checkout).

```text
FAILED tests/unit/test_models_boundary.py::test_golden_script_stops_at_from_panel
1 failed, 249 passed in 809.97s (0:13:29)
```

The one failure is environmental (see Failure). After normalising the line endings, `tests/unit/test_models_boundary.py` gave `6 passed in 16.66s` and `tests/integration` gave `1 passed in 209.27s`. All other 249 tests passed in the full run.

## Failure

`tests/fixtures/golden/panel.json` had CRLF line endings in the working copy from the local `core.autocrlf=true` setting, which changed its hash in `test_golden_script_stops_at_from_panel`. Same issue as Feature 004. The working copy was normalised to LF; git shows no content change and nothing about it is committed. No test was changed.

Failure type: environment.

## What changed

- New: `src/scorecheck/report/`, `tests/support/report.py`, `tests/unit/test_report_{inputs,lift,switch,swap,equal_rate,summary,golden}.py`, `tests/evals/test_report_repeat.py`, `tests/fixtures/golden/report_2000.json`, `results/feature-005/`.
- Edited: `src/scorecheck/cli.py`, `tests/conftest.py` (`report_2000` fixture), `tests/integration/test_cli_run.py`, `tests/fixtures/golden/CHANGELOG.md`, `docs/choices/feature-005.md` (change log), `features.md` (Feature 005 Complete), project-context `references/project.md` (identical in `.claude/skills` and `.cursor/skills`).

## Why kept or undone

Every locked check has a passing test, `verify_checks.py` exits 0, and no earlier test broke. Kept.

## Lesson

On this machine `core.autocrlf` turns `panel.json` to CRLF on checkout; the golden-script test then fails for a reason unrelated to the code. Not a program.md rule candidate; an environment note.

## Completeness

A person runs `python -m scorecheck`. After the experiment stage the `report` stage writes `data/experiment/<run id>/report/` with `summary.md` and the five CSVs, and the default-book copy is in `results/feature-005/`. From them one can read where the vendor still leads (29 of 32 groups), where the scorecard has caught up (three regions), what a phased switch costs (more approvals and more expected loss at every share and cutoff), and the bad rate and loss at an equal approval rate. The CLI still prints only the banner and the six stage names. Verified by running the default command in the integration test.
