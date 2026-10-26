# Checks — feature-001: Synthetic behavioural panel

Status: draft

Feature: feature-001

Source of truth is `docs/design.md` sections 2 and 3. Where `features.md` differs on scale, drivers, or model count, these checks follow `docs/design.md`.

"Small run" below means `panel.generate` with a household count between 200 and 2,000 and the config seed. No unit test generates 50,000 or 200,000 households.

"Logical hash" means the SHA-256 of a table after its columns are sorted by name, its rows are sorted by every column, and each column is cast to a fixed dtype. It is computed from the table, not from the Parquet bytes.

## Behavior

### Config

- [ ] B1. `scorecheck.config` defines an integer `SEED`, `SCALE_DEFAULT == 50000`, `SCALE_FULL == 200000`, and a month count of 24.
- [ ] B2. `scorecheck.config` owns one banner string per scale. Each banner states that 50,000 households is the default, that 200,000 households is the full run, and which of the two this run used.
- [ ] B3. Every generator multiplier in `scorecheck.config` carries a source label, and every label is one of `BSP`, `telco`, `Meralco`, or `assumption`.

### Detail tables and ground truth

- [ ] B4. `panel.generate` writes one Parquet file per table under `data/processed/<run-id>/`, named after the table: `household`, `person`, `sim`, `electricity_account`, `ewallet_account`, `month_behaviour`, and `ground_truth`. A JSON file in the same directory records the seed and the household count.
- [ ] B5. The column set of each detail table equals the list in `docs/design.md` section 2, with no extra columns:
  - `household`: `household_id`, `region`, `urban_rural`, `income_band`, `remittance_receiver`
  - `person`: `person_id`, `household_id`, `age_years`, `role`
  - `sim`: `sim_id`, `person_id`, `prepaid`, `operator_slot`
  - `electricity_account`: `account_id`, `household_id`, `shared`
  - `ewallet_account`: `account_id`, `household_id`, `shared`
  - `month_behaviour`: `person_id`, `month`, `electricity_state`, `topup_amount`, `wallet_inflow`, `wallet_outflow`
- [ ] B6. `ground_truth` has `person_id`, `month`, `ability`, `willingness`, `vendor_signal`, `true_default`, and one or more shock-flag columns. It has no other columns.
- [ ] B7. On a small run, `household` has exactly the requested number of rows. Every `person.household_id`, `electricity_account.household_id`, and `ewallet_account.household_id` exists in `household`. Every `sim.person_id`, `month_behaviour.person_id`, and `ground_truth.person_id` exists in `person`.
- [ ] B8. On a small run, every `month_behaviour.month` and `ground_truth.month` is an integer from 1 to 24, and every person has all 24 months in `month_behaviour`.
- [ ] B9. On a small run, every `electricity_state` is one of `on_time`, `late_before_disconnection`, `disconnected_restored_30d`, or `unpaid_past_30d`. Both `on_time` and at least one other state appear.
- [ ] B10. On a small run, `true_default` takes only the values 0 and 1, and both values appear.

### Philippine data quirks

- [ ] B11. On a 2,000-household run, the share of `sim` rows with `prepaid` true is within 0.02 of the prepaid probability in `scorecheck.config`.
- [ ] B12. On a small run, at least one person has two or more `sim` rows, and no person has two `sim` rows with the same `operator_slot`.
- [ ] B13. On a small run, `shared` takes both true and false values in `electricity_account`, and both values in `ewallet_account`.
- [ ] B14. On a 2,000-household run, for households with `remittance_receiver` true, mean `wallet_inflow` in the months with the highest remittance-calendar multiplier in `scorecheck.config` is greater than mean `wallet_inflow` in the months with the lowest multiplier.

### Drivers

- [ ] B15. On a 2,000-household run, the Spearman correlation of `ability` with `true_default` is negative, and the Spearman correlation of `willingness` with `true_default` is negative.
- [ ] B16. On a 2,000-household run, the absolute Spearman correlation of `vendor_signal` with `true_default` is at least 0.05. This tolerance is proposed and needs human approval.

### `application_features`

- [ ] B17. `features.from_panel` writes `application_features` as Parquet in the same run directory. Its column set equals the 31 columns in `docs/design.md` section 2, with no extra columns:
  - Core: `application_id`, `person_id`, `age_years`, `income`, `dependents`, `credit_amount`, `installment_to_income`, `utilization`, `open_credit_count`, `delinquency_count_30`, `delinquency_count_60`, `delinquency_count_90`, `history_months`, `on_time_rate`, `payment_to_obligation_ratio`, `gender`, `education`, `marital_status`, `region`, `default_label`, `label_observed`
  - Vendor-only: `external_score_1`, `external_score_2`, `external_score_3`
  - Alternative-data: `sim_count`, `prepaid_flag`, `electricity_late_rate`, `electricity_disconnect_count`, `remittance_inflow_mean`, `ewallet_net_flow_mean`, `shared_account_flag`
- [ ] B18. On a small run, `application_id` is unique and every `application_features.person_id` exists in `person`.
- [ ] B19. On a small run, every row has a non-null value in each of the seven alternative-data columns.
- [ ] B20. On a small run, every row has a null value in `external_score_1`, `external_score_2`, and `external_score_3`.
- [ ] B21. On a small run, `label_observed` takes only the values 0 and 1. Where `label_observed` is 1, `default_label` is 0 or 1.
- [ ] B22. No `ground_truth` value column appears in `application_features`. The test checks `ability`, `willingness`, `vendor_signal`, `true_default`, and every shock-flag column name from `ground_truth`. `person_id` is the shared key and is allowed.

### Consumer scope

- [ ] B23. The run directory holds only the eight tables named in B4 and B17, plus the run JSON. No table or column name in any of them matches the case-insensitive pattern `firm|msme|business|enterprise|company`, and no `person.role` value matches it.

### Reproducibility

- [ ] B24. Two small runs with the same seed and config, each in its own process with a different `PYTHONHASHSEED`, give the same logical hash for each of the eight tables.
- [ ] B25. A small run with a second seed and the same config gives a different logical hash for `ground_truth` and for `application_features`.
- [ ] B26. The logical hash of a table does not change when its rows are shuffled, its columns are reordered, or it is written to Parquet and read back.
- [ ] B27. Code under `src/scorecheck/panel/` and `src/scorecheck/features/` draws random numbers only through `np.random.default_rng`. A source scan finds no call to `np.random.seed`, to any other `np.random.<name>(` module-level draw, or to the standard-library `random` module.
- [ ] B28. `tests/fixtures/golden/` holds a fixture of 200 to 500 households: the seed, the household count, the expected logical hash of each of the eight tables, the household count, the person count, and the mean of `true_default`. A fresh run with that seed and count matches every value exactly.

### CLI

- [ ] B29. `python -m scorecheck` accepts `--scale default` and `--scale full`, and runs at `default` when the flag is absent. `--scale default` resolves to `SCALE_DEFAULT` households and `--scale full` resolves to `SCALE_FULL` households. Any other value exits with a non-zero code and writes no tables.
- [ ] B30. The first line `python -m scorecheck` prints to stdout is the config banner for the scale it used.
- [ ] B31. After the banner, `python -m scorecheck` names each later stage it skipped because the feature behind it does not exist yet.

## Executable tests

Every automated test that will prove the checks above, named before any product code exists. The feature builder writes these first and may not weaken them.

Test command: none yet: the feature creates it. The feature records the command in `docs/testing-standards.md`.

| Test | File | What it asserts | Proves check |
|---|---|---|---|
| test_scale_constants | tests/unit/test_config.py | `SEED` is an int. `SCALE_DEFAULT == 50000`, `SCALE_FULL == 200000`, and the month count is 24. Exact equality. | B1 |
| test_banner_text | tests/unit/test_config.py | For each scale, the banner contains "50,000", "200,000", the word "default", the word "full", and the name of the scale used. The two banners differ. | B2 |
| test_multiplier_sources | tests/unit/test_config.py | Every multiplier entry has a source label in {`BSP`, `telco`, `Meralco`, `assumption`}. Zero entries without a label. | B3 |
| test_tables_written | tests/unit/test_panel_schema.py | A 300-household run writes the seven panel Parquet files and a JSON file whose seed and household count equal the inputs. | B4 |
| test_detail_columns | tests/unit/test_panel_schema.py | Each detail table's column set equals the B5 list exactly. | B5 |
| test_ground_truth_columns | tests/unit/test_panel_schema.py | `ground_truth` has the six named columns plus one or more shock-flag columns, and nothing else. | B6 |
| test_keys_and_counts | tests/unit/test_panel_schema.py | On 300 households, the `household` row count is 300 and every foreign key in B7 resolves. Zero orphan rows. | B7 |
| test_months | tests/unit/test_panel_schema.py | Months are integers in [1, 24]. Each person has 24 distinct months in `month_behaviour`. | B8 |
| test_electricity_states | tests/unit/test_panel_schema.py | Zero values outside the four states. `on_time` count > 0 and non-`on_time` count > 0. | B9 |
| test_true_default_binary | tests/unit/test_panel_schema.py | `true_default` values are a subset of {0, 1}, and both appear. | B10 |
| test_prepaid_share | tests/unit/test_panel_quirks.py | On 2,000 households, the absolute difference between the observed prepaid share and the config probability is at most 0.02. | B11 |
| test_multi_sim | tests/unit/test_panel_quirks.py | At least one person has 2 or more SIMs. Zero duplicate (`person_id`, `operator_slot`) pairs. | B12 |
| test_shared_accounts | tests/unit/test_panel_quirks.py | `shared` has both values in each account table. | B13 |
| test_remittance_calendar | tests/unit/test_panel_quirks.py | On 2,000 households, receivers' mean `wallet_inflow` in the peak multiplier months is greater than in the trough months. | B14 |
| test_driver_signs | tests/unit/test_panel_drivers.py | On 2,000 households, Spearman(`ability`, `true_default`) < 0 and Spearman(`willingness`, `true_default`) < 0. | B15 |
| test_vendor_signal | tests/unit/test_panel_drivers.py | On 2,000 households, abs(Spearman(`vendor_signal`, `true_default`)) >= 0.05. | B16 |
| test_feature_columns | tests/unit/test_features_schema.py | `application_features` column set equals the 31 names in B17 exactly. | B17 |
| test_feature_keys | tests/unit/test_features_schema.py | `application_id` has zero duplicates. Zero `person_id` values missing from `person`. | B18 |
| test_alt_data_filled | tests/unit/test_features_schema.py | Null count is 0 in each of the seven alternative-data columns. | B19 |
| test_vendor_columns_empty | tests/unit/test_features_schema.py | Non-null count is 0 in each `external_score_*` column. | B20 |
| test_label_values | tests/unit/test_features_schema.py | `label_observed` is a subset of {0, 1}. Where it is 1, `default_label` is a subset of {0, 1}. | B21 |
| test_no_ground_truth_leak | tests/unit/test_features_schema.py | The intersection of `application_features` columns with the `ground_truth` columns, minus `person_id` and `month`, is empty. | B22 |
| test_no_firm_entities | tests/unit/test_scope.py | The run directory holds exactly the eight table files plus the JSON. Zero table names, column names, or `person.role` values match `firm\|msme\|business\|enterprise\|company`, case-insensitive. | B23 |
| test_same_seed_same_hash | tests/unit/test_reproducibility.py | Two subprocess runs at 300 households, with `PYTHONHASHSEED` 0 and 1, give equal logical hashes for all eight tables. | B24 |
| test_second_seed_differs | tests/unit/test_reproducibility.py | Seed `SEED` and seed `SEED + 1` at 300 households give different hashes for `ground_truth` and for `application_features`. | B25 |
| test_hash_is_logical | tests/unit/test_reproducibility.py | Shuffling rows, reordering columns, and a Parquet round trip leave the hash unchanged. Changing one cell changes it. | B26 |
| test_rng_source_scan | tests/unit/test_reproducibility.py | A scan of `src/scorecheck/panel/` and `src/scorecheck/features/` finds zero matches for `np.random.seed`, module-level `np.random.<name>(` calls other than `default_rng`, and `import random` or `from random`. | B27 |
| test_golden_panel | tests/unit/test_golden_panel.py | A fresh run with the fixture seed and household count, read from `tests/fixtures/golden/`, matches every stored table hash, both stored counts, and the stored `true_default` mean. Exact match for hashes and counts. Absolute tolerance 1e-12 for the mean. | B28 |
| test_scale_flag | tests/unit/test_cli.py | No flag and `--scale default` resolve to 50000. `--scale full` resolves to 200000. `--scale bogus` exits non-zero and writes no table file. | B29 |
| test_cli_default_run | tests/integration/test_cli_run.py | `python -m scorecheck` in a subprocess with a 600-second timeout exits 0. Stdout line 1 equals the default banner. Stdout names the skipped stages. The run directory holds the eight tables, and `household` has 50,000 rows. This test is in the integration suite, not the unit suite. | B4, B30, B31, Completeness |

Required kinds, per `docs/testing-standards.md`:

- Unit: the `tests/unit/` rows above.
- Golden dataset: `test_golden_panel`. The fixture is created by the feature builder after the first stable run, not in this phase. Any later change to a golden value needs a changelog line that says why it changed.
- Eval case: not applicable. Feature 001 output is deterministic for a given seed and config, so `test_same_seed_same_hash` and `test_golden_panel` cover regression by exact match. Needs human approval.
- Coverage: `src/scorecheck/panel/` and `src/scorecheck/features/` have at least 80% line coverage under the unit suite.

## Integration

- [ ] `python -m scorecheck` is the user-facing action. It calls `panel.generate` and then `features.from_panel` in the same change that makes the behavior checks pass. No separate script is needed to produce the tables.
- [ ] `README.md` states the default command, the full command, and the banner text from `scorecheck.config`.

## Regression

- [ ] None. The app does not exist yet, so Feature 001 changes no existing behavior.

## Completeness

- [ ] A person runs `python -m scorecheck` from the repo root after `pip install -r requirements.txt`. They see the scale banner as the first line of output, and they find the eight Parquet tables and the run JSON under `data/processed/<run-id>/`. A passing unit test alone does not satisfy this check.
