# C. Public dataset grain and quality

Jose's rule, 2026-10-25: ignore licensing. Judge datasets by grain and quality. Hugging Face was checked the same day.

## Findings

### Home Credit can carry the public-data chapters that need time and a vendor score

Claim: the competition file is one current application per person (on the order of 307,000 training rows and about 122 application columns) plus previous applications, bureau credits, monthly bureau status, monthly POS and card balances, and installment payments. Bureau balance alone is on the order of 27 million rows. The target rate is about 8 percent. `EXT_SOURCE_1`, `EXT_SOURCE_2`, and `EXT_SOURCE_3` are anonymized external scores. `DAYS_EMPLOYED` uses 365243 as a sentinel.

Evidence: IEEE DataPort restates the official table roles, including "one row for each month of history of every previous credit" in bureau balance. A published file inventory gives application 307,511 rows, bureau balance 27,299,925 rows, installment payments 13,605,401 rows. https://ieee-dataport.org/documents/home-credit-default-risk and https://github.com/oguzerdo/HomeCreditDefaultRisk, both accessed 2026-10-25.

Confidence: table roles `verified` (DataPort text matches the competition data description). Row counts `likely` (secondary inventory of the same files; confirm when the files are downloaded).

What it can support: ranking overall and by segment (gender, education, region, income, history length); calibration by those segments; characteristic drift across relative months in bureau balance, POS, and installments; thin versus thick as "no bureau rows" versus a long bureau history; a vendor-versus-challenger split by giving `EXT_SOURCE_*` only to the vendor arm.

What it cannot support: a 24-month learning curve of new originations, because each loan has one outcome and the month index is relative to the application, not a calendar. A labeled El Niño year cannot be aligned to these months. Reject inference is simulated by hiding labels, unless a reject file is added from somewhere else.

Quality defects to handle in the loader, not by dropping the file: the employment sentinel; missing `EXT_SOURCE_1` on a large share of rows (missingness is a thin-file signal, so do not median-fill it before the split); the target is payment difficulty on early installments, and the report must say that rather than call it 90-days-past-due.

### Give Me Some Credit is too coarse

Claim: about 150,000 training rows, 10 predictors, one cross-section, default rate about 6.7 percent (`SeriousDlqin2yrs`). No month, no external score, no region. Delinquency fields contain the sentinel values 96 and 98. Utilization has extreme values above 1.

Evidence: PaMIR harmonized table lists `gmsc` at 150,000 rows, 10 features, 6.7 percent default, geography USA. https://arxiv.org/html/2610.03259v1, accessed 2026-10-25. Sentinel codes are long-standing competition-data behaviour; treat the 96/98 point as `likely` until the file is profiled in the repo.

Confidence: size and column count `likely`. Insufficient grain `verified` from the column list.

ScoreCheck: do not build a loader for it. It cannot test drift, history length, or a vendor score.

### UCI 350 is high quality and short

Claim: 30,000 rows, no missing values, six months of repayment status, bill, and payment (April–September 2005), demographics sex, education, marriage, and age, default rate about 22 percent. Undocumented status codes include -2 and 0, and education includes 0, 5, and 6.

Evidence: "This dataset is licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) license." UCI page and API, https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients, accessed 2026-10-24. The same file is on Hugging Face as `scikit-learn/credit-card-clients` (30,000 rows), accessed 2026-10-25.

Confidence: `verified`.

ScoreCheck: this file fits inside the ten-minute command. Use it for ranking, calibration, fairness, and a six-month characteristic-drift check. Do not describe it as thin-file or as a 24-month panel. Every row is an existing cardholder.

### Lending Club has vintages and rejects, and easy leakage

Claim: accepted loans from 2007–2018 (on the order of 1.3–2.3 million depending on the cut) include `issue_d`, FICO, income, DTI, and a charged-off label. A companion reject file exists in the `wordsforthewise/lending-club` upload. Post-origination fields (payments received, last FICO, recoveries) leak if they are left in the matrix.

Evidence: Zenodo 11295916 describes 1,347,681 resolved loans with `issue_d` and `fico_n`, licence CC BY 4.0. https://zenodo.org/records/11295916, accessed 2026-10-24. Hugging Face `BuildersLab/loan-application-dataset` points at the same Kaggle Lending Club source, accessed 2026-10-25.

Confidence: `verified` for the Zenodo record. Leakage list `likely` (standard for this file; confirm columns at load).

ScoreCheck: not the primary file. It is the backup if a later round needs a real reject table or a calendar vintage. The loader must keep an explicit application-time column allow-list.

### Hugging Face does not add a better real panel

Claim: searched 2026-10-25. Relevant pages:

- `mohameddhameem/home-credit-default-risk` shows previous-credit monthly rows (`SK_ID_PREV`, `MONTHS_BALANCE`, `SK_DPD`). It is a mirror, not a new source. Do not assume the mirror contains all seven tables until they are listed.
- `scikit-learn/credit-card-clients` is UCI 350.
- `zyplai/pamir` hosts no files. The card says it fetches 19 datasets locally. Several are corporate bankruptcy or small-business, which this project does not use. Give Me Some Credit is one of the 19.
- `electricsheepafrica` Nigerian personal loans, utility bills, and telco credit files are synthetic, and the telco credit file's own sample has a `payment_consistency_score` of 0.12 on a row labeled excellent. Useful as a warning about synthetic vendor panels, not as ScoreCheck's public dataset.
- `quailrobot/credit-risk-v1-sample` is synthetic, one row per loan, with grade and interest rate. The card says the free sample is CC BY-NC-SA and the full file is paid. Grade beside interest rate is circular for a challenger test.

Evidence: dataset cards fetched 2026-10-25. PaMIR card: "This page hosts no data."

Confidence: `verified` for what those cards display.

## Recommendations

- Primary public run, full command: Home Credit application features, with bureau and installment history aggregated to the canonical columns. `EXT_SOURCE_*` go to the vendor arm only.
- Ten-minute command: UCI 350 only, beside the 50,000-household synthetic panel.
- Skip Give Me Some Credit.
- Skip Hugging Face synthetic telco and utility sets. The generator is the synthetic Philippine panel.
- Keep Lending Club off the critical path. Name it in the design doc as the optional reject-file source.
