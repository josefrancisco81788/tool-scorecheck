# Checks for feature-002, the black-box vendor score API

Status: draft

Feature: feature-002

The ledger contract is JOS-24. The four training answers are the JOS-83 reply `527ed809-3466-4401-9c3d-ae40548db9b6`. Where `docs/design.md` says the synthetic vendor score is written back into `external_score_1`, or that vendor training includes `external_score_*` and behavioural correlates of `vendor_signal`, these checks follow JOS-24 and that reply. `external_score_*` stay null. Origination-month `vendor_signal` is the only private input.

The LightGBM seed integer is one `integers(0, 2**31)` draw. LightGBM stores that seed as a 32-bit signed integer, so the draw is the non-negative range below `2**31`. A missing origination row, and a group-map mismatch, each raise `scorecheck.schema.SchemaError`. The same class is what `read_at_origination` raises when a person has no single origination row. Two-class reason codes are the top three groups by the sum of absolute LightGBM contributions.

## Definitions

A vendor run is `panel.generate(seed, n_households, data_dir)` followed by `features.from_panel` on the directory it wrote. Unit checks use `scorecheck.config.SEED` and 300 households unless a check names another size. No test generates 200,000 households. The integration test is the only 50,000-household run.

The run id is the first 16 hex characters of the SHA-256 of the UTF-8 string `"{seed}|{n_households}|24"`. For seed `20261024` and 50,000 households the run id is `31a32519f30491a4`. For seed `20261024` and 200 households the run id is `6e6c82611fa89cf4`.

The ledger path is `run_dir.parent.with_name("vendor") / run_dir.name`. The default command's ledger path is `data/vendor/31a32519f30491a4/`.

The ledger directory holds exactly two files, `ledger.parquet` and `bind.json`. `ledger.parquet` has exactly these columns, one row per application, sorted by `application_id` ascending.

- `application_id`, int64, zero duplicates
- `probability`, float64, every value finite and inside the closed interval from 0 to 1
- `reason_1`, `reason_2`, `reason_3`, strings

`bind.json` parses as one JSON object whose only key is `features_hash`. The value is `scorecheck.logical_hash.logical_hash` of the `application_features` table at publish time. `score` reads that table and computes the same hash again. A difference raises `StaleLedger`. Parquet byte equality is not the bind. `logical_hash` already renders a null `external_score_*` cell as `<NA>`.

The ledger hash is the panel logical-hash procedure applied to `ledger.parquet`, with one added cast. `application_id` is an id column. `probability` is float64. `reason_1`, `reason_2`, and `reason_3` are UTF-8 strings. Parquet byte equality is not required.

An origination row is the `ground_truth` row whose `person_id` equals that application row's `person_id` and whose `month` equals that person's `origination_month`. There is one such row per person on a vendor run that has not been damaged.

The origination read keeps `person_id`, `month`, and `vendor_signal` only, and only those origination rows, joined on `person_id`. `ability`, `willingness`, `region_month_shock`, `post_origination_shock`, and `true_default` stay out of the fit. `vendor_signal` and `private_factor` are not columns of the ledger or of `application_features`.

Fit columns are the `application_features` columns except `application_id`, `person_id`, `age_years`, `gender`, `education`, `marital_status`, `region`, `external_score_1`, `external_score_2`, `external_score_3`, `default_label`, and `label_observed`, plus the derived column `private_factor`. `private_factor` equals that row's origination `vendor_signal`, exact float64 equality, absolute tolerance 0. Training row i is the application row with the i-th smallest `application_id`. The label is `default_label` in that same order, not `true_default`.

`scorecheck.vendor.COLUMN_GROUPS` is the group map. `publish` reads it at call time. It is not in `__all__`. Its keys are exactly the fit columns. Its values are the tokens below.

- `utilization`, `open_credit_count`, `delinquency_count_30`, `delinquency_count_60`, `delinquency_count_90`, `on_time_rate` map to `credit_stress`
- `income`, `dependents`, `credit_amount`, `installment_to_income`, `payment_to_obligation_ratio` map to `capacity`
- `history_months` maps to `thin_file`
- `sim_count`, `prepaid_flag`, `electricity_late_rate`, `electricity_disconnect_count`, `remittance_inflow_mean`, `ewallet_net_flow_mean`, `shared_account_flag` map to `alt_activity`
- `private_factor` maps to `private_factor`

`application_profile` is not a key, not a value, and not a `ReasonCode` member.

A one-class feature file has one distinct `default_label`. A two-class feature file is a vendor run whose `default_label` has been overwritten so the lower half of `application_id` values are 0 and the upper half are 1. The natural 200-household draw is not required to be one-class.

The LightGBM seed integer is `int(Streams(seed, "vendor")("lightgbm").integers(0, 2**31))`. `seed` is the integer `seed` in that run's `run_config.json`. The call has no `size` argument, so it returns one integer. The lower bound is included and `2**31` is excluded. That stream is asked for no other integer. The same integer is `seed`, `bagging_seed`, `feature_fraction_seed`, and `data_random_seed`.

`scorecheck.vendor.rank_reasons(contributions)` is not in `__all__`. `contributions` maps every fit-column name to one float. A missing or extra name raises `SchemaError` before a code is returned. The weight of a group is the sum of the absolute values of its columns. The three codes are the three groups with the largest weights. A tie breaks by this order: `credit_stress`, `capacity`, `thin_file`, `alt_activity`, `private_factor`. An all-zero mapping therefore returns `credit_stress`, `capacity`, `thin_file`. A mapping with `income` 3, `history_months` 3, `private_factor` 2, `utilization` 1, `sim_count` 0.5, and every other fit column 0 returns `capacity`, `thin_file`, `private_factor`.

A two-class `publish` calls `pred_contrib` on the training rows in `application_id` order. The matrix has one column per fit column, in training-matrix order, plus a final bias column. The bias column is dropped. Each remaining row is passed to `rank_reasons`. One-class `publish` does not call `rank_reasons` or `pred_contrib`.

## Behavior

### Command

- [ ] V1. `python -m scorecheck` calls `panel.generate`, then `features.from_panel`, then `vendor.publish`, in that order, once each. `explain.draft` is not called. Printing the stage name `explain` is not a call to `explain.draft`. `publish` writes nothing to stdout and nothing to stderr on a one-class publish and on a two-class publish. After the scale banner, stdout is the six stage names `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`, one per line, and nothing else. `test_main_prints_banner_then_stages` monkeypatches the default scale to 200 households, requires exit 0, and requires stdout to equal the default banner plus those six names. That test does not have to be the one-class draw.

### Ledger path

- [ ] V2. After `publish(run_dir)`, the ledger directory is `run_dir.parent.with_name("vendor") / run_dir.name` and holds exactly `ledger.parquet` and `bind.json`. The default command writes `data/vendor/31a32519f30491a4/` and leaves exactly one child of `data/processed`, the run id `31a32519f30491a4`. The 200-household command writes `data/vendor/6e6c82611fa89cf4/` and leaves exactly one child of `data/processed`.

### Writers

- [ ] V3. `publish` is the only writer of the ledger. `score` is the only reader of the ledger. `panel.generate` still writes only `household.parquet`, `person.parquet`, `sim.parquet`, `electricity_account.parquet`, `ewallet_account.parquet`, `month_behaviour.parquet`, `ground_truth.parquet`, and `run_config.json`. `from_panel` still adds only `application_features.parquet`. After `publish`, the run directory's file set is unchanged. The ledger files are not inside the run directory.

### External scores

- [ ] V4. After `from_panel`, after `publish`, and after `python -m scorecheck`, `external_score_1`, `external_score_2`, and `external_score_3` are null on every `application_features` row. Those three names are absent from the training columns on a two-class publish. Filling all three with `1.0` before `publish` leaves the training matrix unchanged, absolute tolerance 0, relative to the same run with the three columns left null.

### Origination signal

- [ ] V5. The private input is origination-month `vendor_signal` only. The read columns are `person_id`, `month`, and `vendor_signal`. The kept rows are those whose `month` equals that person's `origination_month`, joined on `person_id`. On a two-class publish, `private_factor` equals that origination value, absolute tolerance 0. Adding `1000.0` to `vendor_signal` on rows whose `month` is not `origination_month` leaves `private_factor` unchanged, absolute tolerance 0. Adding `1000.0` to `vendor_signal` on the origination rows adds `1000.0` to `private_factor`, absolute tolerance 0. Adding `1000.0` to `ability` and to `willingness`, flipping `region_month_shock` and `post_origination_shock`, and setting `true_default` to `1 - true_default`, all leave the training matrix and the training label unchanged when `default_label` is left unchanged, absolute tolerance 0. Overwriting `default_label` changes the training label to the new `default_label`. The ledger columns and the `application_features` columns do not include `vendor_signal` or `private_factor`. The logical hash of `application_features` after a successful `publish` equals the hash from before that `publish`. If any `application_features` person has no origination row, `publish` raises `scorecheck.schema.SchemaError` before it writes. The ledger path does not exist after that raise, when it did not exist before, and the logical hash of `application_features` is unchanged. `ability` and the rest of `ground_truth` are not training columns.

### Columns that leave the matrix

- [ ] V6. On a two-class publish, `age_years`, `gender`, `education`, `marital_status`, and `region` are absent from the training columns. They remain columns of `application_features`, and a successful `publish` does not change that file's logical hash. On a two-class publish, adding `1000` to `age_years`, and replacing `gender`, `education`, `marital_status`, and `region` with a different allowed value on every row, leaves the training matrix unchanged, absolute tolerance 0. `application_profile` is not a training column, not a ledger token, and not a `ReasonCode` member. `ReasonCode("application_profile")` raises. Feature 003 is the later drop of the same five columns from the challenger matrix. This feature does not fit a challenger.

### Group map

- [ ] V7. On a two-class publish, the training column names equal the keys of `COLUMN_GROUPS`, and `COLUMN_GROUPS` equals the map in Definitions. If those keys differ from the fit columns, `publish` raises `scorecheck.schema.SchemaError` before it writes. The test drops the `private_factor` key from `COLUMN_GROUPS` and calls `publish`. The call raises `SchemaError`, the ledger path is absent, and the logical hash of `application_features` is unchanged.

### Join key

- [ ] V8. `person_id` is the join key for the origination read. `score` looks up `application_id`. The test adds `1000000` to every `application_id`, then publishes. For a `person_id` that is absent from the rewritten `application_id` column, `score(run_dir, person_id)` raises `UnknownApplicant`. `score(run_dir, person_id + 1000000)` returns the ledger row whose `application_id` is that sum. On a two-class publish of that rewritten file, adding `1000.0` to origination `vendor_signal` for one `person_id` adds `1000.0` to `private_factor` on the training row with that `person_id`, absolute tolerance 0.

### One-class publish

- [ ] V9. If `default_label` has one distinct value, `publish` does not call `lightgbm.train` and does not call `lightgbm.Dataset`. Every ledger row has `probability` equal to that observed rate, `0.0` when the label is 0 and `1.0` when the label is 1, absolute tolerance 0. `reason_1` is `credit_stress`, `reason_2` is `capacity`, and `reason_3` is `thin_file`, in that order, on every row. The write uses the same directory rename as a two-class publish. `publish` prints nothing and does not raise. `score` returns that stored decision. The 200-household CLI test does not have to build this draw. A unit test does.

### LightGBM

- [ ] V10. `pyproject.toml` and `requirements.txt` each pin `lightgbm==4.7.0`. `importlib.metadata.version("lightgbm")` equals `4.7.0`. A two-class `publish` calls `lightgbm.train` once. The params mapping has exactly these keys and values. `objective` is `binary`. `deterministic` is boolean `True`. `force_row_wise` is boolean `True`. `device_type` is `cpu`. `num_threads` is the integer `1`. `feature_fraction` compares equal to 1. `bagging_fraction` compares equal to 1. `bagging_freq` is the integer `0`. `num_leaves` is the integer `15`. `learning_rate` compares equal to 0.1. `verbose` is the integer `-1`. `seed`, `bagging_seed`, `feature_fraction_seed`, and `data_random_seed` are the LightGBM seed integer from Definitions. `num_boost_round` is the integer `40` on that call. The call has no early-stopping argument and no early-stopping callback. Two two-class publishes with the same `run_config.json` seed and different household counts, 200 and 300, pass equal params, including the four seeds. The seed draw uses `Streams`. It does not call `default_rng`, `RandomState`, `np.random.seed`, or `SeedSequence` outside `src/scorecheck/_streams.py`.

### Same-machine hash

- [ ] V11. Two publishes of the same run, in two subprocesses on one machine, produce the same ledger hash. The check runs that pair for a one-class run and for a two-class run. Cross-machine equality is not this check. V11 does not prove the origination cut. V5 does.

### Score

- [ ] V12. `vendor.score(run_dir, application_id)` returns a `VendorDecision`. The unpacking `probability, reason_1, reason_2, reason_3 = vendor.score(run_dir, application_id)` yields a float in the closed interval from 0 to 1 and three `ReasonCode` values. The three codes are distinct. Each code's value is one of `credit_stress`, `capacity`, `thin_file`, `alt_activity`, and `private_factor`. On a two-class publish, those three codes equal `rank_reasons` of that row's `pred_contrib` values after the bias column is dropped. The four unpacked values equal the ledger row for that `application_id`. `score` does not call `lightgbm.train` or `Booster.predict`. `scorecheck.vendor.__all__` is exactly `publish`, `score`, `VendorDecision`, `ReasonCode`, `LedgerMissing`, `StaleLedger`, and `UnknownApplicant`. `rank_reasons` and `COLUMN_GROUPS` are absent from `__all__`. `ReasonCode` has exactly those five token values. `rank_reasons` on the all-zero mapping returns `credit_stress`, `capacity`, `thin_file`. `rank_reasons` on the named mapping in Definitions returns `capacity`, `thin_file`, `private_factor`.

### Ledger errors

- [ ] V13. `score` on a run that has never been published raises `LedgerMissing` and does not create the ledger directory. After a successful `publish`, deleting `ledger.parquet` or deleting `bind.json` raises `LedgerMissing`. `score(run_dir, max(application_id) + 1)` raises `UnknownApplicant` and leaves both ledger files in place. Changing `income` by `1.0` on every application row, and writing `application_features.parquet` back, makes `score` raise `StaleLedger` and return no probability. `LedgerMissing`, `StaleLedger`, and `UnknownApplicant` are distinct subclasses of `Exception`, and none is a subclass of another.

### Swap, booster, and imports

- [ ] V14. `publish` writes `ledger.parquet` and `bind.json` into a staging directory and puts that directory on the ledger path with one `os.replace`. After a successful `publish`, the ledger path holds exactly those two files, and the staging directory is gone. If that `os.replace` raises, the exception propagates, any previous ledger's file bytes are unchanged, and the staging directory is gone. The booster is a local in `publish`. It is not stored. The ledger directory has no model file. `scorecheck.vendor` has no attribute `Booster` or `booster`, and `__all__` does not export one. A file under `src/`, `tests/`, or `scripts/` whose path is outside `src/scorecheck/vendor/` does not import `scorecheck.vendor._private`.

### Replaced run

- [ ] V15. `score` reads the ledger from disk on each call. On a one-class publish with label 0, `score` returns probability `0.0`. After `income` changes by `1.0` and the feature file is rewritten, `score` raises `StaleLedger` and does not return `0.0`. After the labels are set to 1 and `publish` runs again, `score` returns probability `1.0`. Copying a vendor run of seed `SEED + 1` over the original run directory, so the directory name and the ledger path stay the same, makes `score` raise `StaleLedger`. The probability from the label-0 publish is not returned.

### Golden path

- [ ] V16. `tests/support/runs.py` `generate_run` still stops at `features.from_panel`. After `generate_run`, the ledger path does not exist. A monkeypatch that makes `vendor.publish` raise is not triggered by `generate_run`. `scripts/write_golden_panel.py` contains a call to `features.from_panel` and does not contain `vendor.publish` or `scorecheck.vendor`. The stored panel golden hashes are unchanged. This feature does not add a vendor hash to `tests/fixtures/golden/panel.json`.

## Out of the locked set

Cross-machine ledger equality is not a locked check. The JOS-83 reply cites the LightGBM 4.7 parameter page, `https://lightgbm.readthedocs.io/en/v4.7.0/Parameters.html`. That page says `deterministic=True` stabilises a run for the same data and parameters, and that different systems or different compiled binaries are expected to differ. A stored golden hash of a two-class ledger would freeze one machine's bytes. This draft does not require that file. A later vendor decision fixture, if someone adds one, is a new file with its own changelog line. It is not one of these checks.

Eval output is advisory. It proves no check above.

Feature 003 drops the same five demographic columns from the challenger matrix. Feature 004 names this private channel when it reports the gap. Neither feature is a pass or fail of these checks.

## Executable tests

Every automated test that will prove the checks above, named before any product code exists. The feature builder writes these first and may not weaken them.

Test command: `python -m pytest` from the repo root.

Coverage command: `python -m pytest tests/unit --cov=scorecheck.panel --cov=scorecheck.features --cov=scorecheck.vendor --cov-report=term-missing`

Tests import `scorecheck.cli`. Importing `scorecheck.__main__` runs the default panel, so no test imports it.

| Test | File | What it asserts | Proves check |
|---|---|---|---|
| test_main_prints_banner_then_stages | tests/unit/test_cli.py | Monkeypatch the default scale to 200 households. `cli.main([])` returns 0. Stdout lines equal the default banner plus `vendor`, `models`, `experiment`, `report`, `validate`, `explain`. A monkeypatch that raises from `explain.draft` is not triggered. This draw is not required to be one-class. | V1 |
| test_command_order | tests/unit/test_cli.py | On that same 200-household command, the call order is `panel.generate`, then `features.from_panel`, then `vendor.publish`, once each. | V1 |
| test_publish_is_silent | tests/unit/test_vendor_publish.py | Captured stdout and stderr are empty for one one-class `publish` and one two-class `publish`. | V1 |
| test_ledger_path | tests/unit/test_vendor_publish.py | The ledger path equals `run_dir.parent.with_name("vendor") / run_dir.name` and contains exactly `ledger.parquet` and `bind.json`. The 200-household run id is `6e6c82611fa89cf4`. | V2 |
| test_publish_leaves_run_dir_unchanged | tests/unit/test_vendor_publish.py | The set of file names in the run directory is the same before and after `publish`. The ledger files are not in that set. | V3 |
| test_generate_writes_only_panel | tests/unit/test_run_artifact.py | `panel.generate(SEED, 300, tmp)` writes exactly the seven panel Parquet files and `run_config.json`. | V3 |
| test_external_scores_stay_null | tests/unit/test_vendor_publish.py | After `publish`, the three `external_score_*` columns are null on every row. Their names are absent from the training columns. Filling them with `1.0` leaves the training matrix unchanged, absolute tolerance 0. | V4 |
| test_origination_read | tests/unit/test_vendor_publish.py | `private_factor` equals origination `vendor_signal`, absolute tolerance 0. Adding `1000.0` off the origination month leaves `private_factor` unchanged. Adding `1000.0` on the origination month adds `1000.0`. Edits to `ability`, `willingness`, both shock flags, and `true_default` leave the training matrix and the label unchanged when `default_label` is unchanged. Overwriting `default_label` changes the training label. Deleting one person's origination row makes `publish` raise `scorecheck.schema.SchemaError`, leaves the ledger path absent, and leaves the `application_features` logical hash unchanged. The ledger and `application_features` have no `vendor_signal` or `private_factor` column. | V5 |
| test_demographics_leave_the_matrix | tests/unit/test_vendor_publish.py | On a two-class publish, the five demographic names are absent from the training columns and present on `application_features`. `publish` leaves that file's logical hash unchanged. Adding `1000` to `age_years` and replacing the other four demographics leaves the training matrix unchanged, absolute tolerance 0. `application_profile` is not a training name, not a ledger token, and `ReasonCode("application_profile")` raises. | V6 |
| test_group_map | tests/unit/test_vendor_publish.py | `COLUMN_GROUPS` equals the Definitions map. Training names equal its keys. Dropping the `private_factor` key makes `publish` raise `scorecheck.schema.SchemaError` with the ledger path absent and the feature-file logical hash unchanged. | V7 |
| test_person_id_is_only_the_join_key | tests/unit/test_vendor_publish.py | After adding `1000000` to every `application_id`, `score` on a `person_id` absent from that column raises `UnknownApplicant`, and `score(run_dir, person_id + 1000000)` returns that row. On a two-class publish, adding `1000.0` to one person's origination `vendor_signal` adds `1000.0` to `private_factor` on that person's training row, absolute tolerance 0. | V8 |
| test_one_class_ledger | tests/unit/test_vendor_publish.py | With every `default_label` set to 0, `lightgbm.train` and `lightgbm.Dataset` are not called, every probability is `0.0`, and the tokens are `credit_stress`, `capacity`, `thin_file` in that order. The same holds for label 1 with probability `1.0`. `publish` does not raise and prints nothing. `score` returns the stored row. | V9 |
| test_lightgbm_contract | tests/unit/test_vendor_publish.py | The pin `lightgbm==4.7.0` is in `pyproject.toml` and `requirements.txt`, and the installed version equals `4.7.0`. A two-class publish calls `lightgbm.train` once with the V10 params, `num_boost_round` 40, and no early stopping. The four seeds equal `int(Streams(seed, "vendor")("lightgbm").integers(0, 2**31))`. A 200-household two-class publish and a 300-household two-class publish with the same run seed pass equal params. | V10 |
| test_same_machine_ledger_hash | tests/unit/test_vendor_publish.py | Two subprocess publishes of the same one-class run have equal ledger hashes. Two subprocess publishes of the same two-class run have equal ledger hashes. The hashes use the Definitions procedure. Parquet bytes may differ. | V11 |
| test_score_returns_decision | tests/unit/test_vendor_score.py | Unpacking `score` yields a float in the closed interval from 0 to 1 and three distinct `ReasonCode` values from the five tokens. The four values equal the ledger row. On a two-class publish, the three codes equal `rank_reasons` of that row's `pred_contrib` values after the bias column is dropped. A monkeypatch that raises from `lightgbm.train` and from `Booster.predict` is not triggered by `score`. | V12 |
| test_reason_rank | tests/unit/test_vendor_publish.py | `rank_reasons` on an all-zero fit-column mapping returns `credit_stress`, `capacity`, `thin_file`. The Definitions mapping (`income` 3, `history_months` 3, `private_factor` 2, `utilization` 1, `sim_count` 0.5, every other fit column 0) returns `capacity`, `thin_file`, `private_factor`. A missing fit-column name raises `SchemaError`. | V12 |
| test_public_surface | tests/unit/test_vendor_boundary.py | `__all__` is exactly `publish`, `score`, `VendorDecision`, `ReasonCode`, `LedgerMissing`, `StaleLedger`, and `UnknownApplicant`. `ReasonCode` has exactly the five token values. The module has no `Booster` or `booster` attribute. | V12, V14 |
| test_ledger_errors | tests/unit/test_vendor_score.py | `score` before `publish` raises `LedgerMissing` and does not create the ledger directory. Deleting either ledger file raises `LedgerMissing`. `score(run_dir, max(application_id) + 1)` raises `UnknownApplicant` and both files remain. Adding `1.0` to `income` and rewriting the feature file makes `score` raise `StaleLedger`. The three classes are distinct `Exception` subclasses, and none subclasses another. | V13 |
| test_atomic_swap | tests/unit/test_vendor_publish.py | A successful one-class `publish` calls `os.replace` once, from a staging directory that already holds both ledger files, onto the ledger path. The staging directory is gone. If that `os.replace` raises, the previous ledger's file bytes are unchanged and the staging directory is gone. | V14 |
| test_no_private_import_outside_vendor | tests/unit/test_vendor_boundary.py | No file under `src/`, `tests/`, or `scripts/` outside `src/scorecheck/vendor/` imports `scorecheck.vendor._private`. | V14 |
| test_replaced_run_is_not_served | tests/unit/test_vendor_score.py | A label-0 publish scores `0.0`. Rewriting `income` by `1.0` makes `score` raise `StaleLedger`. A later label-1 publish scores `1.0`. Copying a `SEED + 1` run directory onto the same path makes `score` raise `StaleLedger`. | V15 |
| test_generate_run_stops_at_from_panel | tests/unit/test_vendor_boundary.py | `generate_run` returns without creating the ledger path. A `vendor.publish` monkeypatch that raises is not called. | V16 |
| test_golden_script_stops_at_from_panel | tests/unit/test_vendor_boundary.py | The text of `scripts/write_golden_panel.py` contains `features.from_panel` and does not contain `vendor.publish` or `scorecheck.vendor`. The test does not run the script. | V16 |
| test_cli_default_run | tests/integration/test_cli_run.py | `python -m scorecheck` in an empty working directory, 600-second timeout, exits 0. Stdout lines equal the default banner plus the six stage names and nothing else. `data/processed` has exactly one child, `31a32519f30491a4`. `data/vendor/31a32519f30491a4/` holds exactly `ledger.parquet` and `bind.json`. The run directory holds the seven panel files, `application_features.parquet`, and `run_config.json`, and no other file. The three `external_score_*` columns are null on every row. `household.parquet` has 50,000 rows. | V1, V2, V3, V4, Completeness |
| test_vendor_bounds | tests/evals/test_vendor_score.py | On a 300-household two-class publish, every `score` probability is inside the closed interval from 0 to 1, and the three tokens are distinct members of the five groups. Advisory. It proves no locked check. | none |

Required kinds, per `docs/testing-standards.md` and the project document Testing requirements.

- Unit. The `tests/unit/` rows above. They cover `publish`, `score`, the ledger errors, the absent booster, the origination cut, and null `external_score_*`. `src/scorecheck/vendor/` has at least 80% line coverage under the unit suite. `scorecheck.panel` and `scorecheck.features` stay under that same coverage command. CLI glue stays outside the 80% gate and keeps the 200-household smoke test.
- Golden dataset. Not applicable for a new stored hash. The panel golden stays as Feature 001 left it. A two-class LightGBM ledger hash is not stored, because the LightGBM 4.7 docs say different systems are expected to differ. The one-class ledger is the unit test `test_one_class_ledger`, not a golden file.
- Eval case. `tests/evals/test_vendor_score.py` is a pytest file, not JSON. JSON eval cases belong to Feature 007. This eval is advisory until v1 and proves no locked check.
- Integration. `test_cli_default_run` runs the real default command. No test generates 200,000 households.
- Coverage. `scorecheck.vendor` joins the 80% unit-suite gate. The command is the coverage command above.

## Integration

- [ ] `python -m scorecheck` calls `vendor.publish` in the same change that makes the behavior checks pass. The default data root for the panel stays `data/processed`. The ledger is the sibling `data/vendor/<run id>/`. `vendor.score` is callable on that ledger and returns a probability and three reason-code tokens.

## Regression

- [ ] `panel.generate` still writes only the seven panel files and `run_config.json`. `test_generate_writes_only_panel` still passes.
- [ ] `from_panel` still leaves `external_score_*` null, and `publish` does not fill them. The default command leaves them null.
- [ ] `data/processed` still has one run child after the default command. The ledger is not a second child of `data/processed`.
- [ ] `test_main_prints_banner_then_stages` still monkeypatches the scale to 200 households and still requires exit 0 and stdout equal to the banner plus the six stage names. It does not have to be the one-class draw.
- [ ] `generate_run` and `scripts/write_golden_panel.py` still stop at `from_panel`. `test_golden_panel` still compares the stored panel hashes. Those hashes are not regenerated for this feature.
- [ ] `explain.draft` still raises `RuntimeError`. The default command does not call it.
- [ ] `tests/unit/test_structure.py` still passes. Vendor code draws the LightGBM seed through `Streams`.

## Completeness

- [ ] A person runs `python -m scorecheck` from the repo root after `pip install -r requirements.txt`. They see the default banner and then the six stage names, and nothing else. They find one run directory under `data/processed/` and the ledger under `data/vendor/31a32519f30491a4/`. `vendor.score` on an `application_id` from that ledger returns a probability and three distinct reason-code tokens. A passing unit test alone does not satisfy this check.
