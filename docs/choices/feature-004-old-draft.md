> **Superseded on 2026-11-05.** Reference only, not a contract. The checks are `checks/draft/feature-004.md`; choices are `docs/choices/feature-004.md`. The 0.5 cutoff below declined 0.0% of the default book and is replaced by 0.0185.

# Checks for feature-004, the outcomes-ownership experiment

Status: draft

Feature: feature-004

Do not lock this file until a person accepts the proposals under "Decisions still open". Do not implement from this draft before that. This draft does not edit `checks/approved/`.

Synthetic panel only. No firm or MSME entity. `external_score_*` stay null on `application_features`. The vendor probability is not written onto that table. The Feature 003 scores file is an in-sample shadow record. It is not the vendor-versus-challenger gap. This feature owns that gap on people held out of refitting. `label_observed` on `application_features` stays 1. Hidden outcomes live only in `data/experiment/<run id>/outcomes.parquet`.

`vendor.publish` and `vendor.score` stay the full-book Feature 002 API on `data/vendor/<run id>/`. `scorecheck.vendor.__all__` stays the locked Feature 002 list. `scorecheck.models.__all__` stays the locked Feature 003 list. The regime writer, the regime reader, and the challenger refit are module attributes under `vendor.regime` and `models.regime`. They are absent from both `__all__` lists. Downstream code does not import `vendor._private`.

A vendor refit is not `vendor.publish`. The writer lives inside `vendor/` and writes `data/experiment/<run id>/<regime>/`. Challenger refits are code under `models/` and do not overwrite `data/models/<run id>/`.

The hypothesis sentence is recorded. It is not a target. A run that tries to match it fails. The negative AUC gap in the fixture below is a pass.

Measured on this machine on 31 Oct 2026, outside the panel, on a random 50,000 by 20 matrix with the locked trainer arguments below. One LightGBM train took 0.230 seconds. One XGBoost fit took 0.546 seconds. One `HistGradientBoostingClassifier` fit took 1.969 seconds. Repeating every refit this draft names, on the full 50,000 rows rather than on the approved subset, is still about a minute. The integration timeout stays 600 seconds. Those three timings are not expected test values.

Feature 003 measured one `logical_hash` of the 50,000-row feature file at 0.870 seconds, and a per-row `vendor.score` at about 12 hours. `experiment.run` does not call `vendor.score`. It does not hash `application_features` once per application.

## Decisions still open

Approving this draft accepts all of these. Rejecting one means revise the draft. It does not mean start implementation.

1. **Published ledger, and locked Feature 002 V3.** V3 says `vendor.score` is the only reader of `data/vendor/<run id>/`. This draft adds `scorecheck.vendor.regime.read_published`, a second reader inside `vendor/`, so the first checkpoint can load that ledger once. Locking this draft requires a person to narrow that V3 sentence and then run `python scripts/refresh_check_manifest.py`. This draft does not do that. The other choice is a cache inside `vendor.score`. That also changes `vendor/` and is not what this draft specifies.
2. **Checkpoints.** The six quarterly checkpoints are months `4, 8, 12, 16, 20, 24`.
3. **Approval cutoff.** Approve when the vendor probability is strictly less than `0.5`. The cutoff is the constant `APPROVAL_MAX_PROBABILITY`. It is not fit on labels.
4. **Holdout.** `application_id % 5 == 0` is held out of every fit. The same ids are held out in both regimes. This is not a new random stream.
5. **Gap.** The curve stores sklearn AUC, log loss, and Brier, each as vendor minus challenger. JOS-26 asks for one seed's learning curve as a golden file. This draft does not store a booster curve. Booster scores differ across machines, which is why Feature 003 stored no scores hash. The golden numbers are the sklearn fixture below. A person has to accept that deviation before lock.
6. **Vendor-only challenger.** It is fit once, on origination `default_label`, excluding the holdout, including applicants who are later declined. It is not updated when matured labels arrive. It is not read from `data/models/<run id>/`. Declined applicants' matured `true_default` stays out of every fit. Their origination `default_label` is already on the Feature 001 table.
7. **Which score is the curve.** At checkpoint `C`, approval uses the previous model: `read_published` when `C` is 4, otherwise that regime's ledger from the previous checkpoint. The curve uses the model just refit at `C`, scored on the holdout. The refit does not include the holdout.

## Definitions

`run` below means `scorecheck.experiment.run`. Unit checks use `scorecheck.config.SEED` and 300 households unless a check names another size. No test generates 200,000 households. The integration test remains the only 50,000-household run, and its timeout stays 600 seconds.

The run id is the Feature 002 run id. For seed `20261024` and 50,000 households it is `31a32519f30491a4`. For seed `20261024` and 200 households it is `6e6c82611fa89cf4`.

`scorecheck.experiment.__all__` is exactly `run`, `approve`, `gap`, `Gap`, `InvalidExperiment`, `CHECKPOINTS`, `REGIMES`, and `APPROVAL_MAX_PROBABILITY`.

`CHECKPOINTS` is the tuple `(4, 8, 12, 16, 20, 24)`. `REGIMES` is the tuple `("vendor_only", "data_owner")`. `APPROVAL_MAX_PROBABILITY` is the float `0.5`. `InvalidExperiment` is a subclass of `Exception`. It is not a subclass of `LedgerMissing`, `StaleLedger`, `ScoresMissing`, `StaleScores`, `vendor.UnknownApplicant`, or `models.UnknownApplicant`.

`approve(probability)` returns true when `float(probability) < 0.5` and false otherwise. The signature has one positional parameter. `approve(0.49)` is true. `approve(0.5)` is false. `approve(0.0)` is true. `approve(1.0)` is false.

An application is on the book at checkpoint `C` when that person's `origination_month` is less than or equal to `C`. `origination_month` is read from `person.parquet`. An application is holdout when `application_id % 5 == 0`. Application ids `5`, `10`, and `15` are holdout. Application ids `1`, `2`, `3`, `4`, and `6` are not.

The matured label of an approved non-holdout application at checkpoint `C` is `ground_truth.true_default` on the row with that `person_id` and `month == C`. It is not `default_label`. It is not recomputed from earlier months. A holdout row, a declined row, and a row not yet on the book have no matured label.

`data/experiment/<run id>/outcomes.parquet` has exactly these columns, in this order, one row per application, checkpoint, and regime. Sort is `regime`, then `checkpoint`, then `application_id`, all ascending. `mergesort` is the sort. Row count is `n_applications * 6 * 2`.

- `application_id`, int64
- `checkpoint`, int64, one of the six checkpoint months
- `regime`, the string `vendor_only` or `data_owner`
- `approved`, int64, `0` or `1`
- `label_observed`, int64, `0` or `1`
- `matured_label`, null where `label_observed` is 0, and equal to `0` or `1` where `label_observed` is 1, absolute tolerance 0

`label_observed` is 1 only when the row is approved, on the book, and not holdout. Otherwise it is 0 and `matured_label` is null. For a fixed `application_id` and `checkpoint`, the two regime rows have equal `approved`, equal `label_observed`, and equal `matured_label`. An application not yet on the book has `approved` 0.

`data/experiment/<run id>/fits.parquet` has columns `regime`, `checkpoint`, `arm`, and `fit_ids_hash`, in that order. `arm` is `vendor` or `challenger`. `fit_ids_hash` is `logical_hash` of a one-column int64 frame named `application_id` holding exactly the ids passed into that fit. Input order does not change the hash. `logical_hash([30, 10, 20])` is `761a58240947f3caf8c0af75e1e8cadf0496ed1c17cee2fdf7df3cbe2088c462`. The empty id list hashes to `1bcaeedcda3bf388ccc9cef0cb4b5e38e19d3fb03a007a5a90bc05f149691df9`. Both digests were produced by `python checks/draft/feature-004-fixtures.py` on 31 Oct 2026. Absolute tolerance does not apply to a hash. The strings are exact.

Vendor rows exist for both regimes at each of the six checkpoints. The two regimes' vendor hashes are equal at the same checkpoint. A challenger row for `data_owner` exists at each checkpoint and its hash equals that checkpoint's vendor hash. `vendor_only` has one challenger row, at checkpoint `0`, whose ids are every non-holdout application, and no challenger row at checkpoints `4` through `24`.

The fit ids at checkpoint `C` for a vendor row, and for a `data_owner` challenger row, are the applications that are on the book, approved, and not holdout at `C`. A holdout id is absent. An id with `label_observed` 0 is absent. An empty id list is allowed and uses the empty hash above. The writer then does not call a trainer. It copies the previous model's probability and three reason codes. At checkpoint 4 the previous model is the published ledger.

`data/experiment/<run id>/<regime>/` holds `ledger.parquet`, `bind.json`, and a directory `challengers`. The vendor writer creates or replaces only `ledger.parquet` and `bind.json`. It does not delete `challengers`. `challengers` holds exactly `scores.parquet` and `bind.json`.

`bind.json` parses as one object whose keys are exactly `features_hash` and `fit_ids_hash`. `features_hash` is `logical_hash` of `application_features`. `fit_ids_hash` is the hash of the ids used in the last vendor fit for a regime ledger, or the last challenger fit for a challenger bind. Parquet byte equality is not the bind.

The regime ledger has the Feature 002 ledger columns: `application_id`, `probability`, `reason_1`, `reason_2`, `reason_3`. One row per application, sorted by `application_id`. Probability is finite and inside the closed interval from 0 to 1. The three codes are distinct members of the five Feature 002 tokens. The on-disk ledger is the checkpoint-24 fit.

The challenger scores file has exactly `application_id`, `lightgbm`, `lightgbm_monotone`, `xgboost`, `xgboost_monotone`, `hist_gradient_boosting`, `hist_gradient_boosting_monotone`, and `scorecard_probability`, in that order. It has no `vendor_probability` column and no `scorecard_points` column. One row per application, sorted by `application_id`. Each probability is finite and inside the closed interval from 0 to 1. The on-disk `data_owner` file is the checkpoint-24 refit. The on-disk `vendor_only` file is the checkpoint-0 fit.

`data/experiment/<run id>/heldout_scores.parquet` has `application_id`, `checkpoint`, `regime`, `vendor_probability`, and the seven challenger probability names above, in that order. Rows are holdout applications on the book at that checkpoint. Sort is `regime`, `checkpoint`, `application_id`.

`data/experiment/<run id>/curves.parquet` has exactly these columns, in this order: `regime`, `checkpoint`, `line`, `n_holdout`, `n_positives`, `vendor_auc`, `line_auc`, `auc_gap`, `vendor_log_loss`, `line_log_loss`, `log_loss_gap`, `vendor_brier`, `line_brier`, `brier_gap`. `line` is one of the seven challenger names. Row count is `2 * 6 * 7`, which is 84. `auc_gap` is `vendor_auc - line_auc`. The same subtraction defines the log-loss gap and the Brier gap. Absolute tolerance is `1e-12`. When `n_positives` is 0 or equals `n_holdout`, the six metric cells are null and the row is still present. The writer does not drop a negative gap and does not train again to change it.

`Gap` is a named tuple with fields `auc`, `log_loss`, and `brier`, each vendor minus challenger. `gap(labels, vendor_probability, challenger_probability)` returns `None` when `labels` has fewer than two distinct values. It does not raise and it does not call a trainer. Otherwise it returns `roc_auc_score`, `log_loss`, and `brier_score_loss` from scikit-learn `1.9.1`, vendor minus challenger, absolute tolerance `1e-12` against calling those three functions.

The fixture labels are `0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1`. The vendor scores are `0.20, 0.30, 0.25, 0.40, 0.35, 0.45, 0.55, 0.50, 0.60, 0.48, 0.70, 0.42`. The challenger scores are `0.10, 0.15, 0.12, 0.18, 0.20, 0.22, 0.80, 0.85, 0.78, 0.90, 0.88, 0.83`. All three arrays are float64 except the labels, which are int64. On 31 Oct 2026, sklearn `1.9.1` returned:

- vendor AUC `0.9722222222222223`, log loss `0.5139083833436667`, Brier `0.16556666666666667`
- challenger AUC `1.0`, log loss `0.17661799762264355`, Brier `0.027658333333333337`
- gaps AUC `-0.02777777777777768`, log loss `0.3372903857210232`, Brier `0.13790833333333333`

The AUC gap is negative. The challenger ranks this fixture better than the vendor. That result is a pass.

`data/experiment/<run id>/hypothesis.txt` is UTF-8 and its exact text, including the final newline, is the two lines below.

```
The vendor leads early, and the gap narrows only in the regime where the data owner keeps the outcomes.
This sentence is a hypothesis. It is not a target. The curves are the ones this seed produced.
```

The sentence is the one research note D quotes from the Notion page, read 2026-10-24. This draft does not assert that the curves match it.

Vendor refit training columns are the Feature 002 fit columns, including derived `private_factor` equal to origination-month `vendor_signal`, and excluding `external_score_*`, the five demographic columns, `default_label`, `label_observed`, `ability`, `willingness`, `true_default`, `region_month_shock`, `post_origination_shock`, and `vendor_signal`. The label is the matured label, in `application_id` order. A two-class vendor refit uses the Feature 002 LightGBM arguments: `objective` `binary`, `deterministic` true, `force_row_wise` true, `device_type` `cpu`, `num_threads` 1, `feature_fraction` 1, `bagging_fraction` 1, `bagging_freq` 0, `num_leaves` 15, `learning_rate` 0.1, `verbose` -1, the four seeds equal to `int(Streams(seed, "vendor")("lightgbm").integers(0, 2**31))`, and `num_boost_round` 40. There is no `monotone_constraints` key and no early stopping. Every checkpoint uses that same integer. A one-class matured label does not call `lightgbm.train` or `lightgbm.Dataset`. Probability is `0.0` or `1.0` as in Feature 002, and the reason codes are `credit_stress`, `capacity`, `thin_file`.

Challenger refit training columns are the Feature 003 matrix, in that order. `external_score_*`, the five demographics, `private_factor`, `ability`, `willingness`, `true_default`, and both shock flags are absent. A two-class refit uses the Feature 003 unconstrained and monotone arguments for LightGBM, XGBoost, and `HistGradientBoostingClassifier`, including the same `Streams(seed, "models")` integers, and the same scorecard: ten quantile bins, adjacent merge on the five monotone columns, weight of evidence with 0.5 smoothing, logistic regression `C` 1.0, `solver` `lbfgs`, `max_iter` 500. The label is the matured label for a checkpoint refit. The `vendor_only` checkpoint-0 fit uses origination `default_label` instead. A one-class label does not call those trainers. Each probability column is that observed rate, and `scorecard_probability` is that rate.

Forbidden columns on `application_features`, each of which makes `run` raise `InvalidExperiment` before any fit and before any experiment directory is created: `ability`, `willingness`, `vendor_signal`, `true_default`, `region_month_shock`, `post_origination_shock`, `private_factor`. `external_score_*` may be present. They stay out of both matrices. Filling them with `1.0` leaves both training matrices unchanged, absolute tolerance 0.

`read_published(run_dir)` returns a frame with columns `application_id`, `probability`, `reason_1`, `reason_2`, `reason_3`, sorted by `application_id`, one row per application. Before `vendor.publish` it raises `LedgerMissing` and does not create a directory. After publish it calls `logical_hash` once and reads the published ledger once. It does not call `lightgbm.train`. On a 300-household book its probability and three codes equal `vendor.score` for every id, absolute tolerance 0 on the probability.

`vendor.regime.read(run_dir, regime, application_id)` returns a `VendorDecision`. It checks `features_hash`. A mismatch raises `StaleLedger`. A missing ledger file raises `LedgerMissing`. An unknown id raises `vendor.UnknownApplicant`. It does not call `lightgbm.train`. `vendor.regime.write` and `models.regime.refit` are the writers. `models.publish` and `models.line` are not called by `run`.

On a 300-household `run`, `logical_hash` is called at most 40 times. That budget is one `read_published`, twelve vendor binds, one frozen challenger bind, and six data-owner challenger binds, with room for a second hash on each bind. It is not once per application.

A two-class book, for the call-count check, is a 300-household run whose matured labels on the fit ids have both classes at every checkpoint, and whose origination `default_label` has both classes on the non-holdout ids. The test may overwrite `true_default` and `default_label` and may replace `read_published` with known probabilities so the approved set is determined. A natural 300-household draw is not required to be that book.

`match_hypothesis=True` raises `InvalidExperiment` before any trainer call and before the experiment directory is created. The default is false.

## Behavior

### Command

- [ ] E1. `python -m scorecheck` calls `panel.generate`, then `features.from_panel`, then `vendor.publish`, then `models.publish`, then `experiment.run`, in that order, once each. `explain.draft` is not called. Printing the stage name `experiment` is not a call to `experiment.run`. `run` writes nothing to stdout and nothing to stderr. After the scale banner, stdout is the six stage names `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`, one per line, and nothing else. `test_command_order` records that five-call order. The first four names stay `panel.generate`, `features.from_panel`, `vendor.publish`, and `models.publish`, once each.

### Outcomes

- [ ] E2. After `run`, `data/experiment/<run id>/outcomes.parquet` matches Definitions. `application_features` is not rewritten. Its logical hash is unchanged. `label_observed` on that table is 1 on every row. `default_label` is unchanged. Checkpoint 4 `approved` is 1 exactly for applications on the book whose `read_published` probability is strictly less than 0.5. An application with `origination_month` 18 has `approved` 0 at checkpoints 4, 8, 12, and 16.

### Approval rule

- [ ] E3. `approve` matches Definitions. A spy on `approve` during `run` sees one float per decision and no label argument. Two runs that share `application_features` and the published ledger, and differ by replacing every `true_default` with `1 - true_default`, have equal `approved` values at checkpoint 4. Later checkpoints are not required to match, because later approval uses a model fit on earlier matured labels.

### Two regimes

- [ ] E4. Both regime names are present. Shared columns match across regimes at the same application and checkpoint. Vendor `fit_ids_hash` matches across regimes at the same checkpoint. `data_owner` challenger hashes equal those vendor hashes. `vendor_only` has the single checkpoint-0 challenger row from Definitions and no later challenger row. `vendor.publish` is not called by `run`.

### Regime vendor writer and reader

- [ ] E5. `vendor.regime.write` is called once per regime per checkpoint. After `run`, each regime directory matches Definitions. `read` returns the checkpoint-24 ledger row for an id in that ledger and does not call `lightgbm.train`. Deleting `ledger.parquet` or `bind.json` makes `read` raise `LedgerMissing`. An unknown id raises `vendor.UnknownApplicant` and both files remain. Adding `1.0` to `income` and rewriting `application_features` makes `read` raise `StaleLedger`. The published directory `data/vendor/<run id>/` still holds exactly `ledger.parquet` and `bind.json`, and its logical hash is unchanged. `vendor.__all__` is unchanged. No file outside `src/scorecheck/vendor/` imports `scorecheck.vendor._private`.

### Challenger refit paths

- [ ] E6. `models.regime.refit` writes `data/experiment/<run id>/<regime>/challengers/` and does not write under `data/models/<run id>/`. After `run`, `data/models/<run id>/` still holds exactly `scores.parquet` and `bind.json`, and that scores logical hash is unchanged when `models.publish` ran before `run`. A file under `src/scorecheck/models/` does not contain the text `ledger.parquet` and does not import `vendor._private`. `models.__all__` is unchanged. `run` does not call `models.publish` or `models.line`. Deleting `data/models/<run id>/` before `run` still produces `curves.parquet`. The checkpoint-0 `refit` receives origination `default_label` on the non-holdout ids, integer equality. A later `data_owner` `refit` receives that checkpoint's matured labels, integer equality. Changing only post-origination `true_default` leaves the label vector of the checkpoint-0 refit unchanged.

### Held-out curves

- [ ] E7. `heldout_scores.parquet` and `curves.parquet` match Definitions. The holdout rows are exactly `application_id % 5 == 0` and on the book. `gap` on the fixture returns the three documented gaps, absolute tolerance `1e-12`, and those gaps equal the sklearn subtractions. `gap` on an all-zero label returns `None`. For a holdout application, `vendor_only` challenger probabilities are equal across the checkpoints where that application is on the book, absolute tolerance 0. Vendor probabilities for the same application, checkpoint, and the two regimes are equal, absolute tolerance 0. `hypothesis.txt` equals Definitions. No curve row is deleted because the gap is negative.

### Invalidation

- [ ] E8. Each of these fails the run. The failure is `InvalidExperiment`, or a spy assertion that a passing implementation must satisfy. Matching the hypothesis sentence is not a pass.
  - Both arms seeing `external_score_*`: filling the three columns with `1.0` leaves the vendor matrix and the challenger matrix unchanged, absolute tolerance 0. A training matrix that contains one of those names raises `InvalidExperiment` before `lightgbm.train`.
  - Ability alone: `ability` is not a training column. `config.ability_default_weight` is unchanged by `run`. Adding a column named `ability` to `application_features` raises `InvalidExperiment` and does not create the experiment directory.
  - Rejected matured defaults in a fit: each vendor hash, and each `data_owner` challenger hash, equals `logical_hash` of the approved non-holdout ids from Definitions. Holdout ids are absent. `vendor_only` has no challenger row after checkpoint 0. An id with `label_observed` 0 is absent from those id lists.
  - Approval seeing the eventual default: E3. `approve` has no label parameter.
  - Shocks copied onto features: the `application_features` logical hash is unchanged. `config.TUNING` is unchanged. `hypothesis.txt` is the two sentences in Definitions and contains no digit. `curves.parquet` has no column whose name contains `shock`. `panel.generate` is not called by `run`.
  - A tuned-to-hypothesis run: `run(run_dir, match_hypothesis=True)` raises `InvalidExperiment`, calls no trainer, and does not create the experiment directory. With the flag false, `run` calls `vendor.regime.write` twelve times and `models.regime.refit` seven times: one checkpoint-0 `vendor_only` refit and six `data_owner` refits. On a two-class fit, each `write` calls `lightgbm.train` exactly once, and each `refit` calls `lightgbm.train` exactly twice and constructs `XGBClassifier` and `HistGradientBoostingClassifier` exactly twice. There is no further trainer call. Every call uses the Definitions arguments, including the seeds. A call whose `num_leaves`, `max_leaves`, `max_leaf_nodes`, `learning_rate`, or `n_estimators` differs fails this check. The fixture AUC gap is negative and `gap` returns that negative number. The test may replace the score source used for approval so that every checkpoint sees the same injected probabilities and every fit id set stays two-class.

### Batch read and the 600 second command

- [ ] E9. `read_published` matches Definitions. `run` does not call `vendor.score`. On a 300-household `run`, `logical_hash` is called at most 40 times. The integration test's timeout argument stays 600. `python -m scorecheck` still runs the real `experiment.run`, including all six checkpoints and both regimes, and still exits 0 inside that timeout.

### In-sample file

- [ ] E10. `run` does not read `data/models/<run id>/scores.parquet`. It succeeds when that file is absent. The curve's vendor probability is the regime ledger's probability, not the Feature 003 `vendor_probability` column. On a book of more than 300 applications the Feature 003 column is the constant `0.5`; the checkpoint-24 regime probability for a two-class refit is not required to differ from `0.5` on every row. The lock is that `models.line` is not called.

### Schema left in place

- [ ] E11. After `run` and after `python -m scorecheck`, `external_score_1`, `external_score_2`, and `external_score_3` are null on every `application_features` row. That table gains no column. No column written under `data/experiment/` has a name containing `firm` or `msme`, compared case-insensitively. `ground_truth` is not a column of either training matrix.

### Same machine

- [ ] E12. Two `run` calls on the same run, in two subprocesses on one machine, write equal `outcomes.parquet` values, equal `curves.parquet` float columns at absolute tolerance 0, and equal hypothesis text. Parquet bytes may differ. Cross-machine equality is not this check. A stored golden of `curves.parquet` is not this check.

### No stored booster

- [ ] E13. Regime directories contain no model file. `scorecheck.vendor` has no attribute `Booster` or `booster`. `scorecheck.experiment` has no attribute `Booster`, `XGBClassifier`, or `HistGradientBoostingClassifier`. Fitted objects are locals. `src/scorecheck/experiment/` does not contain the text `ledger.parquet` and does not contain `default_rng`.

## Out of the locked set

A stored golden of one seed's booster learning curve is not a locked check. The sklearn fixture is the numeric lock. Same-machine equality of the curve table is E12.

Feature 005 owns segment rank lift, thin-file versus thick-file, and the approval-rate and expected-loss cost of a phased switch. This feature does not write that report. Feature 006 owns UCI 350, Home Credit, and the validation PDF. Feature 007 owns decline text. This feature does not call `explain.draft` and does not set an approval flag on `application_features`. The `approved` column exists only on the outcomes table.

Eval output is advisory. It proves no check above. It must not assert that the vendor leads early or that the gap narrows in `data_owner`.

## Executable tests

Every automated test that will prove the checks above, named before any product code exists. The feature builder writes these first and may not weaken them. `test_command_order` is extended to the five-call order. Its assertion still fails if any of the first four calls is missing, repeated, or reordered.

Test command: `python -m pytest` from the repo root.

Fixture command: `python checks/draft/feature-004-fixtures.py` from the repo root. It exits 0 when the quoted floats and hashes still match scikit-learn and `logical_hash`.

Coverage command: `python -m pytest tests/unit --cov=scorecheck.panel --cov=scorecheck.features --cov=scorecheck.vendor --cov=scorecheck.models --cov=scorecheck.experiment --cov-report=term-missing`

Tests import `scorecheck.cli`. Importing `scorecheck.__main__` runs the default panel, so no test imports it.

| Test | File | What it asserts | Proves check |
|---|---|---|---|
| test_command_order | tests/unit/test_cli.py | On the 200-household command, the call order is `panel.generate`, `features.from_panel`, `vendor.publish`, `models.publish`, `experiment.run`, once each. | E1 |
| test_main_prints_banner_then_stages | tests/unit/test_cli.py | Monkeypatch the default scale to 200 households. `cli.main([])` returns 0. Stdout lines equal the default banner plus the six stage names. A monkeypatch that raises from `explain.draft` is not triggered. | E1 |
| test_run_is_silent | tests/unit/test_experiment_run.py | Captured stdout and stderr of `run` are empty. | E1 |
| test_outcomes_table | tests/unit/test_experiment_outcomes.py | Columns, sort, row count, shared regime values, `label_observed` rule, and null matured labels match Definitions. Checkpoint 4 `approved` matches `approve` of `read_published`. An `origination_month` of 18 is unapproved at checkpoints 4, 8, 12, and 16. | E2, E4 |
| test_features_table_is_not_rewritten | tests/unit/test_experiment_outcomes.py | The `application_features` logical hash, `default_label`, and `label_observed` are unchanged. `label_observed` is 1 on every row. `external_score_*` are null. No column was added. | E2, E11 |
| test_approve_cutoff | tests/unit/test_experiment_outcomes.py | `approve(0.49)` is true, `approve(0.5)` is false, `approve(0.0)` is true, and `approve(1.0)` is false. The signature has one positional parameter. | E3 |
| test_checkpoint_four_ignores_true_default | tests/unit/test_experiment_outcomes.py | Flipping every `true_default` leaves checkpoint 4 `approved` unchanged. A spy shows `approve` was called with one float. | E3, E8 |
| test_fit_hashes | tests/unit/test_experiment_regimes.py | Vendor hashes match across regimes. `data_owner` challenger hashes match them. `vendor_only` has one challenger row at checkpoint 0 whose hash is the non-holdout id list. `logical_hash` of ids `30, 10, 20` is `761a58240947f3caf8c0af75e1e8cadf0496ed1c17cee2fdf7df3cbe2088c462`. The empty hash is `1bcaeedcda3bf388ccc9cef0cb4b5e38e19d3fb03a007a5a90bc05f149691df9`. | E2, E4, E8 |
| test_regime_reader | tests/unit/test_vendor_regime.py | `read` returns the ledger row, calls no trainer, and raises `LedgerMissing`, `UnknownApplicant`, and `StaleLedger` in the Definitions cases. The published vendor directory's file hash is unchanged. | E5 |
| test_public_surface_unchanged | tests/unit/test_experiment_boundary.py | `vendor.__all__` and `models.__all__` equal the locked lists. `experiment.__all__` equals Definitions. Neither package gains a `Booster` attribute. | E5, E6, E13 |
| test_no_private_import | tests/unit/test_experiment_boundary.py | No file outside `src/scorecheck/vendor/` contains the contiguous text `scorecheck.vendor._private`. The test splits that string the way `test_vendor_boundary.py` does. `src/scorecheck/models/` does not contain `ledger.parquet`. `src/scorecheck/experiment/` does not contain `ledger.parquet` or `default_rng`. | E5, E6, E13 |
| test_challenger_path | tests/unit/test_models_regime.py | Challenger files are under `data/experiment/<run id>/<regime>/challengers/` with the Definitions columns. `data/models/<run id>/` is unchanged. `models.line` and `models.publish` are not called. Deleting the Feature 003 scores file still yields a curve. | E6, E10 |
| test_frozen_challenger_uses_origination_label | tests/unit/test_models_regime.py | The checkpoint-0 refit label equals origination `default_label` on the non-holdout ids. A later `data_owner` refit label equals that checkpoint's matured labels. Changing only post-origination `true_default` leaves the checkpoint-0 label vector unchanged. | E6 |
| test_gap_fixture | tests/unit/test_experiment_curves.py | `gap` on the fixture equals the documented vendor, challenger, and gap triples, absolute tolerance `1e-12`, and equals `roc_auc_score`, `log_loss`, and `brier_score_loss` subtracted as in Definitions. The AUC gap is negative. An all-zero label returns `None`. | E7, E8 |
| test_curves_and_hypothesis | tests/unit/test_experiment_curves.py | 84 curve rows, the column list, holdout membership, equal regime vendor probabilities, constant `vendor_only` challenger probabilities across checkpoints, and the exact hypothesis text. No metric row is absent because a gap is negative. | E7 |
| test_external_scores_do_not_enter | tests/unit/test_experiment_invalid.py | Filling `external_score_*` with `1.0` leaves both training matrices unchanged, absolute tolerance 0. A matrix that includes one of those names raises `InvalidExperiment` before `lightgbm.train`. | E8, E11 |
| test_ability_column_is_invalid | tests/unit/test_experiment_invalid.py | Adding `ability` raises `InvalidExperiment` and creates no experiment directory. `ability_default_weight` and `TUNING` are unchanged. `ability` is absent from both matrices on a valid run. | E8 |
| test_rejected_ids_are_out_of_the_fit | tests/unit/test_experiment_invalid.py | Each vendor and `data_owner` challenger hash equals the approved non-holdout id hash. Holdout ids `5`, `10`, and `15` are absent from that id list. | E8 |
| test_shocks_are_not_findings | tests/unit/test_experiment_invalid.py | The feature-file logical hash is unchanged. The hypothesis text has no digit. No curve column name contains `shock`. `panel.generate` is not called. | E8 |
| test_match_hypothesis_fails | tests/unit/test_experiment_invalid.py | `match_hypothesis=True` raises `InvalidExperiment`, calls no trainer, and creates no experiment directory. | E8 |
| test_trainer_contract | tests/unit/test_experiment_invalid.py | `write` is called twelve times and `refit` seven times. On a two-class fit, each `write` calls `lightgbm.train` once and each `refit` calls it twice, with two `XGBClassifier` and two `HistGradientBoostingClassifier` constructions. Arguments and seeds equal Definitions. No further trainer call is made. | E8 |
| test_read_published_is_one_hash | tests/unit/test_vendor_regime.py | Before `vendor.publish`, `read_published` raises `LedgerMissing`. After publish: one `logical_hash` call, one ledger read, no `lightgbm.train`. On 300 households the frame equals `vendor.score` for every id, absolute tolerance 0. | E5, E9 |
| test_run_does_not_score_per_row | tests/unit/test_experiment_run.py | `vendor.score` is not called. On 300 households `logical_hash` is called at most 40 times. | E9 |
| test_integration_timeout_stays_600 | tests/unit/test_experiment_boundary.py | The text of `tests/integration/test_cli_run.py` contains `timeout=600`. | E9 |
| test_same_machine_curves | tests/unit/test_experiment_curves.py | Two subprocess runs write equal outcomes, equal curve floats at absolute tolerance 0, and equal hypothesis text. | E12 |
| test_no_stored_model | tests/unit/test_experiment_boundary.py | After `run`, no file under the experiment run id has a booster suffix or a name `model.txt`. The experiment module has no booster attribute. | E13 |
| test_generate_run_stops_at_from_panel | tests/unit/test_experiment_boundary.py | `generate_run` does not create `data/experiment`. A `run` monkeypatch that raises is not called. | Regression |
| test_golden_script_stops_at_from_panel | tests/unit/test_experiment_boundary.py | `scripts/write_golden_panel.py` contains `features.from_panel` and does not contain `experiment.run` or `scorecheck.experiment`. The test does not run the script. | Regression |
| test_cli_default_run | tests/integration/test_cli_run.py | The existing 600-second default command still exits 0 and keeps every assertion it has now. It also leaves `data/experiment/31a32519f30491a4/` with `outcomes.parquet`, `fits.parquet`, `heldout_scores.parquet`, `curves.parquet`, and `hypothesis.txt`, plus both regime ledgers and both challenger directories. `label_observed` on `application_features` is 1. `external_score_*` are null. `data/models/31a32519f30491a4/` and `data/vendor/31a32519f30491a4/` still hold exactly their two files each. `hypothesis.txt` equals Definitions. Curve row count is 84. | E1, E2, E7, E9, E11, Completeness |
| test_outcomes_bounds | tests/evals/test_outcomes_experiment.py | On a 300-household run, every stored probability is inside the closed interval from 0 to 1. The test does not assert the sign of `auc_gap`. Advisory. It proves no locked check. | none |

Required kinds, per `docs/testing-standards.md`.

- Unit. The `tests/unit/` rows above. They cover the approval rule, the outcomes table, the two regimes, the regime reader, the challenger path, the held-out curve, and the invalidation list. `src/scorecheck/experiment/` has at least 80% line coverage under the unit suite. `scorecheck.panel`, `scorecheck.features`, `scorecheck.vendor`, and `scorecheck.models` stay under that same coverage command. `vendor/regime.py` and `models/regime.py` are inside those packages. CLI glue stays outside the 80% gate and keeps the 200-household smoke test.
- Golden dataset. The sklearn fixture and the two fit-id hashes above are the golden numbers. They are not a new file under `tests/fixtures/golden/`. A booster learning curve is not stored. Reason: LightGBM, XGBoost, and the histogram booster differ across machines, the same reason Feature 003 gave for storing no scores hash. A person approves this when they approve the draft. The panel golden stays as Feature 001 left it.
- Eval case. `tests/evals/test_outcomes_experiment.py` is a pytest file, not JSON. JSON eval cases belong to Feature 007. This eval is advisory until v1 and proves no locked check.
- Integration. `test_cli_default_run` runs the real default command once, including `experiment.run`. No test generates 200,000 households. The timeout stays 600 seconds.
- Coverage. `scorecheck.experiment` joins the 80% unit-suite gate. The command is the coverage command above.

## Integration

- [ ] `python -m scorecheck` calls `experiment.run` in the same change that makes the behavior checks pass. The outcomes table, the curve, the hypothesis file, and both regime ledgers are under `data/experiment/<run id>/`. `vendor.regime.read` is callable on a regime ledger and returns a probability and three reason codes. The Feature 002 ledger and the Feature 003 scores directory stay where they are.

## Regression

- [ ] `panel.generate` still writes only the seven panel files and `run_config.json`.
- [ ] `from_panel` still leaves `external_score_*` null, and `run` does not fill them.
- [ ] `data/processed` still has one run child after the default command. The experiment directory is not a child of `data/processed`.
- [ ] The default command still prints the banner and the six stage names, and nothing else. `explain.draft` still raises `RuntimeError` and the command does not call it.
- [ ] `vendor.score` still returns a probability and three reason codes. `vendor.__all__` is still the locked list. `models.__all__` is still the locked list.
- [ ] `generate_run` and `scripts/write_golden_panel.py` still stop at `from_panel`. The stored panel hashes are not regenerated.
- [ ] `test_command_order` still requires `panel.generate`, then `features.from_panel`, then `vendor.publish`, then `models.publish`, once each, before `experiment.run`.
- [ ] `tests/integration/test_cli_run.py` still passes `timeout=600`.
- [ ] `tests/unit/test_structure.py` still passes. New draws, if any, go through `Streams`. The holdout rule does not draw.

## Completeness

- [ ] A person runs `python -m scorecheck` from the repo root after `pip install -r requirements.txt`. They see the default banner and then the six stage names, and nothing else. They find one run directory under `data/processed/`, the vendor ledger under `data/vendor/31a32519f30491a4/`, the challenger scores under `data/models/31a32519f30491a4/`, and the experiment under `data/experiment/31a32519f30491a4/`. That experiment directory has the outcomes table, a curve of 84 rows, the hypothesis sentences, and a ledger plus a challenger file for `vendor_only` and for `data_owner`. `vendor.regime.read` on an `application_id` from a regime ledger returns a probability and three reason codes. `application_features` still has `label_observed` 1 and null `external_score_*` columns. The curve is allowed to show a negative gap. A passing unit test alone does not satisfy this check.
