# feature-001 — round 001

Status: kept

## Attempt

First build of the synthetic behavioural panel, in seven commits on `feature/001-panel`, each pushed before the next began:

1. `2df14d2` packaging (`pyproject.toml`, `requirements.txt` ending in `-e .`), `config.py`, `logical_hash.py`
2. `37a2396` `schema.py` (the only column list), `rundir.py` (`run_id(seed, n_households)`, staged run writes), `_streams.py` (named RNG streams)
3. `3b1dcdc` `panel.generate`: population, `PersonMonthGrid`, `Exogenous` draws, `Traits` with override replacement, absorbing default, behaviour
4. `f3ddb4b` distribution and driver tests at 2,000 households, shared with the advisory eval suite
5. `d7531f3` `panel.read_at_origination` returning `OriginationView`, and `features.from_panel`
6. `74619dd` `python -m scorecheck`, plus `explain.draft`, which raises and is never called
7. `cb25a6d` golden fixture at 250 households, `README.md`, and test commands in `docs/testing-standards.md`

## Checks

- B1 to B6, config: pass
- B7 to B9, run artifact: pass
- B10 to B15, detail tables: pass
- B16 to B20, ground truth: pass
- B21 to B24, Philippine distributions: pass
- B25 to B30, drivers: pass
- B48 to B50, driver weights: pass
- B51 and B52, trait overrides: pass
- B31 to B39, `application_features`: pass
- B40, consumer scope: pass
- B41 to B43, reproducibility: pass
- B44, golden fixture: pass
- B45 to B47, CLI: pass
- Coverage of `scorecheck.panel` and `scorecheck.features` under the unit suite is at least 80%: pass, 98%
- Integration, `python -m scorecheck` calls `panel.generate` then `features.from_panel` with data root `data/processed`: pass
- Integration, `README.md` states both commands and both banners: pass
- Regression: none applies
- Completeness: pass, observed by hand as described below

`verify_checks.py`: pass, before product code and again before this write-up.

## Test run

Command: `python -m pytest -rA -q` from the repo root, in a venv built with `pip install -r requirements.txt` (Python 3.12.9, numpy 2.5.4, pandas 3.1.0, pyarrow 26.0.0, pytest 9.1.1).

```text
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[prepaid_share]
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[sims_per_person]
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[electricity_state_shares]
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[shared_account_counts]
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[driver_signs]
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[default_class_counts]
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[ability_rank_residual]
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[willingness_rank_residual]
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[vendor_signal_rank_residual]
PASSED tests/evals/test_panel_distributions.py::test_panel_eval[calendar_split]
PASSED tests/integration/test_cli_run.py::test_cli_default_run
PASSED tests/unit/test_cli.py::test_scale_flag
PASSED tests/unit/test_cli.py::test_bad_scale_writes_nothing[huge]
PASSED tests/unit/test_cli.py::test_bad_scale_writes_nothing[DEFAULT]
PASSED tests/unit/test_cli.py::test_bad_scale_writes_nothing[Full]
PASSED tests/unit/test_cli.py::test_bad_scale_writes_nothing[]
PASSED tests/unit/test_cli.py::test_bad_scale_writes_nothing[50000]
PASSED tests/unit/test_cli.py::test_missing_scale_value_exits_nonzero
PASSED tests/unit/test_cli.py::test_draft_raises
PASSED tests/unit/test_cli.py::test_main_prints_banner_then_stages
PASSED tests/unit/test_config.py::test_scale_constants
PASSED tests/unit/test_config.py::test_banner_text
PASSED tests/unit/test_config.py::test_multiplier_sources
PASSED tests/unit/test_config.py::test_sourced_rejects_unknown_label
PASSED tests/unit/test_config.py::test_prepaid_config
PASSED tests/unit/test_config.py::test_remittance_config
PASSED tests/unit/test_config.py::test_disconnection_config
PASSED tests/unit/test_config.py::test_driver_weights_nonzero_in_config
PASSED tests/unit/test_config.py::test_scale_name
PASSED tests/unit/test_features.py::test_feature_columns
PASSED tests/unit/test_features.py::test_features_file_matches_return
PASSED tests/unit/test_features.py::test_labels_at_origination
PASSED tests/unit/test_features.py::test_alt_data_recomputed
PASSED tests/unit/test_features.py::test_post_origination_invariance
PASSED tests/unit/test_features.py::test_vendor_columns_null
PASSED tests/unit/test_features.py::test_detail_ties
PASSED tests/unit/test_features.py::test_core_columns
PASSED tests/unit/test_features.py::test_no_ground_truth_leak
PASSED tests/unit/test_golden_panel.py::test_golden_panel
PASSED tests/unit/test_ground_truth.py::test_ground_truth_columns
PASSED tests/unit/test_ground_truth.py::test_ground_truth_grain
PASSED tests/unit/test_ground_truth.py::test_shock_columns
PASSED tests/unit/test_ground_truth.py::test_no_shock_before_origination
PASSED tests/unit/test_ground_truth.py::test_true_default_absorbing
PASSED tests/unit/test_logical_hash.py::test_worked_example_bytes_and_digest
PASSED tests/unit/test_logical_hash.py::test_worked_example_any_order
PASSED tests/unit/test_logical_hash.py::test_negative_zero_and_quotes
PASSED tests/unit/test_logical_hash.py::test_no_digest_for_bad_int_columns[float-id]
PASSED tests/unit/test_logical_hash.py::test_no_digest_for_bad_int_columns[null-id]
PASSED tests/unit/test_logical_hash.py::test_no_digest_for_bad_int_columns[non-whole-int-column]
PASSED tests/unit/test_logical_hash.py::test_no_digest_for_bad_int_columns[null-int-column]
PASSED tests/unit/test_panel_distributions.py::test_prepaid_share
PASSED tests/unit/test_panel_distributions.py::test_sims_per_person
PASSED tests/unit/test_panel_distributions.py::test_electricity_state_shares
PASSED tests/unit/test_panel_distributions.py::test_shared_account_counts
PASSED tests/unit/test_panel_drivers.py::test_driver_signs
PASSED tests/unit/test_panel_drivers.py::test_default_class_counts
PASSED tests/unit/test_panel_drivers.py::test_ability_rank_residual
PASSED tests/unit/test_panel_drivers.py::test_willingness_rank_residual
PASSED tests/unit/test_panel_drivers.py::test_vendor_signal_rank_residual
PASSED tests/unit/test_panel_drivers.py::test_calendar_split
PASSED tests/unit/test_panel_drivers.py::test_driver_weights_nonzero
PASSED tests/unit/test_panel_drivers.py::test_zero_willingness_weight_changes_default
PASSED tests/unit/test_panel_drivers.py::test_zero_ability_weight_changes_default
PASSED tests/unit/test_panel_drivers.py::test_willingness_override_changes_default
PASSED tests/unit/test_panel_drivers.py::test_ability_override_changes_default
PASSED tests/unit/test_panel_schema.py::test_detail_columns
PASSED tests/unit/test_panel_schema.py::test_unique_keys
PASSED tests/unit/test_panel_schema.py::test_foreign_keys
PASSED tests/unit/test_panel_schema.py::test_origination_month_range
PASSED tests/unit/test_panel_schema.py::test_month_behaviour_grain
PASSED tests/unit/test_panel_schema.py::test_electricity_states
PASSED tests/unit/test_reproducibility.py::test_same_seed_same_hash
PASSED tests/unit/test_reproducibility.py::test_second_seed_differs
PASSED tests/unit/test_reproducibility.py::test_hash_is_logical[person]
PASSED tests/unit/test_reproducibility.py::test_hash_is_logical[ground_truth]
PASSED tests/unit/test_reproducibility.py::test_hash_is_logical[month_behaviour]
PASSED tests/unit/test_reproducibility.py::test_hash_is_logical[application_features]
PASSED tests/unit/test_reproducibility.py::test_worked_example_digest
PASSED tests/unit/test_reproducibility.py::test_bad_int_cast_produces_no_digest
PASSED tests/unit/test_run_artifact.py::test_run_id
PASSED tests/unit/test_run_artifact.py::test_generate_writes_only_panel
PASSED tests/unit/test_run_artifact.py::test_generate_twice_into_same_directory
PASSED tests/unit/test_run_artifact.py::test_run_config
PASSED tests/unit/test_scope.py::test_no_firm_entities
PASSED tests/unit/test_structure.py::test_schema_kinds_match_hash_casts[household]
PASSED tests/unit/test_structure.py::test_schema_kinds_match_hash_casts[person]
PASSED tests/unit/test_structure.py::test_schema_kinds_match_hash_casts[sim]
PASSED tests/unit/test_structure.py::test_schema_kinds_match_hash_casts[electricity_account]
PASSED tests/unit/test_structure.py::test_schema_kinds_match_hash_casts[ewallet_account]
PASSED tests/unit/test_structure.py::test_schema_kinds_match_hash_casts[month_behaviour]
PASSED tests/unit/test_structure.py::test_schema_kinds_match_hash_casts[ground_truth]
PASSED tests/unit/test_structure.py::test_schema_kinds_match_hash_casts[application_features]
PASSED tests/unit/test_structure.py::test_generators_only_built_in_streams
PASSED tests/unit/test_structure.py::test_stream_is_reproducible_and_independent_of_order
PASSED tests/unit/test_structure.py::test_stream_name_reuse_raises
PASSED tests/unit/test_structure.py::test_conform_rejects_wrong_columns
PASSED tests/unit/test_structure.py::test_conform_casts_whole_floats_and_rejects_fractions
PASSED tests/unit/test_structure.py::test_write_run_replaces_existing_directory
99 passed in 67.17s (0:01:07)
```

Command: `python -m pytest tests/unit --cov=scorecheck.panel --cov=scorecheck.features --cov-report=term -q`

```text
Name                                      Stmts   Miss  Cover
-------------------------------------------------------------
src\scorecheck\features\__init__.py          10      0   100%
src\scorecheck\features\_application.py      35      0   100%
src\scorecheck\panel\__init__.py             36      4    89%
src\scorecheck\panel\_behaviour.py           44      0   100%
src\scorecheck\panel\_grid.py                39      1    97%
src\scorecheck\panel\_params.py              16      0   100%
src\scorecheck\panel\_population.py          52      0   100%
src\scorecheck\panel\_truth.py               36      0   100%
src\scorecheck\panel\_view.py                28      1    96%
-------------------------------------------------------------
TOTAL                                       296      6    98%
88 passed in 65.23s (0:01:05)
```

The golden test and the logical-hash tests also pass under the machine's global Python, which has numpy 1.26.4 and pandas 2.1.3. Both stacks give the same eight golden hashes.

## Failure

None in the final run. These are the failures observed on the way.

- Before each unit's product code, its tests failed on the missing module (`scorecheck.config`, `scorecheck.logical_hash`, `scorecheck.rundir`, `scorecheck.panel`, `scorecheck.features`, `scorecheck.cli`). The golden test failed with "golden fixture missing" and did not skip.
- Unit 4's tests could not fail first. The generator that B21 to B30 and B48 to B52 measure landed in unit 3, so its tests came after the code. As a substitute, I fed mutated tuning to the same assertion functions. Removing the remittance calendar from ability failed B30. Reversing the vendor-signal weight failed B29. A default intercept of -12 failed B26. Zeroing the late-payment share failed B23.
- I mutated the time cut to `month <= origination_month` to check the leak test. B34 and B35 both failed, and I reverted the cut before committing.
- The two locked `test_panel_distributions.py` files share a basename, and pytest's default import mode refused to collect both. `pyproject.toml` now sets `--import-mode=importlib`.

Failure type: implementation

## What changed

- `src/scorecheck/` holds `config.py`, `logical_hash.py`, `schema.py`, `rundir.py`, `_streams.py`, `cli.py`, `__main__.py`, the `panel/` package, the `features/` package, and the `explain/` stub
- `tests/` holds the unit, eval, and integration suites, plus `tests/support/` for shared runs and assertions, and `tests/fixtures/golden/` with `panel.json` and `CHANGELOG.md`
- `scripts/write_golden_panel.py` is new. The three locked check scripts are untouched.
- `README.md`, `docs/testing-standards.md`, `pyproject.toml`, `requirements.txt`, and `.gitignore`, which now ignores `data/processed/`, `.venv/`, and build and test caches

Behaviour: `python -m scorecheck` prints the default banner, writes `data/processed/31a32519f30491a4/` with the eight Parquet tables and `run_config.json`, and then prints the six stage names. At 50,000 households, 10.4% of persons are in default at their origination month (9,122 of 87,337). The 2,000-household test run gives 10.6%.

## Why kept or undone

Every locked check has a passing test seen in this run. The user-facing command was run from the repo root and wrote the run directory. No earlier behaviour existed to regress.

Completeness was observed by hand. In the venv built from `pip install -r requirements.txt`, I ran `python -m scorecheck` from the repo root with no `data/` directory present. It exited 0. The first stdout line was the default banner, followed by `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`. `data/processed/31a32519f30491a4/` held all eight Parquet tables and `run_config.json`. `python -m scorecheck --scale bogus` exited 2. I deleted the generated `data/` directory afterwards.

## Lesson

When one build unit's product code is measured by a later unit's checks, those checks cannot fail first. Order the units so that each unit's checks cover every line of product code it adds. For example, land the generator's distribution and driver logic in the same unit as the B21 to B30 tests. Candidate rule only, pending human confirmation.

Two notes for the human, outside this feature's scope:

- `checks/approved/feature-001.md` still reads `Status: draft` although it is locked and verified. I did not edit it.
- The project half of `docs/testing-standards.md` says eval cases live in `tests/evals/*.json`, but the locked check names `tests/evals/test_panel_distributions.py`. I followed the check.
