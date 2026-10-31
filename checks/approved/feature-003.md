# Checks for feature-003, the in-house challenger in shadow mode

Status: draft

Feature: feature-003

`external_score_1`, `external_score_2`, and `external_score_3` stay null. Challenger scores are recorded in a sibling directory, beside the vendor probability taken from `vendor.score`. Research note A proposed writing that probability back into `external_score_1`. JOS-24, the locked Feature 002 checks, and `docs/design.md` keep the columns null.

`default_label` is origination-month `true_default`, and `label_observed` is 1 on every row. The scores file is the in-sample shadow record on that fully labelled book. Features 004 and 005 do not use it as the vendor-versus-challenger gap. Feature 004 measures that gap on people held out of refitting. This feature does not add an approval flag, does not call `explain.draft`, and does not issue a decline.

The scorecard constants below are approved: points to double the odds `20`, base points `600`, base odds `50` goods to one bad. The binning choice is quantile bins, ten bins. The LightGBM monotone method is `advanced`. `xgboost==3.4.1` requires Python `>=3.12`. `scikit-learn==1.9.1` is the histogram booster and the logistic regression. `requires-python` becomes `>=3.12` when Feature 003 is implemented.

Measured on this machine on 30 Oct 2026. One `logical_hash` of a 50,000-row, 31-column frame took 0.870 seconds. `vendor.score` recomputes that hash and rereads the ledger on every call. Calling it once per row of the default book is about 12 hours of hashing. The integration timeout stays 600 seconds. Feature 002 locks `vendor.__all__`. This draft does not add a name to that list and does not change `vendor.score`. The per-row call in C4 is the contract for a book of at most 300 applications. It is not the contract for the default command until a human allows a change inside `src/scorecheck/vendor/`.

## Definitions

A challenger run is a vendor run that has already been published. `publish` below means `scorecheck.models.publish`. Unit checks use `scorecheck.config.SEED` and 300 households unless a check names another size. No test generates 200,000 households. The integration test remains the only 50,000-household run, and its timeout stays 600 seconds.

The run id is the Feature 002 run id. For seed `20261024` and 50,000 households it is `31a32519f30491a4`. For seed `20261024` and 200 households it is `6e6c82611fa89cf4`.

The scores path is `run_dir.parent.with_name("models") / run_dir.name`. The default command's scores path is `data/models/31a32519f30491a4/`. The 200-household command's scores path is `data/models/6e6c82611fa89cf4/`.

The scores directory holds exactly two files, `scores.parquet` and `bind.json`. `scores.parquet` has exactly these columns, in this order, one row per application, sorted by `application_id` ascending.

- `application_id`, int64, zero duplicates
- `vendor_probability`, float64, every value finite and inside the closed interval from 0 to 1
- `lightgbm`, `lightgbm_monotone`, `xgboost`, `xgboost_monotone`, `hist_gradient_boosting`, `hist_gradient_boosting_monotone`, `scorecard_probability`, float64, every value finite and inside the closed interval from 0 to 1
- `scorecard_points`, float64, finite on a two-class publish, null on a one-class publish

`bind.json` parses as one JSON object whose only key is `features_hash`. The value is `scorecheck.logical_hash.logical_hash` of the `application_features` table at publish time. `line` reads that table and computes the same hash again. A difference raises `StaleScores`. Parquet byte equality is not the bind.

The scores hash is `logical_hash` of `scores.parquet`. `application_id` is an id column. Every other column is float64. A null `scorecard_points` cell renders as `<NA>`. Parquet byte equality is not required.

The matrix columns, in this order, are the only columns a challenger fit receives.

`utilization`, `open_credit_count`, `delinquency_count_30`, `delinquency_count_60`, `delinquency_count_90`, `on_time_rate`, `income`, `dependents`, `credit_amount`, `installment_to_income`, `payment_to_obligation_ratio`, `history_months`, `sim_count`, `prepaid_flag`, `electricity_late_rate`, `electricity_disconnect_count`, `remittance_inflow_mean`, `ewallet_net_flow_mean`, `shared_account_flag`.

`features.challenger_matrix(frame)` returns those columns and no others. Row i is the application row with the i-th smallest `application_id`. The function does not write a file and does not read `ground_truth`. The label is `default_label` in that same order, not `true_default`. `application_id`, `person_id`, `age_years`, `gender`, `education`, `marital_status`, `region`, `external_score_1`, `external_score_2`, `external_score_3`, `default_label`, and `label_observed` are absent. `vendor_signal` and `private_factor` are absent. No ground-truth column is present.

The monotone columns are `utilization`, `delinquency_count_30`, `delinquency_count_60`, `delinquency_count_90`, and `installment_to_income`. The constraint value on each is the integer `1`, meaning a higher value raises predicted default probability. Every other matrix column has constraint `0`. The constraint vector follows the matrix column order.

A one-class feature file has one distinct `default_label`. A two-class feature file is a vendor run whose `default_label` has been overwritten so the lower half of `application_id` values are 0 and the upper half are 1. The natural 200-household draw is not required to be one-class.

Each library seed is one `integers(0, 2**31)` draw, lower bound included and `2**31` excluded, with no `size` argument. The namespace is `models`. The stream names are `lightgbm`, `xgboost`, `hist_gradient_boosting`, and `scorecard`, each issued once. The same LightGBM integer is `seed`, `bagging_seed`, `feature_fraction_seed`, and `data_random_seed` on both LightGBM fits. The same XGBoost integer is `random_state` on both XGBoost fits. The same histogram integer is `random_state` on both histogram fits. The scorecard integer is `random_state` on the logistic regression. Those streams are asked for no other integer.

Both LightGBM fits use `lightgbm.train` once each on a two-class publish. The shared params mapping has exactly these keys and values, plus the monotone keys only on the second fit. `objective` is `binary`. `deterministic` is boolean `True`. `force_row_wise` is boolean `True`. `device_type` is `cpu`. `num_threads` is the integer `1`. `feature_fraction` compares equal to 1. `bagging_fraction` compares equal to 1. `bagging_freq` is the integer `0`. `num_leaves` is the integer `15`. `learning_rate` compares equal to 0.1. `verbose` is the integer `-1`. The four seeds are the LightGBM integer. `num_boost_round` is the integer `40`. Neither call has an early-stopping argument or an early-stopping callback. The unconstrained params have no `monotone_constraints` key and no `monotone_constraints_method` key. The monotone params add `monotone_constraints`, the constraint vector as a list of ints, and `monotone_constraints_method` equal to `advanced`.

Both XGBoost fits construct `xgboost.XGBClassifier` once each on a two-class publish and call `fit` once each, with the matrix and the label and with no `eval_set`. The shared constructor arguments are `n_estimators` 40, `learning_rate` 0.1, `max_leaves` 15, `grow_policy` `lossguide`, `tree_method` `hist`, `subsample` 1, `colsample_bytree` 1, `n_jobs` the integer `1`, `random_state` the XGBoost integer, `objective` `binary:logistic`, and `verbosity` the integer `0`. The unconstrained constructor passes `monotone_constraints` as `None`. The monotone constructor passes the constraint vector as a tuple of ints. `early_stopping_rounds` is not set.

Both histogram fits construct `sklearn.ensemble.HistGradientBoostingClassifier` once each on a two-class publish and call `fit` once each. The shared constructor arguments are `loss` `log_loss`, `learning_rate` 0.1, `max_iter` 40, `max_leaf_nodes` 15, `min_samples_leaf` 20, `l2_regularization` 0.0, `max_features` 1.0, `max_bins` 255, `categorical_features` `None`, `early_stopping` boolean `False`, `random_state` the histogram integer, and `verbose` the integer `0`. The unconstrained constructor passes `monotonic_cst` as `None`. The monotone constructor passes the constraint vector as a sequence of ints in column order.

`pyproject.toml` and `requirements.txt` each pin `xgboost==3.4.1` and `scikit-learn==1.9.1`, and they keep `lightgbm==4.7.0`. `requires-python` becomes `>=3.12` because that XGBoost wheel requires it. `importlib.metadata.version` returns `3.4.1` for `xgboost`, `1.9.1` for `scikit-learn`, and `4.7.0` for `lightgbm`.

Weight of evidence uses goods as `default_label == 0` and bads as `default_label == 1`. For a column, bins come from `pandas.qcut` on the training values with `q=10` and `duplicates="drop"`. A column with one distinct value is one bin. `scorecheck.models.binned_weight_of_evidence(values, labels, monotone)` is not in `__all__`. It returns one weight-of-evidence float per input row.

For `n` bins with good counts `g_i` and bad counts `b_i`:

- `dist_good_i = (g_i + 0.5) / sum(g_j + 0.5)`
- `dist_bad_i = (b_i + 0.5) / sum(b_j + 0.5)`
- `woe_i = ln(dist_good_i / dist_bad_i)`

When `monotone` is true, bins are ordered by ascending feature value. While an adjacent pair has `woe[i + 1] > woe[i]`, merge the leftmost such pair, recompute, and stop when the weights are non-increasing or one bin remains. When `monotone` is false, bins are not merged.

Two fixtures fix those numbers. Both use values `0, 1, 2, 3, 4, 5, 6, 7, 8, 9` as float64. `qcut` with `q=5` is not the production call; these fixtures use `q=10`, and `duplicates="drop"` yields five bins of two rows because there are ten distinct values. The five bins are rows `(0, 1)`, `(2, 3)`, `(4, 5)`, `(6, 7)`, `(8, 9)`.

The level fixture labels are `0, 0, 0, 0, 0, 1, 1, 1, 1, 1`. Its weights of evidence are `ln(5)`, `ln(5)`, `0`, `-ln(5)`, `-ln(5)`, each value repeated on both rows of its bin. No merge happens when `monotone` is true. Absolute tolerance is `0` on these mathematical values, compared at `1e-12`.

The merge fixture labels are `0, 1, 1, 0, 0, 0, 1, 1, 1, 1`. With `monotone` false, the five bin weights are `ln(17/13)`, `ln(17/13)`, `ln(85/13)`, `ln(17/65)`, `ln(17/65)`. With `monotone` true, the leftmost violating pairs merge until three bins remain, and the row weights are `ln(27/11)` on the first six rows and `ln(3/11)` on the last four rows. Absolute tolerance is `1e-12`.

The logistic regression is `sklearn.linear_model.LogisticRegression` constructed with `C` 1.0, `solver` `lbfgs`, `max_iter` 500, and `random_state` the scorecard integer, and with no other arguments. On a two-class publish it is fit once, on the weight-of-evidence matrix in matrix column order and `application_id` order. `scorecard_probability` is the predicted probability of class 1.

`scorecheck.models.points_to_double_the_odds(probability)` is not in `__all__`. `PDO` is 20, `BasePoints` is 600, and `BaseOdds` is 50. `Factor = PDO / ln(2)`. `Offset = BasePoints - Factor * ln(BaseOdds)`. The stored probability `p` is clipped only inside this function to the closed interval from `1e-6` to `1 - 1e-6`. Odds are `(1 - p_clip) / p_clip`. Points are `Offset + Factor * ln(odds)`. At probability `0.2`, points equal that formula, absolute tolerance `1e-9`. Points at probability `0.2` exceed points at probability `1/3` by 20, absolute tolerance `1e-9`, because the odds double from 2 to 4. A one-class publish does not call this function.

`scorecheck.models.__all__` is exactly `publish`, `line`, `ChallengerLines`, `ScoresMissing`, `StaleScores`, and `UnknownApplicant`. `ChallengerLines` is a named tuple with the eight score fields in the parquet column order after `application_id`. `scorecard_points` is `None` when the parquet cell is null. `ScoresMissing`, `StaleScores`, and `UnknownApplicant` are distinct subclasses of `Exception`. None is a subclass of another. None is a subclass of `LedgerMissing`, `StaleLedger`, or `vendor.UnknownApplicant`.

## Behavior

### Command

- [ ] C1. `python -m scorecheck` calls `panel.generate`, then `features.from_panel`, then `vendor.publish`, then `models.publish`, in that order, once each. `explain.draft` is not called. Printing the stage name `models` is not a call to `models.publish`. `models.publish` writes nothing to stdout and nothing to stderr on a one-class publish and on a two-class publish. After the scale banner, stdout is the six stage names `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`, one per line, and nothing else. `test_command_order` records that four-call order. The first three calls remain `panel.generate`, `features.from_panel`, and `vendor.publish`, once each.

### Scores path

- [ ] C2. After `publish(run_dir)`, the scores directory is `run_dir.parent.with_name("models") / run_dir.name` and holds exactly `scores.parquet` and `bind.json`. The default command writes `data/models/31a32519f30491a4/`. The 200-household command writes `data/models/6e6c82611fa89cf4/`. `data/processed` still has exactly one child, the run id. The vendor ledger path still holds exactly `ledger.parquet` and `bind.json`.

### Writers

- [ ] C3. `models.publish` is the only writer of the scores directory. `models.line` is the only reader of it. `publish` does not call `vendor.publish`. After `publish`, the run directory's file set is unchanged, and the logical hash of `application_features` is unchanged. The logical hash of `ledger.parquet` is unchanged. The scores files are not inside the run directory and not inside the vendor directory.

### Vendor score

- [ ] C4. On a book of at most 300 applications, `publish` obtains `vendor_probability` by calling `vendor.score(run_dir, application_id)` once per application, in ascending `application_id` order, before it calls `lightgbm.train`, `XGBClassifier`, `HistGradientBoostingClassifier`, or `LogisticRegression`. The stored probability equals that return value, absolute tolerance 0. A monkeypatch that makes `vendor.score` return probability `0.25` stores `0.25`. A file under `src/scorecheck/models/` does not import `scorecheck.vendor._private`, does not contain the text `ledger.parquet`, and does not contain the text `pred_contrib`. If `vendor.score` raises `LedgerMissing` or `StaleLedger`, that exception propagates, no trainer is called, and the scores path is absent when it was absent before. The default command does not use this per-row loop. Its `vendor_probability` values stay unspecified until a human allows a change inside `src/scorecheck/vendor/`.

### Matrix

- [ ] C5. `features.challenger_matrix` returns exactly the matrix columns in Definitions, in that order, sorted by `application_id`. Filling `external_score_1`, `external_score_2`, and `external_score_3` with `1.0` leaves the matrix unchanged, absolute tolerance 0. Adding `1000` to `age_years`, and replacing `gender`, `education`, `marital_status`, and `region` with a different allowed value on every row, leaves the matrix unchanged, absolute tolerance 0. Adding columns named `ability`, `willingness`, `vendor_signal`, `true_default`, and `private_factor` to the frame passed in leaves them out of the returned matrix. Deleting `ground_truth.parquet` after a successful `vendor.publish` still lets `models.publish` write the scores. Adding `1000.0` to every `ability` and `willingness` cell before that deletion is not required. Overwriting `default_label` changes the training label and leaves the matrix columns unchanged.

### External scores and demographics stay put

- [ ] C6. After `from_panel`, after `vendor.publish`, after `models.publish`, and after `python -m scorecheck`, `external_score_1`, `external_score_2`, and `external_score_3` are null on every `application_features` row. Those names are absent from the challenger matrix. The five demographic names remain columns of `application_features` and remain absent from the matrix. `application_features` gains no column.

### Monotone refit

- [ ] C7. On a two-class publish, each of LightGBM, XGBoost, and `HistGradientBoostingClassifier` is fit unconstrained and fit again with the constraint vector. The constructor and `train` arguments equal Definitions. A 200-household two-class publish and a 300-household two-class publish with the same run seed pass equal params, including the seeds and the constraint vector. The seed draws use `Streams`. They do not call `default_rng`, `RandomState`, `np.random.seed`, or `SeedSequence` outside `src/scorecheck/_streams.py`.

### Scorecard

- [ ] C8. On the level fixture, `binned_weight_of_evidence` returns the level weights in Definitions, absolute tolerance `1e-12`, for `monotone` false and for `monotone` true. On the merge fixture, `monotone` false returns the five unmerged weights, and `monotone` true returns the three-bin merged weights, absolute tolerance `1e-12`. A two-class `publish` calls `binned_weight_of_evidence` once per matrix column, with `monotone` true only for the five monotone columns. The logistic `fit` receives that weight-of-evidence matrix, absolute tolerance `1e-12`, and the `default_label` vector. `points_to_double_the_odds(0.2)` matches the formula, absolute tolerance `1e-9`, and exceeds `points_to_double_the_odds(1/3)` by 20, absolute tolerance `1e-9`. On a two-class publish, `scorecard_points` equals `points_to_double_the_odds` of that row's `scorecard_probability`, absolute tolerance `1e-9`.

### One-class publish

- [ ] C9. If `default_label` has one distinct value, `publish` does not call `lightgbm.train`, `lightgbm.Dataset`, `XGBClassifier`, `HistGradientBoostingClassifier`, `LogisticRegression`, `binned_weight_of_evidence`, or `points_to_double_the_odds`. Every probability column equals that observed rate, `0.0` when the label is 0 and `1.0` when the label is 1, absolute tolerance 0. `scorecard_points` is null on every row. `line` returns `None` for `scorecard_points`. `publish` prints nothing and does not raise. The 200-household CLI test does not have to build this draw. A unit test does.

### Lines

- [ ] C10. `models.line(run_dir, application_id)` returns a `ChallengerLines`. On a two-class publish the eight numbers equal the scores row for that `application_id`. The seven probabilities lie in the closed interval from 0 to 1. `line` does not call `vendor.score`, `lightgbm.train`, or any `fit`. `line` before `publish` raises `ScoresMissing` and does not create the scores directory. Deleting either scores file raises `ScoresMissing`. `line(run_dir, max(application_id) + 1)` raises `models.UnknownApplicant` and leaves both scores files in place. Changing `income` by `1.0` on every application row, and writing `application_features.parquet` back, makes `line` raise `StaleScores` and return no probability.

### Shadow

- [ ] C11. The scores file has no column named `approval`, `decision`, `decline`, `reason_1`, `reason_2`, or `reason_3`. `publish` does not call `explain.draft`. A monkeypatch that raises from `explain.draft` is not triggered by `publish` or by `line`. No file written by `publish` is a decline or a signed decision. The vendor ledger's logical hash after `publish` equals the hash from before `publish`.

### Same-machine hash

- [ ] C12. Two publishes of the same run, in two subprocesses on one machine, produce the same scores hash. The check runs that pair for a one-class run and for a two-class run. Cross-machine equality is not this check.

### Swap and stored models

- [ ] C13. `publish` writes `scores.parquet` and `bind.json` into a staging directory and puts that directory on the scores path with one `os.replace`. After a successful `publish`, the scores path holds exactly those two files, and the staging directory is gone. If that `os.replace` raises, the exception propagates, any previous scores directory's file bytes are unchanged, and the staging directory is gone. The fitted objects are locals in `publish`. They are not stored. The scores directory has no model file. `scorecheck.models` has no attribute `Booster`, `booster`, `XGBClassifier`, or `HistGradientBoostingClassifier`.

### Pins

- [ ] C14. `pyproject.toml` and `requirements.txt` pin `xgboost==3.4.1` and `scikit-learn==1.9.1` and keep `lightgbm==4.7.0`. The installed versions equal those pins. `requires-python` is `>=3.12`.

### Replaced features

- [ ] C15. `line` reads the scores from disk on each call. On a one-class publish with label 0, `line` returns probability `0.0` for `lightgbm`. After `income` changes by `1.0` and the feature file is rewritten, `line` raises `StaleScores` and does not return `0.0`. After the labels are set to 1 and `vendor.publish` then `models.publish` run again, `line` returns probability `1.0` for every probability field.

### Golden path

- [ ] C16. `tests/support/runs.py` `generate_run` still stops at `features.from_panel`. After `generate_run`, the scores path does not exist and the ledger path does not exist. A monkeypatch that makes `models.publish` raise is not triggered by `generate_run`. `scripts/write_golden_panel.py` contains a call to `features.from_panel` and does not contain `models.publish`, `scorecheck.models`, `vendor.publish`, or `scorecheck.vendor`. The stored panel golden hashes are unchanged. This feature does not add a scores hash to `tests/fixtures/golden/`.

## Out of the locked set

Cross-machine equality of LightGBM, XGBoost, or histogram scores is not a locked check. A stored golden hash of `scores.parquet` would freeze one machine's library build. This draft does not require that file.

Feature 004 owns the approval rule, the two outcome regimes, and the learning curves. Those curves use people held out of refitting. They do not read this feature's in-sample scores file as the gap. Feature 005 reports rank lift from those held-out scores. Feature 006 owns UCI 350, Home Credit, and the validation PDF. Feature 007 owns decline text. This feature does not load a public dataset, does not fit on a column named `true_default`, and does not call the explanation agent. The label it does fit is `default_label`, which Feature 001 copies from origination-month `true_default` with `label_observed` set to 1.

Eval output is advisory. It proves no check above.

## Executable tests

Every automated test that will prove the checks above, named before any product code exists. The feature builder writes these first and may not weaken them. `test_command_order` is extended to the four-call order. Its assertion still fails if `panel.generate`, `features.from_panel`, or `vendor.publish` is missing, repeated, or reordered.

Test command: `python -m pytest` from the repo root.

Coverage command: `python -m pytest tests/unit --cov=scorecheck.panel --cov=scorecheck.features --cov=scorecheck.vendor --cov=scorecheck.models --cov-report=term-missing`

Tests import `scorecheck.cli`. Importing `scorecheck.__main__` runs the default panel, so no test imports it.

| Test | File | What it asserts | Proves check |
|---|---|---|---|
| test_command_order | tests/unit/test_cli.py | On the 200-household command, the call order is `panel.generate`, `features.from_panel`, `vendor.publish`, `models.publish`, once each. | C1 |
| test_main_prints_banner_then_stages | tests/unit/test_cli.py | Monkeypatch the default scale to 200 households. `cli.main([])` returns 0. Stdout lines equal the default banner plus the six stage names. A monkeypatch that raises from `explain.draft` is not triggered. | C1 |
| test_publish_is_silent | tests/unit/test_models_publish.py | Captured stdout and stderr are empty for one one-class `publish` and one two-class `publish`. | C1 |
| test_scores_path | tests/unit/test_models_publish.py | The scores path equals `run_dir.parent.with_name("models") / run_dir.name` and contains exactly `scores.parquet` and `bind.json`. The 200-household run id is `6e6c82611fa89cf4`. The vendor directory still holds exactly its two ledger files. `data/processed` has one child. | C2 |
| test_publish_leaves_run_dir_unchanged | tests/unit/test_models_publish.py | The run directory's file names and the `application_features` logical hash are unchanged. The ledger logical hash is unchanged. The scores files are in neither directory. `vendor.publish` is not called by `models.publish`. | C3 |
| test_vendor_score_is_copied_through_the_api | tests/unit/test_models_publish.py | On a book of at most 300 applications, `vendor.score` is called once per application id, in ascending order, before any trainer. The stored `vendor_probability` equals the returned probability, absolute tolerance 0. A monkeypatch returning `0.25` stores `0.25`. This test does not run the 50,000-household command. | C4 |
| test_models_do_not_open_the_vendor_interior | tests/unit/test_models_boundary.py | No file under `src/scorecheck/models/` imports `scorecheck.vendor._private` or contains `ledger.parquet` or `pred_contrib`. If `vendor.score` raises `LedgerMissing`, no trainer is called and the scores path is absent. The same holds for `StaleLedger`. | C4 |
| test_challenger_matrix | tests/unit/test_models_publish.py | The matrix columns equal Definitions, in that order. Filling the three `external_score_*` columns with `1.0` leaves the matrix unchanged, absolute tolerance 0. Replacing the five demographics leaves the matrix unchanged, absolute tolerance 0. Added ground-truth names and `private_factor` are absent. Overwriting `default_label` changes the label and not the matrix columns. | C5 |
| test_publish_ignores_ground_truth | tests/unit/test_models_publish.py | After `vendor.publish`, deleting `ground_truth.parquet` still lets `models.publish` write scores. | C5 |
| test_external_scores_stay_null | tests/unit/test_models_publish.py | After `models.publish`, the three `external_score_*` columns are null on every row. The five demographic names stay on `application_features` and stay off the matrix. The feature-file column set is unchanged. | C6 |
| test_library_contract | tests/unit/test_models_publish.py | A two-class publish fits each of the three libraries twice, unconstrained and monotone, with the Definitions arguments and the constraint vector. The four seeds equal the `Streams` draws. A 200-household two-class publish and a 300-household two-class publish with the same run seed pass equal params. The pins and installed versions equal Definitions. | C7, C14 |
| test_weight_of_evidence_fixtures | tests/unit/test_models_scorecard.py | The level fixture returns `ln(5)`, `ln(5)`, `0`, `-ln(5)`, `-ln(5)` with and without the monotone merge, absolute tolerance `1e-12`. The merge fixture returns the five unmerged weights when `monotone` is false and the merged `ln(27/11)` / `ln(3/11)` weights when `monotone` is true, absolute tolerance `1e-12`. | C8 |
| test_scorecard_fit | tests/unit/test_models_scorecard.py | A two-class publish calls `binned_weight_of_evidence` once per matrix column, monotone only on the five named columns. Logistic `fit` receives that matrix, absolute tolerance `1e-12`. Points at `0.2` match the formula, absolute tolerance `1e-9`, and exceed points at `1/3` by 20, absolute tolerance `1e-9`. Stored points match the function of the stored probability, absolute tolerance `1e-9`. | C8 |
| test_one_class_scores | tests/unit/test_models_publish.py | With every `default_label` set to 0, no trainer or scorecard function is called, every probability is `0.0`, and `scorecard_points` is null. The same holds for label 1 with probability `1.0`. `line` returns `None` for points. `publish` does not raise and prints nothing. | C9 |
| test_line_returns_scores | tests/unit/test_models_line.py | `line` returns `ChallengerLines` equal to the scores row. The seven probabilities lie in the closed interval from 0 to 1. A monkeypatch that raises from `vendor.score` or from `lightgbm.train` is not triggered by `line`. | C10 |
| test_scores_errors | tests/unit/test_models_line.py | `line` before `publish` raises `ScoresMissing` and does not create the directory. Deleting either file raises `ScoresMissing`. An unknown `application_id` raises `models.UnknownApplicant` and both files remain. Adding `1.0` to `income` and rewriting the feature file makes `line` raise `StaleScores`. The three classes are distinct `Exception` subclasses, none subclasses another, and none subclasses a vendor ledger exception. | C10 |
| test_shadow_does_not_decide | tests/unit/test_models_boundary.py | The scores columns are exactly the Definitions list. `explain.draft` is not called. The ledger logical hash is unchanged. | C11 |
| test_same_machine_scores_hash | tests/unit/test_models_publish.py | Two subprocess publishes of the same one-class run have equal scores hashes. Two subprocess publishes of the same two-class run have equal scores hashes. The hashes use `logical_hash`. Parquet bytes may differ. | C12 |
| test_atomic_swap | tests/unit/test_models_publish.py | A successful one-class `publish` calls `os.replace` once, from a staging directory that already holds both scores files, onto the scores path. The staging directory is gone. If that `os.replace` raises, the previous scores file bytes are unchanged and the staging directory is gone. | C13 |
| test_no_stored_model | tests/unit/test_models_boundary.py | After `publish`, the scores directory has exactly two files. The module has no `Booster`, `booster`, `XGBClassifier`, or `HistGradientBoostingClassifier` attribute. | C13 |
| test_public_surface | tests/unit/test_models_boundary.py | `__all__` is exactly `publish`, `line`, `ChallengerLines`, `ScoresMissing`, `StaleScores`, and `UnknownApplicant`. | C10, C13 |
| test_replaced_features_are_not_served | tests/unit/test_models_line.py | A label-0 publish returns `lightgbm` probability `0.0`. Rewriting `income` by `1.0` makes `line` raise `StaleScores`. A later label-1 `vendor.publish` and `models.publish` return probability `1.0` on every probability field. | C15 |
| test_generate_run_stops_at_from_panel | tests/unit/test_models_boundary.py | `generate_run` returns without creating the scores path or the ledger path. A `models.publish` monkeypatch that raises is not called. | C16 |
| test_golden_script_stops_at_from_panel | tests/unit/test_models_boundary.py | The text of `scripts/write_golden_panel.py` contains `features.from_panel` and does not contain `models.publish`, `scorecheck.models`, `vendor.publish`, or `scorecheck.vendor`. The test does not run the script. The stored panel hashes are unchanged. | C16 |
| test_cli_default_run | tests/integration/test_cli_run.py | The existing 600-second default command still exits 0, prints the banner plus the six stage names, leaves one child of `data/processed`, leaves the vendor ledger's two files, leaves `external_score_*` null, and still returns a vendor probability and three reason codes. It also leaves `data/models/31a32519f30491a4/` with exactly `scores.parquet` and `bind.json`. `models.line` on an `application_id` from that file returns seven probabilities in the closed interval from 0 to 1. Equality of that row's `vendor_probability` to `vendor.score` is not this test. | C1, C2, C6, Completeness |
| test_challenger_bounds | tests/evals/test_challenger_scores.py | On a 300-household two-class publish, every stored probability is inside the closed interval from 0 to 1, and the four family names are present as columns. Advisory. It proves no locked check. | none |

Required kinds, per `docs/testing-standards.md` and the project document Testing requirements.

- Unit. The `tests/unit/` rows above. They cover the matrix, the three monotone refits, the scorecard arithmetic, the scores file, and the untouched vendor ledger. `src/scorecheck/models/` has at least 80% line coverage under the unit suite. `scorecheck.panel`, `scorecheck.features`, and `scorecheck.vendor` stay under that same coverage command. CLI glue stays outside the 80% gate and keeps the 200-household smoke test.
- Golden dataset. Not applicable for a new stored hash. The panel golden stays as Feature 001 left it. Booster scores are not stored, because those libraries differ across machines. The scorecard fixtures are unit tests with the numbers in Definitions, not a golden file.
- Eval case. `tests/evals/test_challenger_scores.py` is a pytest file, not JSON. JSON eval cases belong to Feature 007. This eval is advisory until v1 and proves no locked check.
- Integration. `test_cli_default_run` runs the real default command once. No test generates 200,000 households. The timeout stays 600 seconds.
- Coverage. `scorecheck.models` joins the 80% unit-suite gate. The command is the coverage command above.

## Integration

- [ ] `python -m scorecheck` calls `models.publish` in the same change that makes the behavior checks pass. The scores directory is the sibling `data/models/<run id>/`. `models.line` is callable on that directory and returns the vendor probability and the four families. The vendor ledger remains the sibling `data/vendor/<run id>/`.

## Regression

- [ ] `panel.generate` still writes only the seven panel files and `run_config.json`.
- [ ] `from_panel` still leaves `external_score_*` null, and neither `vendor.publish` nor `models.publish` fills them.
- [ ] `data/processed` still has one run child after the default command. The scores directory is not a child of `data/processed`.
- [ ] The default command still prints the banner and the six stage names, and nothing else. `explain.draft` still raises `RuntimeError` and the command does not call it.
- [ ] `vendor.score` still returns a probability and three reason codes. `models.publish` reaches the vendor only through that function.
- [ ] `generate_run` and `scripts/write_golden_panel.py` still stop at `from_panel`. The stored panel hashes are not regenerated.
- [ ] `test_command_order` still requires `panel.generate`, then `features.from_panel`, then `vendor.publish`, once each, before `models.publish`.
- [ ] `tests/unit/test_structure.py` still passes. Model seeds are drawn through `Streams`.

## Completeness

- [ ] A person runs `python -m scorecheck` from the repo root after `pip install -r requirements.txt`. They see the default banner and then the six stage names, and nothing else. They find one run directory under `data/processed/`, the vendor ledger under `data/vendor/31a32519f30491a4/`, and the challenger scores under `data/models/31a32519f30491a4/`. `models.line` on an `application_id` from that file returns the vendor probability, a LightGBM probability, an XGBoost probability, a histogram-boosting probability, and a scorecard probability, each with its monotone twin where the library fit one, and scorecard points on a two-class file. `application_features` still has null `external_score_*` columns. A passing unit test alone does not satisfy this check.
