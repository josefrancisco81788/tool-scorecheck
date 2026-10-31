# Design Doc — Tool - ScoreCheck

> Filled 2026-10-26 from [PRD.md](PRD.md), [plan.md](plan.md), and [research/a-schema-reproducibility.md](research/a-schema-reproducibility.md). Decisions of 2026-10-25 in [../decisions.md](../decisions.md) override earlier wording in [../features.md](../features.md) where they differ. Checks for Feature 001 are drafted from this doc.

`features.md` and the PRD now use this contract. Default scale is 50,000 households. Full scale is about 200,000. Drivers are ability, willingness, shocks, and a vendor-only signal. Challengers are three boosters plus a scorecard. Home Credit is the full command. UCI Default of Credit Card Clients (id 350) is the default command's public file.

---

## 1. Module & File Boundaries

One package, `src/scorecheck/`, so `python -m scorecheck` is the ten-minute command. Subpackages match the layers in the plan.

| Module / Path | Responsibility | Depends on | Owned by |
|---|---|---|---|
| `src/scorecheck/config.py` | Seed, scale, month count, refit cadence, shock windows, banner sentence, column lists | nothing | human locks constants; feature code reads them |
| `src/scorecheck/__main__.py` | CLI: `--scale default\|full`. Prints the scale banner first. Default runs panel plus Taiwan file. Full runs 200,000 households plus Home Credit aggregates | all runtime modules | feature builder |
| `src/scorecheck/panel/` | Synthetic detail tables, ground truth, and the draw of ability, willingness, shocks, and the vendor-only signal | `config` | Feature 001 |
| `src/scorecheck/features/` | Build `application_features` from the panel, from UCI 350, or from Home Credit. Public rows leave alternative-data columns null. Populations are separate frames | `panel` for synthetic; files under `data/raw/` for public | Feature 001 for the synthetic row; Feature 006 for the public loaders |
| `src/scorecheck/vendor/` | Train the vendor booster on vendor columns. Public surface is `score(applicant) -> (score, reason_code, reason_code, reason_code)` | `features` | Feature 002 |
| `src/scorecheck/models/` | LightGBM, XGBoost, `HistGradientBoostingClassifier`, and the in-house scorecard. Unconstrained fit is the default. Monotone refit where the library supports it. Challenger matrices drop `external_score_*` | `features` | Feature 003 |
| `src/scorecheck/experiment/` | Two regimes, shared approval rule, learning curves on held-out people | `vendor`, `models`, `panel` ground truth | Feature 004 |
| `src/scorecheck/report/` | Champion/challenger tables by segment and by `history_months` | `experiment` outputs | Feature 005 |
| `src/scorecheck/validate/` | Ranking, calibration, PSI/CSI, reject inference, fairness, cutoff curves, year-two shift, ReportLab PDF | scores and outcomes | Feature 006 |
| `src/scorecheck/explain/` | Stub until Feature 007. Then: approved codes only, template sentences, validator, unsigned draft | vendor reason codes plus policy text | Feature 007 |
| `data/raw/` | Downloaded public files. Gitignored | — | human download; loaders read |
| `data/processed/` | Panel and feature tables for a run | writers in `panel` and `features` | the command that produced them |
| `outputs/` | Metrics, figures, PDF, run config | `validate`, `report` | the command |
| `tests/fixtures/golden/` | Small seeded panel: logical hashes and a few expected aggregates | Feature 001 | feature builder, after the first stable run |
| `README.md` | How to run the default command, the full command, the scale banner, and limitations | — | updated with Feature 001 and again with Feature 006 |

Paths the init script already reserved. Do not repurpose them:

| Path | Responsibility | Owned by |
|---|---|---|
| `checks/approved/` | Locked evaluation for the feature loop | human, after approval |
| `program.md` | Loop operating manual; Learned rules may be appended | human; auto-loop appends only |
| `features.md` | One feature per loop | build skill |
| `.cursor/skills/`, `.claude/skills/` | Project context and loop workflow | human |

Entry point for a credit analyst: `python -m scorecheck` from the repo root, after `pip install -r requirements.txt`. That process prints the banner, writes the default panel, scores it, and (once Feature 006 exists) writes the PDF. Until Feature 006 exists, the same entry point runs whatever features are already implemented and says which stages it skipped.

---

## 2. Data Model

No database and no migrations. Tables are Parquet under `data/processed/<run-id>/`, with the run config JSON beside them. Sameness tests hash the logical table (sorted rows and columns, fixed dtypes), not the file bytes.

### Detail tables (synthetic only)

Written by `panel`. Not a model matrix.

- `household`: `household_id`, `region`, `urban_rural`, `income_band`, `remittance_receiver`
- `person`: `person_id`, `household_id`, `age_years`, `role`
- `sim`: `sim_id`, `person_id`, `prepaid`, `operator_slot`
- `electricity_account`: `account_id`, `household_id`, `shared`
- `ewallet_account`: `account_id`, `household_id`, `shared`
- `month_behaviour`: `person_id`, `month` (1–24), `electricity_state` in {`on_time`, `late_before_disconnection`, `disconnected_restored_30d`, `unpaid_past_30d`}, `topup_amount` per SIM, `wallet_inflow`, `wallet_outflow`

Generator draws, stored only in ground truth: `ability` (scaled by the remittance calendar and by a region-month shock), `willingness`, an idiosyncratic shock after origination, and a vendor-only signal correlated with default. Config labels each multiplier as taken from a BSP, telco, or Meralco figure, or as an assumption. Shared-column marginals (age, income, utilization, delinquency) are calibrated to Home Credit application-time distributions. Prepaid share, multi-SIM counts, remittance shape, and electricity states use the Philippine sources in [research/b-synthetic-panel.md](research/b-synthetic-panel.md).

### `ground_truth` (synthetic only)

`person_id`, `month`, `ability`, `willingness`, shock flags, `vendor_signal`, `true_default`.

### `application_features` (the contract)

One row per application. Synthetic rows and public rows use this column list and are stored as separate frames. They are not stacked.

Core: `application_id`, `person_id`, `age_years`, `income`, `dependents`, `credit_amount`, `installment_to_income`, `utilization`, `open_credit_count`, `delinquency_count_30`, `delinquency_count_60`, `delinquency_count_90`, `history_months`, `on_time_rate`, `payment_to_obligation_ratio`, `gender`, `education`, `marital_status`, `region`, `default_label`, `label_observed`.

Vendor-only, dropped before every challenger fit: `external_score_1`, `external_score_2`, `external_score_3`. On Home Credit these are `EXT_SOURCE_*`. On the synthetic panel the three columns stay null. The vendor probability is read through `vendor.score` and is not written back onto `application_features`. Research note A proposed that write-back. JOS-24 and the locked Feature 002 checks rejected it. The drop is asserted by a test.

Alternative-data, null on every public row: `sim_count`, `prepaid_flag`, `electricity_late_rate`, `electricity_disconnect_count`, `remittance_inflow_mean`, `ewallet_net_flow_mean`, `shared_account_flag`.

On `application_features`, Feature 001 writes `label_observed` 1 on every row, and `default_label` equals origination-month `true_default`. Feature 004 records hidden outcomes in `data/experiment/<run id>/outcomes.parquet`, keyed by application, checkpoint, and regime. A hidden row has `label_observed` 0 there and an empty matured label. Refits read that table. `application_features` is not rewritten, so the Feature 002 bind stays valid. Evaluation of people held out of the fit uses `ground_truth`. `history_months` is the thin-file versus thick-file cut.

### Scale

`SCALE_DEFAULT = 50_000` households × 24 months. `SCALE_FULL = 200_000`. Refit cadence on the default command is quarterly (six checkpoints across 24 months). The banner string, owned by `config.py`, is printed by the CLI, written in the README, and placed in the PDF header: the run states which scale was used, and states that 50,000 is the default and 200,000 is the full run.

### Invariants

- No column from `ground_truth` appears in `application_features` or in any challenger matrix.
- Challenger fits do not receive `external_score_1`, `external_score_2`, or `external_score_3`.
- Synthetic, Taiwan, and Home Credit frames are scored and reported separately.
- The same seed and config produce the same logical hash. A second seed does not. Draws use `scorecheck._streams.Streams`. `Streams` is the only caller of `np.random.default_rng` in `src/`. `PYTHONHASHSEED` is fixed at process start. LightGBM uses `deterministic=True`, a forced histogram direction, and `num_threads=1`. XGBoost uses `random_state` and `n_jobs=1`. The sklearn histogram booster uses `random_state`.
- No firm or MSME entity is written.
- A decline draft from `explain` cannot set an approval flag. A person signs it.
- Adding a column to `application_features` is a schema change and needs an explicit decision before the code changes.

---

## 3. Sequence of Operations (per Acceptance Criterion)

`features.md` wording is noted where this sequence follows the 2026-10-25 decisions instead.

### Feature 001: Synthetic behavioural panel

- Given: a seed and a generator config (`scale` default or full).
- Steps: 1) `panel.generate` writes detail tables and `ground_truth`. 2) `features.from_panel` writes `application_features` with alternative-data columns filled and vendor scores empty. 3) The CLI prints the scale banner. 4) A golden fixture of a few hundred households is stored with its logical hash once the generator is stable.
- Satisfies: documented schema, Philippine quirks, known defaults, same seed reproduces the logical table. Default size is 50,000 households. Full size is about 200,000. Drivers are ability, willingness, shocks, and a vendor-only signal, not one latent factor.

### Feature 002: Black-box vendor score API

- Given: a gradient-boosted vendor model trained on the synthetic panel. Origination-month `vendor_signal` is the only private input. `external_score_*` stay null and are not training columns. Age, gender, education, marital status, and region leave the matrix. `application_profile` is not a reason code.
- Steps: 1) Training code lives under `vendor/` and is not re-exported. 2) `vendor.score` returns a float and exactly three reason codes. 3) A test imports `scorecheck.vendor` and asserts the booster object is not in the public namespace.
- Satisfies: downstream code receives only a score and three reason codes.

### Feature 003: In-house challenger in shadow mode

- Given: the same applicants the vendor scored.
- Steps: 1) `features.challenger_matrix` drops `external_score_*` and the same five demographic columns the vendor matrix drops. 2) Fit LightGBM, XGBoost, and `HistGradientBoostingClassifier` unconstrained, plus a monotone refit on utilization, delinquency counts, and installment-to-income where the library supports it. 3) Fit the in-house weight-of-evidence scorecard: ten quantile bins, adjacent merge on the five monotone columns, weight of evidence with 0.5 smoothing, logistic regression, points to double the odds 20, base points 600, base odds 50 goods to one bad. 4) Write all scores beside the vendor score, in the challenger's own artifact. 5) Do not change the approval flag.
- The scores file is an in-sample fit on a book where every `default_label` is observed. It is not the held-out vendor-versus-challenger gap. Feature 004 owns that gap. Booster scores are not stored as a golden hash.
- When Feature 003 is implemented, `requires-python` becomes `>=3.12` because `xgboost==3.4.1` requires that floor. The pins stay in the Feature 003 draft until that implementation.
- Satisfies: challengers run in shadow on the data owner's columns. All four lines are reported.

### Feature 004: Outcomes-ownership experiment

- Given: 24 synthetic months and two regimes.
- Steps: 1) Each month, approve with the vendor score using a rule frozen before that month's defaults realise. The rule does not read `true_default`. 2) Write observed and hidden outcomes to `data/experiment/<run id>/outcomes.parquet`. 3) Vendor-only regime: matured labels refit the vendor arm only through a writer inside `vendor/` that takes the run directory and the application ids allowed into that fit, and writes `data/experiment/<run id>/<regime>/` (`ledger.parquet` plus `bind.json`). The bind is the features hash plus a hash of those ids. `vendor.publish` and `vendor.score` stay the full-book Feature 002 API on `data/vendor/<run id>/`. A second reader returns the same probability and three reason codes for a regime ledger. 4) Data-owner regime: the same labels also refit the challengers under `models/` without overwriting `data/models/<run id>/`. 5) Both regimes share the approval rule. 6) Learning curves are the vendor-minus-challenger gap on people held out of refitting. Default cadence is the six quarterly checkpoints. 7) The report quotes the Notion hypothesis and prints the curves the seed produced. The Feature 003 in-sample scores file is not this gap.
- A run is not evidence if any of these is true: both arms see `external_score_*`; ability alone is enough to match the vendor; rejected defaults are used in training against the regime rule; the approval rule sees the eventual default; shocks are copied onto features with the coefficient the report then calls a finding; the generator or the hyperparameters are changed until the curves match the Notion sentence.
- Satisfies: learning curves of the gap under both regimes. Synthetic panel only.

### Feature 005: Champion and challenger decision report

- Given: vendor and challenger scores with outcomes, on one population at a time. The scores are the held-out scores from Feature 004. The Feature 003 in-sample file is not this report.
- Steps: 1) Split by segment (`region`, income band, gender, age band where non-null) and by `history_months` (thin versus thick). 2) For each split, report rank lift of the vendor over each challenger. 3) At several cut-offs, report the change in approval rate and expected loss if the cut moves from the vendor score to a named challenger.
- Satisfies: where the vendor still adds lift, where a challenger has caught up, and what a phased switch does to approval rate and expected loss.

### Feature 006: Lender validation pack

- Given: scores and outcomes, plus the year-two shift on the synthetic panel only.
- Steps: 1) Default command loads UCI 350 (`scikit-learn` / UCI id 350) into `application_features` and scores that frame separately. 2) Full command aggregates Home Credit application, bureau, and installment history into the same columns; `EXT_SOURCE_*` stay vendor-only; `DAYS_EMPLOYED == 365243` is kept as a sentinel, not median-filled; missing `EXT_SOURCE_1` is left missing. 3) Year-two shift is config: a new channel mix, a rural ability scale over a stated month range, and a telco price scale. 4) Metrics: AUC, log loss, and Brier overall and by segment; Wilson intervals on segment default rates; segments with fewer than 30 defaults marked sparse; PSI with the 0.10 / 0.25 bands and the sample-size critical value; CSI on each canonical column. 5) Reject inference on the synthetic declines only: accepted-only, hard cutoff, fuzzy augmentation, inverse-probability weights, and parcelling, each scored against `ground_truth`. 6) Fairness: approval rate and default capture by gender, age band, and region. Proxy note: association of `prepaid_flag`, `region`, and `education` with the outcome. 7) ReportLab writes the PDF. The header includes the scale banner. fpdf2 is the fallback if ReportLab fails a layout check.
- Satisfies: the validation pack, including the PDF. Give Me Some Credit is not loaded.

### Feature 007: Constrained decline-explanation agent

- Given: a score, the three vendor reason codes, and the approved code list plus policy sentences. This feature does not start until that list exists.
- Steps: 1) If no supplied code is in the approved list, return abstain and do not call the model. 2) The model may return only codes from that enum, or abstain. Sentences come from templates. Figures are interpolated in Python from the payload. 3) The validator rejects a draft whose codes are not the input set, whose numbers are absent from the payload, or whose required policy sentence is missing. 4) The draft is stored unsigned. 5) The harness records exact code-set match, Flesch-Kincaid and Coleman-Liau as diagnostics, policy-sentence presence, and cost and latency when a live call is made.
- Satisfies: no invented figure or reason, human sign-off, harness table. Model class for Features 002–006 is unchanged by this feature.

---

## 4. Immutable Zone Overlaps

- **Vendor score internals** → Training and the booster object stay inside `src/scorecheck/vendor/`. Other packages call `vendor.score` for the full-book ledger, or the Feature 004 regime reader for a regime ledger, and receive a score plus three reason codes. Downstream code does not import `vendor._private`. Feature 002's test checks that the booster object is not in the package's public namespace. The challenger drop of `external_score_*` is part of this boundary. On a public frame those columns are vendor-only inputs. On the synthetic panel they stay null. They are not a window into the booster.
- **Behavioural-data schema** → Section 2 is the schema. Feature 001 is the first writer. A later column change is a decision, then a check change, then code. The logical-hash test is the reproducibility lock. Ground truth is outside the schema the models see.
- **Approved reason-code list and policy text** → Not created in Features 001–006. `explain/` stays a stub that cannot draft. Feature 007 reads the list from a file under `src/scorecheck/explain/policy/` once a human has put the sentences there. The agent does not add codes at runtime.
- **`checks/approved/` and `MANIFEST.sha256`** → This design does not write there. The feature loop locks checks only after review, through `python scripts/lock_checks.py`.

---

## 5. Open Architectural Questions

Made decisions stay in [../decisions.md](../decisions.md). Still open:

- [ ] Confirm Home Credit row counts and that all seven tables are present when the files are first downloaded. Until that load is measured, the ten-minute command uses the synthetic default panel plus UCI 350.
- [ ] Re-quote BSP Circular 855 subsection numbers from the PDF when the model-risk note is written. The final number of the 2025 model-risk draft is unknown; cite the draft or omit a number.
- [ ] Re-check Claude API prices at Feature 007, before any price is written into the repo.
- [x] Update [../features.md](../features.md) and [PRD.md](PRD.md) to the 2026-10-25 wording (50,000 default, two traits plus shocks, three boosters plus a scorecard, Home Credit on the full command, UCI 350 on the default command).

---

## Feeds forward into

- Feature 001 checks, drafted from section 3 and the invariants in section 2
- `src/scorecheck/` layout when implementation starts
- [../decisions.md](../decisions.md) leftovers above; the decision log already holds the 2026-10-25 choices
