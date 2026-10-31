# A. Schema and reproducibility

Jose's rule, 2026-10-25: generate the model schema from attributes that the public datasets share. The list below is the proposal for the design session to lock. The schema is an immutable zone once locked.

## Findings

### The public sets share an application row, not a household panel

Claim: Home Credit, Give Me Some Credit, UCI 350, and Lending Club can all be cast to one row per application with age, income, a credit amount or limit, a debt-burden ratio, delinquency, a count of existing obligations, and a binary default. Monthly bills and payments exist only in Home Credit (relational) and UCI 350 (six wide months). An external score exists in Home Credit (`EXT_SOURCE_1/2/3`) and Lending Club (FICO). Rejected applications exist in the Lending Club reject file only.

Evidence: Give Me Some Credit columns are utilization, age, 30/60/90-day counts, debt ratio, monthly income, open lines, real-estate lines, dependents, and `SeriousDlqin2yrs`. UCI 350 has `LIMIT_BAL`, `AGE`, six `PAY_*` statuses, six `BILL_AMT*`, six `PAY_AMT*`, and `default.payment.next.month`. Home Credit's application file is one row per loan; bureau balance is one row per bureau credit per month.

Source: UCI 350 dataset page, https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients, accessed 2026-10-24. Home Credit table roles, IEEE DataPort, https://ieee-dataport.org/documents/home-credit-default-risk, accessed 2026-10-25. Give Me Some Credit field list carried in the PaMIR table, https://arxiv.org/html/2610.03259v1, accessed 2026-10-25.

Confidence: `verified` for UCI and Home Credit table roles. `likely` for the Give Me Some Credit field list (reproduced by PaMIR from the competition file).

ScoreCheck: models never see the raw Philippine detail tables. They see `application_features`. The generator aggregates detail into that row. Public loaders fill the same core columns and leave alternative-data columns null.

### Ground truth has to sit in another table

Claim: if ability, willingness, the shock draws, and the true default are columns on the model frame, every later test of leakage is already lost.

Evidence: the Notion page requires known ground truth so the testbed can measure what a score misses. https://app.notion.com/p/402087d04d3d81deb1bcf60268996523, read 2026-10-24.

Confidence: `verified` (project source of truth).

## Proposed schema

### Detail tables (synthetic only)

These exist so the Philippine quirks can be checked. They are not the training frame.

- `household`: `household_id`, `region`, `urban_rural`, `income_band`, `remittance_receiver`
- `person`: `person_id`, `household_id`, `age_years`, `role`
- `sim`: `sim_id`, `person_id`, `prepaid`, `operator_slot`
- `electricity_account`: `account_id`, `household_id`, `shared`
- `ewallet_account`: `account_id`, `household_id`, `shared`
- `month_behaviour`: `person_id`, `month`, electricity state in {on time, late before disconnection, disconnected then restored within 30 days, unpaid past 30 days}, top-up amount per SIM, wallet inflow, wallet outflow

### `ground_truth` (synthetic only, never joined into features)

`person_id`, `month`, `ability`, `willingness`, shock flags, `true_default`.

### `application_features` (the contract)

One row per application. Core columns are the ones at least two of the four public sets can fill.

| Column | Filled from |
|---|---|
| `application_id`, `person_id` | All |
| `age_years` | All four |
| `income` | All four |
| `dependents` | Home Credit, Give Me Some Credit; null if absent |
| `credit_amount` | Limit or loan amount |
| `installment_to_income` | Annuity/income, debt ratio, or payment/limit |
| `utilization` | Revolving utilization, bill/limit, or bureau debt/limit |
| `open_credit_count` | Open lines or bureau credit count |
| `delinquency_count_30`, `_60`, `_90` | Past-due counts or months in status |
| `history_months` | Months with an observed balance or bill; thin versus thick is this column |
| `on_time_rate` | Share of observed months with no delinquency |
| `payment_to_obligation_ratio` | Payment over bill or installment |
| `gender`, `education`, `marital_status`, `region` | Where the source has them, else null |
| `default_label` | Binary default as the source defines it |
| `label_observed` | 0 when the outcome is hidden (rejects) |

Status 30 Oct 2026: Feature 001 writes `label_observed` 1 on every row of `application_features`, and `default_label` equals origination-month `true_default`. Hidden outcomes for Feature 004 live in `data/experiment/<run id>/outcomes.parquet`. The row above is the proposal the locked panel did not implement. On the synthetic panel `external_score_*` stay null; the vendor probability is read through `vendor.score` and is not written back. The write-back sentence below is the earlier proposal.

Vendor-only columns, dropped before any challenger fit: `external_score_1`, `external_score_2`, `external_score_3`. On Home Credit these are `EXT_SOURCE_*`. On the synthetic panel, `external_score_1` is the vendor API score written back for the report, not a training feature for the challenger.

Alternative-data columns, null on every public row: `sim_count`, `prepaid_flag`, `electricity_late_rate`, `electricity_disconnect_count`, `remittance_inflow_mean`, `ewallet_net_flow_mean`, `shared_account_flag`.

## Recommendations

Lock this column list in the design doc before Feature 001 checks are drafted. Adding a column later is a schema change and needs an explicit decision.

## Reproducibility

What "the same seed reproduces the output" requires in this repo:

- One `numpy.random.Generator` from `np.random.default_rng(seed)`. Do not call `np.random.seed`. Status 30 Oct 2026: draws use `scorecheck._streams.Streams`; `Streams` is the only caller of `default_rng` in `src/`.
- `PYTHONHASHSEED` fixed at process start (value `0` is the usual pin).
- Pinned versions in `requirements.txt`.
- Config written next to every output (seed, scale, library versions).
- Sorts use a stable kind, or a unique key as the tie-break.
- The sameness test hashes the logical table (sorted rows and columns, fixed dtypes), not the Parquet file bytes. PyArrow embeds a writer version in the footer, so file hashes move when the library moves.
- LightGBM, when it is one of the three boosters: `deterministic=True`, `force_col_wise=True` or `force_row_wise=True`, `num_threads=1`, and a single seed. The docs say `deterministic` is for the CPU device, and that a histogram direction must be forced or the library times both and may pick differently across runs. https://lightgbm.readthedocs.io/en/latest/Parameters.html, accessed 2026-10-24. Confidence: `verified`.
- XGBoost: `random_state` set, `n_jobs=1`. The project FAQ attributes run-to-run differences to "non-determinism in floating point summation order and multi-threading." https://xgboost.readthedocs.io/en/stable/faq.html, accessed 2026-10-24. Confidence: `verified`.
- scikit-learn's histogram booster: `random_state` set. Thread count pinned if a run shows drift.

Confidence on the Parquet footer point: `likely` (PyArrow behaviour; confirm the hash helper on the first generator run).
