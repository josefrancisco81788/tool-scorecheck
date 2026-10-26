# Checks for feature-001, the synthetic behavioural panel

Status: draft

Feature: feature-001

Source of truth is `docs/design.md` sections 2 and 3. Where `features.md` differs on scale, drivers, or model count, these checks follow `docs/design.md`.

## Definitions

A "300-household run" and a "2,000-household run" mean `panel.generate(SEED, n, data_dir)` with the config `SEED`, that household count, and a temporary `data_dir`, followed by `features.from_panel` on the run directory it wrote. No test generates 200,000 households. Only the integration test generates 50,000.

The "eight tables" are `household`, `person`, `sim`, `electricity_account`, `ewallet_account`, `month_behaviour`, `ground_truth`, and `application_features`.

"Calendar month" of a panel month is `((month - 1) mod 12) + 1`. Month 1 is January, so months 4 and 16 are April and months 12 and 24 are December.

"Origination rows" are the `ground_truth` rows whose `month` equals that person's `origination_month`. There is one per person. "Pre-origination months" are a person's `month_behaviour` rows whose `month` is less than that person's `origination_month`.

"Spearman" is the Spearman rank correlation with average ranks for ties. "Residual of Y on X" is Y minus the fitted value of an ordinary least squares regression of Y on X with an intercept.

### Logical hash

The logical hash of a table is computed from the table's values, not from Parquet bytes. Any two implementations of these steps give the same digest.

1. Cast each column by its name. Every column ending in `_id`, plus `month`, `origination_month`, `age_years`, `operator_slot`, `dependents`, `open_credit_count`, `delinquency_count_30`, `delinquency_count_60`, `delinquency_count_90`, `history_months`, `sim_count`, `electricity_disconnect_count`, `default_label`, `label_observed`, `true_default`, `prepaid_flag`, `shared_account_flag`, `prepaid`, `shared`, `remittance_receiver`, `region_month_shock`, and `post_origination_shock`, becomes int64. Booleans become 1 and 0. `region`, `urban_rural`, `income_band`, `role`, `electricity_state`, `gender`, `education`, and `marital_status` become UTF-8 strings. Every other column becomes float64 and is rounded to 6 decimal places.
2. Sort the columns by name in Unicode code-point order.
3. Sort the rows by the cast values of those columns, in that column order, ascending. Nulls sort last.
4. Serialize as CSV with a header row, comma separator, and `\n` after every line, including the last. Write no index. Write a null as the token `<NA>`. Write a float with exactly 6 digits after the decimal point. Quote a field only if it holds a comma, a double quote, or a newline, using RFC 4180 double-quote escaping.
5. Take the SHA-256 of those bytes, encoded as UTF-8. The hash is the lowercase hex digest.

Worked example. This table, in any row or column order:

| region | person_id | wallet_inflow | shared |
|---|---|---|---|
| NCR | 2 | 1500.1234567 | true |
| Region VII, Cebu | 1 | null | false |
| NCR | 1 | 0.5 | true |

serializes to exactly these bytes:

```text
person_id,region,shared,wallet_inflow
1,NCR,1,0.500000
1,"Region VII, Cebu",0,<NA>
2,NCR,1,1500.123457
```

and its logical hash is `492c75a4c990cada69f18ffcaabb27d2e53edd18a5ddf87e19491ba7aba584b2`.

## Behavior

### Config

- [ ] B1. `scorecheck.config.SEED` is an int. `SCALE_DEFAULT == 50000`. `SCALE_FULL == 200000`. The month count is 24.
- [ ] B2. `scorecheck.config` holds one banner per scale. The default banner equals "This run uses the default scale of 50,000 households. The full run is 200,000 households." The full banner equals "This run uses the full scale of 200,000 households. The default run is 50,000 households."
- [ ] B3. Every generator multiplier in `scorecheck.config` has a source label, and every label is one of `BSP`, `telco`, `Meralco`, or `assumption`.
- [ ] B4. The config prepaid probability equals 0.96 and its source label is `telco`.
- [ ] B5. The config holds exactly 12 monthly remittance multipliers, indexed by calendar month. April and May equal 0.90, July equals 1.07, and December equals 1.18. Each of those four has the source label `BSP`.
- [ ] B6. The config disconnection share equals 0.05 and its source label is `assumption`.

### Run artifact

- [ ] B7. The run id is the first 16 hex characters of the SHA-256 of the UTF-8 string `"{seed}|{n_households}|24"`. For seed 7 and 300 households the run id is `78dc4a1737d02cc1`.
- [ ] B8. `panel.generate(seed, n_households, data_dir)` creates `data_dir/<run id>/` and writes exactly these eight files into it, and no other file: `household.parquet`, `person.parquet`, `sim.parquet`, `electricity_account.parquet`, `ewallet_account.parquet`, `month_behaviour.parquet`, `ground_truth.parquet`, and `run_config.json`.
- [ ] B9. `run_config.json` has the keys `seed`, `n_households`, `scale`, and `n_months`. On a 300-household run, `seed` equals `SEED`, `n_households` equals 300, `n_months` equals 24, and `scale` is a string.

### Detail tables

- [ ] B10. On a 300-household run, the column set of each detail table equals this list exactly:
  - `household`: `household_id`, `region`, `urban_rural`, `income_band`, `remittance_receiver`
  - `person`: `person_id`, `household_id`, `age_years`, `role`, `origination_month`
  - `sim`: `sim_id`, `person_id`, `prepaid`, `operator_slot`
  - `electricity_account`: `account_id`, `household_id`, `shared`
  - `ewallet_account`: `account_id`, `household_id`, `shared`
  - `month_behaviour`: `person_id`, `month`, `electricity_state`, `topup_amount`, `wallet_inflow`, `wallet_outflow`
- [ ] B11. On a 300-household run, `household` has 300 rows. `household.household_id`, `person.person_id`, `sim.sim_id`, `electricity_account.account_id`, and `ewallet_account.account_id` each have zero duplicates. Every `household_id` appears in `person` at least once.
- [ ] B12. On a 300-household run, every foreign key resolves. Every `household_id` in `person`, `electricity_account`, and `ewallet_account` exists in `household`. Every `person_id` in `sim`, `month_behaviour`, and `ground_truth` exists in `person`.
- [ ] B13. On a 300-household run, every `person.origination_month` is an integer from 2 to 18 inclusive.
- [ ] B14. On a 300-household run, `month_behaviour` has one row per person per month. (`person_id`, `month`) has zero duplicates, every `month` is an integer from 1 to 24, and the row count equals 24 times the `person` row count.
- [ ] B15. On a 300-household run, every `month_behaviour.electricity_state` is one of `on_time`, `late_before_disconnection`, `disconnected_restored_30d`, or `unpaid_past_30d`.

### Ground truth

- [ ] B16. On a 300-household run, the column set of `ground_truth` equals exactly `person_id`, `month`, `ability`, `willingness`, `region_month_shock`, `post_origination_shock`, `vendor_signal`, `true_default`.
- [ ] B17. On a 300-household run, (`person_id`, `month`) in `ground_truth` has zero duplicates, every `month` is an integer from 1 to 24, and the row count equals 24 times the `person` row count.
- [ ] B18. On a 300-household run, `region_month_shock` and `post_origination_shock` are boolean, and each takes both true and false.
- [ ] B19. On a 300-household run, `post_origination_shock` is false on every row whose `month` is less than that person's `origination_month`.
- [ ] B20. On a 300-household run, every `true_default` is 0 or 1. For every person, if `true_default` is 1 at month t, it is 1 at every month after t.

### Philippine distributions

- [ ] B21. On a 2,000-household run, the share of `sim` rows with `prepaid` true is within 0.02 of 0.96.
- [ ] B22. On a 2,000-household run, the `sim` row count divided by the `person` row count is between 1.3 and 2.5 inclusive, and at least one person has two or more `sim` rows.
- [ ] B23. On a 2,000-household run, among persons in households with `remittance_receiver` true, mean `wallet_inflow` over December rows is greater than mean `wallet_inflow` over April rows.
- [ ] B24. On a 2,000-household run, the share of `month_behaviour` rows whose `electricity_state` is `disconnected_restored_30d` or `unpaid_past_30d` is within 0.03 of 0.05. The share with `on_time` is greater than 0.5. All four states appear.
- [ ] B25. On a 2,000-household run, `shared` true and `shared` false each appear on at least 20 `electricity_account` rows and on at least 20 `ewallet_account` rows.

### Drivers

- [ ] B26. On the origination rows of a 2,000-household run, Spearman(`ability`, `true_default`) < 0 and Spearman(`willingness`, `true_default`) < 0.
- [ ] B27. On the origination rows of a 2,000-household run, Spearman(residual of `ability` on `willingness`, `true_default`) < 0 and Spearman(residual of `willingness` on `ability`, `true_default`) < 0.
- [ ] B28. On the origination rows of a 2,000-household run, Spearman(residual of `vendor_signal` on `ability` and `willingness`, `true_default`) > 0.

### `application_features` from `features.from_panel`

- [ ] B29. `features.from_panel` on a run directory returns `application_features` and writes it as `application_features.parquet` in that directory. On a 300-household run, its column set equals these 31 names exactly, so `origination_month` is not among them:
  - Core: `application_id`, `person_id`, `age_years`, `income`, `dependents`, `credit_amount`, `installment_to_income`, `utilization`, `open_credit_count`, `delinquency_count_30`, `delinquency_count_60`, `delinquency_count_90`, `history_months`, `on_time_rate`, `payment_to_obligation_ratio`, `gender`, `education`, `marital_status`, `region`, `default_label`, `label_observed`
  - Vendor-only: `external_score_1`, `external_score_2`, `external_score_3`
  - Alternative-data: `sim_count`, `prepaid_flag`, `electricity_late_rate`, `electricity_disconnect_count`, `remittance_inflow_mean`, `ewallet_net_flow_mean`, `shared_account_flag`
- [ ] B30. On a 300-household run, `features.from_panel` returns one row per person. `application_id` and `person_id` each have zero duplicates, and the set of `person_id` values equals the set in `person`.
- [ ] B31. On a 300-household run, `features.from_panel` returns `label_observed` equal to 1 on every row, and `default_label` equal to that person's `true_default` on their origination row.
- [ ] B32. On a 300-household run, each alternative-data value returned by `features.from_panel` equals the value the test recomputes from the detail tables, after both are rounded to 6 decimal places:
  - `sim_count` is the count of the person's `sim` rows.
  - `prepaid_flag` is 1 if the person's `sim` row with the lowest `sim_id` has `prepaid` true, else 0.
  - `electricity_late_rate` is the share of pre-origination months whose `electricity_state` is not `on_time`.
  - `electricity_disconnect_count` is the count of pre-origination months whose `electricity_state` is `disconnected_restored_30d` or `unpaid_past_30d`.
  - `remittance_inflow_mean` is the mean `wallet_inflow` over pre-origination months.
  - `ewallet_net_flow_mean` is the mean of `wallet_inflow` minus `wallet_outflow` over pre-origination months.
  - `shared_account_flag` is 1 if the person's household has any `electricity_account` or `ewallet_account` row with `shared` true, else 0.
- [ ] B33. On a 300-household run, changing every `month_behaviour` row whose `month` is at or after the person's `origination_month`, then running `features.from_panel` again, leaves the logical hash of `application_features` unchanged.
- [ ] B34. On a 300-household run, `features.from_panel` returns `external_score_1`, `external_score_2`, and `external_score_3` null on every row.
- [ ] B35. On a 300-household run, `age_years`, `income`, `utilization`, and `delinquency_count_30` returned by `features.from_panel` have zero nulls and at least two distinct values each. `history_months` has a minimum of at most 3 and a maximum of at least 12. A quantile match against Home Credit waits until the Home Credit file is summarized, and these checks omit it on purpose.
- [ ] B36. On a 300-household run, no `ground_truth` column other than `person_id` appears in `application_features`.

### Consumer scope

- [ ] B37. On a 300-household run, no name of the eight tables, no column name in them, and no `person.role` value matches the case-insensitive pattern `firm|msme|business|enterprise|company`.

### Reproducibility

- [ ] B38. Two 300-household runs with the same seed and config, each in its own process, one with `PYTHONHASHSEED=0` and one with `PYTHONHASHSEED=1`, each writing to a distinct output directory, give equal logical hashes for all eight tables.
- [ ] B39. A 300-household run with seed `SEED + 1` gives a different logical hash from the `SEED` run for `ground_truth` and for `application_features`.
- [ ] B40. The logical hash of a table from a 300-household run does not change when its rows are shuffled, when its columns are reordered, or after a Parquet write and read. Changing one cell changes it. The hash of the worked-example table above equals the stated digest.
- [ ] B41. `tests/fixtures/golden/` holds the seed, a household count between 200 and 500, and the expected logical hash of each of the eight tables. A fresh run with that seed and count matches all eight hashes exactly. The test fails, and does not skip, when the fixture is missing.

The two-process hash in B38 is the proof of reproducibility. A text scan of the source for `np.random.seed` is not evidence of it, so these checks have none.

### CLI

- [ ] B42. The `python -m scorecheck` argument parser accepts `--scale default` and `--scale full`, and uses `default` when the flag is absent. `default` resolves to `SCALE_DEFAULT` households and `full` resolves to `SCALE_FULL` households.
- [ ] B43. `python -m scorecheck --scale` with any value other than `default` or `full` exits non-zero and creates no file or directory under `data/processed`.
- [ ] B44. `python -m scorecheck` with no flag exits 0. The first stdout line equals the default banner from B2. After the first line, stdout has one line that equals each of `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`. The run directory under `data/processed` holds `household.parquet` with 50,000 rows, and its `run_config.json` has `scale` equal to `default` and `n_households` equal to 50000.

## Executable tests

Every automated test that will prove the checks above, named before any product code exists. The feature builder writes these first and may not weaken them.

Test command: none yet. The feature creates it and records it in `docs/testing-standards.md`.

| Test | File | What it asserts | Proves check |
|---|---|---|---|
| test_scale_constants | tests/unit/test_config.py | `SEED` is an int. `SCALE_DEFAULT == 50000`. `SCALE_FULL == 200000`. The month count is 24. | B1 |
| test_banner_text | tests/unit/test_config.py | The default banner equals "This run uses the default scale of 50,000 households. The full run is 200,000 households." The full banner equals "This run uses the full scale of 200,000 households. The default run is 50,000 households." | B2 |
| test_multiplier_sources | tests/unit/test_config.py | Every generator multiplier has a source label in {`BSP`, `telco`, `Meralco`, `assumption`}. | B3 |
| test_prepaid_config | tests/unit/test_config.py | The prepaid probability equals 0.96 and its label is `telco`. | B4 |
| test_remittance_config | tests/unit/test_config.py | Exactly 12 remittance multipliers. April and May equal 0.90, July equals 1.07, December equals 1.18. Each of those four is labeled `BSP`. | B5 |
| test_disconnection_config | tests/unit/test_config.py | The disconnection share equals 0.05 and its label is `assumption`. | B6 |
| test_run_id | tests/unit/test_run_artifact.py | The run id is the first 16 hex characters of SHA-256 of `"{seed}\|{n_households}\|24"`. Seed 7 and 300 households give `78dc4a1737d02cc1`. | B7 |
| test_generate_writes_only_panel | tests/unit/test_run_artifact.py | `panel.generate(SEED, 300, tmp)` creates `tmp/<run id>/` holding exactly the seven panel Parquet files and `run_config.json`, and no other file. | B8 |
| test_run_config | tests/unit/test_run_artifact.py | On a 300-household run, `run_config.json` has the keys `seed`, `n_households`, `scale`, and `n_months`. `seed == SEED`, `n_households == 300`, `n_months == 24`, and `scale` is a string. | B9 |
| test_detail_columns | tests/unit/test_panel_schema.py | On a 300-household run, each detail table's column set equals the B10 list exactly. | B10 |
| test_unique_keys | tests/unit/test_panel_schema.py | On a 300-household run, `household` has 300 rows. Zero duplicates in `household_id`, `person_id`, `sim_id`, and both `account_id` columns. Every `household_id` appears in `person` at least once. | B11 |
| test_foreign_keys | tests/unit/test_panel_schema.py | On a 300-household run, every foreign key in B12 resolves. Zero orphan rows. | B12 |
| test_origination_month_range | tests/unit/test_panel_schema.py | On a 300-household run, every `origination_month` is an integer from 2 to 18 inclusive. | B13 |
| test_month_behaviour_grain | tests/unit/test_panel_schema.py | On a 300-household run, zero duplicate (`person_id`, `month`) pairs in `month_behaviour`. Every `month` is an integer from 1 to 24. Row count equals 24 times the `person` row count. | B14 |
| test_electricity_states | tests/unit/test_panel_schema.py | On a 300-household run, zero `electricity_state` values outside the four states. | B15 |
| test_ground_truth_columns | tests/unit/test_ground_truth.py | On a 300-household run, the `ground_truth` column set equals the eight names in B16 exactly. | B16 |
| test_ground_truth_grain | tests/unit/test_ground_truth.py | On a 300-household run, zero duplicate (`person_id`, `month`) pairs in `ground_truth`. Every `month` is an integer from 1 to 24. Row count equals 24 times the `person` row count. | B17 |
| test_shock_columns | tests/unit/test_ground_truth.py | On a 300-household run, `region_month_shock` and `post_origination_shock` are boolean, and each takes both true and false. | B18 |
| test_no_shock_before_origination | tests/unit/test_ground_truth.py | On a 300-household run, `post_origination_shock` is false on every row with `month` less than that person's `origination_month`. | B19 |
| test_true_default_absorbing | tests/unit/test_ground_truth.py | On a 300-household run, every `true_default` is 0 or 1. Zero persons have a 1 at month t followed by a 0 at a later month. | B20 |
| test_prepaid_share | tests/evals/test_panel_distributions.py | On a 2,000-household run, the share of `sim` rows with `prepaid` true is within 0.02 of 0.96. | B21 |
| test_sims_per_person | tests/evals/test_panel_distributions.py | On a 2,000-household run, `sim` rows divided by `person` rows is between 1.3 and 2.5 inclusive. At least one person has two or more `sim` rows. | B22 |
| test_remittance_december_over_april | tests/evals/test_panel_distributions.py | On a 2,000-household run, among persons in `remittance_receiver` households, mean `wallet_inflow` on December rows is greater than on April rows. | B23 |
| test_electricity_state_shares | tests/evals/test_panel_distributions.py | On a 2,000-household run, the share of rows in {`disconnected_restored_30d`, `unpaid_past_30d`} is within 0.03 of 0.05. The `on_time` share is greater than 0.5. All four states appear. | B24 |
| test_shared_account_counts | tests/evals/test_panel_distributions.py | On a 2,000-household run, `shared` true and `shared` false each appear on at least 20 rows of `electricity_account` and at least 20 rows of `ewallet_account`. | B25 |
| test_driver_signs | tests/evals/test_panel_distributions.py | On the origination rows of a 2,000-household run, Spearman(`ability`, `true_default`) < 0 and Spearman(`willingness`, `true_default`) < 0. | B26 |
| test_driver_residuals | tests/evals/test_panel_distributions.py | On the origination rows of a 2,000-household run, Spearman(residual of `ability` on `willingness`, `true_default`) < 0 and Spearman(residual of `willingness` on `ability`, `true_default`) < 0. | B27 |
| test_vendor_signal_residual | tests/evals/test_panel_distributions.py | On the origination rows of a 2,000-household run, Spearman(residual of `vendor_signal` on `ability` and `willingness`, `true_default`) > 0. | B28 |
| test_feature_columns | tests/unit/test_features.py | On a 300-household run, `features.from_panel` writes `application_features.parquet` in the run directory, and the returned column set equals the 31 names in B29 exactly. | B29 |
| test_one_row_per_person | tests/unit/test_features.py | On a 300-household run, zero duplicates in `application_id` and in `person_id`. The `person_id` set equals the `person` set. | B30 |
| test_labels_at_origination | tests/unit/test_features.py | On a 300-household run, `label_observed` is 1 on every row. `default_label` equals `true_default` on each person's origination row. | B31 |
| test_alt_data_recomputed | tests/unit/test_features.py | On a 300-household run, each of the seven alternative-data columns equals the B32 recomputation from the detail tables, after both are rounded to 6 decimal places. | B32 |
| test_post_origination_invariance | tests/unit/test_features.py | On a 300-household run, changing every `month_behaviour` row at or after `origination_month` and running `features.from_panel` again leaves the `application_features` logical hash unchanged. | B33 |
| test_vendor_columns_null | tests/unit/test_features.py | On a 300-household run, `external_score_1`, `external_score_2`, and `external_score_3` are null on every returned row. | B34 |
| test_core_columns | tests/unit/test_features.py | On a 300-household run, `age_years`, `income`, `utilization`, and `delinquency_count_30` have zero nulls and at least two distinct values each. `history_months` minimum is at most 3 and maximum is at least 12. | B35 |
| test_no_ground_truth_leak | tests/unit/test_features.py | On a 300-household run, the `application_features` columns share no name with `ground_truth` except `person_id`. | B36 |
| test_no_firm_entities | tests/unit/test_scope.py | On a 300-household run, zero table names, column names, or `person.role` values in the eight tables match `firm\|msme\|business\|enterprise\|company`, case-insensitive. | B37 |
| test_same_seed_same_hash | tests/unit/test_reproducibility.py | Two subprocess runs at 300 households, `PYTHONHASHSEED=0` and `PYTHONHASHSEED=1`, distinct output directories, give equal logical hashes for all eight tables. | B38 |
| test_second_seed_differs | tests/unit/test_reproducibility.py | At 300 households, seed `SEED + 1` gives a different logical hash from `SEED` for `ground_truth` and for `application_features`. | B39 |
| test_hash_is_logical | tests/unit/test_reproducibility.py | On a 300-household run, shuffling rows, reordering columns, and a Parquet write and read leave each table's hash unchanged. Changing one cell changes it. The worked-example table hashes to `492c75a4c990cada69f18ffcaabb27d2e53edd18a5ddf87e19491ba7aba584b2`. | B40 |
| test_golden_panel | tests/unit/test_golden_panel.py | The fixture in `tests/fixtures/golden/` exists, and its household count is between 200 and 500. A fresh run with its seed and count matches all eight stored hashes exactly. A missing fixture fails the test. | B41 |
| test_scale_flag | tests/unit/test_cli.py | The parser maps no flag and `--scale default` to `SCALE_DEFAULT`, and `--scale full` to `SCALE_FULL`. | B42 |
| test_bad_scale_writes_nothing | tests/unit/test_cli.py | `python -m scorecheck --scale bogus` exits non-zero. The listing of `data/processed` is the same before and after. | B43 |
| test_cli_default_run | tests/integration/test_cli_run.py | `python -m scorecheck` with no flag, in a subprocess with a 600-second timeout, exits 0. Stdout line 1 equals the default banner. After line 1, one line equals each of `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`. The run directory has `household.parquet` with 50,000 rows and `run_config.json` with `scale` equal to `default` and `n_households` equal to 50000. | B44, Completeness |

No test generates 200,000 rows. The full scale is checked through `SCALE_FULL`, the full banner, and the `--scale full` parser mapping.

Required kinds, per `docs/testing-standards.md`:

- Unit: the `tests/unit/` rows above. They cover config, schema, keys, ground truth, `application_features`, hashes, the golden fixture, and the CLI parser.
- Golden dataset: `test_golden_panel`. The feature builder writes the fixture in this feature, after the other panel tests pass. This commit does not add it. Any later change to a stored hash needs a changelog line that says why it changed.
- Eval case: `tests/evals/test_panel_distributions.py`, holding the distribution checks B21 to B28. Eval scores are advisory until v1, per `docs/testing-standards.md`. The cases still exist and run.
- Integration: `test_cli_default_run`, in the integration suite, not the unit suite.
- Coverage: `src/scorecheck/panel/` and `src/scorecheck/features/` have at least 80% line coverage under the unit suite.

## Integration

- [ ] `python -m scorecheck` is the user-facing action. It calls `panel.generate` and then `features.from_panel` in the same change that makes the behavior checks pass. The default data root is `data/processed`. No separate script is needed to produce the tables.
- [ ] `README.md` states the default command, the full command, and both banner strings from B2.

## Regression

- [ ] None. The app does not exist yet, so Feature 001 changes no existing behavior.

## Completeness

- [ ] A person runs `python -m scorecheck` from the repo root after `pip install -r requirements.txt`. They see the default banner as the first line of output, and they find the eight Parquet tables and `run_config.json` under `data/processed/<run id>/`. A passing unit test alone does not satisfy this check.
