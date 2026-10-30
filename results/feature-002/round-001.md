# feature-002 — round 001

Status: kept

## Attempt

Tests were written against `publish`, `score`, and the ledger path before `scorecheck.vendor` existed. That run failed because the module was missing.

```text
FAILED tests/unit/test_vendor_boundary.py::test_public_surface - ImportError: cannot import name 'vendor' from 'scorecheck'
FAILED tests/unit/test_vendor_publish.py::test_reason_rank - ModuleNotFoundError: No module named 'scorecheck.vendor'
FAILED tests/unit/test_cli.py::test_command_order - ImportError: cannot import name 'vendor' from 'scorecheck'
3 failed in 0.10s
```

The package, the CLI call, and the `lightgbm==4.7.0` pin then went in together. `COLUMN_GROUPS` is the only column-to-token map. `publish` reads it at call time. One-class rows store the observed rate and `credit_stress`, `capacity`, `thin_file`. Two-class rows fit LightGBM and rank `pred_contrib` after the bias column is dropped. The ledger is `ledger.parquet` and `bind.json` beside the panel, swapped in with the same directory rename as `write_run`.

## Checks

- V1: pass
- V2: pass
- V3: pass
- V4: pass
- V5: pass
- V6: pass
- V7: pass
- V8: pass
- V9: pass
- V10: pass
- V11: pass
- V12: pass
- V13: pass
- V14: pass
- V15: pass
- V16: pass
- Integration: pass
- Regression: pass
- Completeness: pass

`verify_checks.py`: pass

```text
Locked checks verified (2 file(s)).
```

## Test run

Command: `python -m pytest tests/unit --cov=scorecheck.panel --cov=scorecheck.features --cov=scorecheck.vendor --cov-report=term-missing -q`

```text
........................................................................ [ 66%]
.....................................                                    [100%]
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.12.9-final-0 _______________

Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
src\scorecheck\features\__init__.py          10      0   100%
src\scorecheck\features\_application.py      47      0   100%
src\scorecheck\panel\__init__.py             39      5    87%   31, 33, 36, 82, 84
src\scorecheck\panel\_behaviour.py           44      0   100%
src\scorecheck\panel\_grid.py                39      1    97%   55
src\scorecheck\panel\_params.py              16      0   100%
src\scorecheck\panel\_population.py          52      0   100%
src\scorecheck\panel\_truth.py               37      0   100%
src\scorecheck\panel\_view.py                28      1    96%   41
src\scorecheck\vendor\__init__.py            60      0   100%
src\scorecheck\vendor\_private.py            96      0   100%
-----------------------------------------------------------------------
TOTAL                                       468      7    99%
109 passed in 71.33s (0:01:11)
```

Command: `python -m pytest tests/integration/test_cli_run.py::test_cli_default_run tests/evals/test_vendor_score.py --tb=short -q`

```text
..                                                                       [100%]
2 passed in 24.29s
```

`scorecheck.vendor` line coverage under the unit suite is 100% on both modules. The gate is 80%. `scorecheck.panel` and `scorecheck.features` stayed above 80% on that same command.

The 50,000-household command exited 0. Stdout was the default banner and the six stage names. `data/processed` had one child, `31a32519f30491a4`. `data/vendor/31a32519f30491a4/` held `ledger.parquet` and `bind.json`. `external_score_1`, `external_score_2`, and `external_score_3` were null. `vendor.score` on an `application_id` from that ledger returned a probability in `[0, 1]` and three distinct `ReasonCode` values. `household.parquet` had 50,000 rows.

`pytest-cov` was not installed in this interpreter. `pip install pytest-cov` made the coverage command runnable. `lightgbm==4.7.0` was installed the same way. `scorecheck` is installed editable.

## Failure

none

Failure type: none

## What changed

- `src/scorecheck/vendor/__init__.py` publishes and scores. `COLUMN_GROUPS` and `rank_reasons` stay off `__all__`.
- `src/scorecheck/vendor/_private.py` builds the training table, fits LightGBM, and renames the ledger into place.
- `src/scorecheck/cli.py` calls `vendor.publish` after `features.from_panel`.
- `pyproject.toml` and `requirements.txt` pin `lightgbm==4.7.0`.
- Unit, integration, and eval tests named in the locked file.
- `tests/support/vendor.py` holds the shared run copy, the two-class label rewrite, the ledger hash, and the LightGBM spy.
- `features.md` marks Feature 002 complete.
- `generate_run` and `scripts/write_golden_panel.py` still stop at `from_panel`. The panel golden was left as Feature 001 stored it.

## Why kept or undone

The missing-module failures are gone. The locked unit tests, the coverage command, and the 50,000-household command passed. The earlier panel and feature tests in that unit suite still passed.

## Lesson

none
