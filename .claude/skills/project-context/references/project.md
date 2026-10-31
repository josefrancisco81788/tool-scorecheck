# Project context — Tool - ScoreCheck

## Contents

1. Purpose
2. Architecture
3. Stack and dependencies
4. Conventions
5. Constraints and non-goals
6. Success

## Purpose

ScoreCheck is an open testbed for the lender's side of an alternative-data consumer credit score: it generates a synthetic Philippine behavioural panel, runs an in-house challenger in shadow mode beside a simulated black-box vendor score, and measures how the value of the model depends on who keeps the repayment outcomes. It produces a validation pack (ranking, calibration, drift, reject inference, fairness) that lets a lender or regulator see how either score behaves, plus a constrained, review-only LLM layer that drafts decline explanations from approved reason codes.

Problem: A data owner that rents a credit model built on its own behavioural data cannot measure what the vendor's black-box score is worth or what it would take to own one.

Core user story: As a data owner or lender buying an alternative-data credit score, I want to validate the vendor's black-box score against an in-house challenger on my own data so I can decide with evidence when to keep, renegotiate or replace the vendor.

Complexity tier: Complex

## Architecture

Package `src/scorecheck/`. Design contract: `docs/design.md` (2026-10-26).

Panel (ability, willingness, shocks, vendor-only signal; default 50,000 households × 24 months; full 200,000) -> `application_features` -> vendor API (score + three reason codes) and challengers in shadow (LightGBM, XGBoost, sklearn `HistGradientBoostingClassifier`, in-house scorecard; unconstrained plus a monotone refit where supported; challengers do not see `external_score_*`) -> outcomes experiment on the synthetic panel only -> decision report -> validation pack PDF (ReportLab). On the synthetic panel `external_score_*` stay null. The vendor probability is read through `vendor.score` and is not written back onto `application_features`. The Feature 003 scores file is an in-sample shadow record. The vendor-versus-challenger gap is the Feature 004 held-out curve. Feature 004 records hidden outcomes in `data/experiment/<run id>/outcomes.parquet` and regime ledgers under `data/experiment/<run id>/<regime>/`. Explanation is a later function and does not choose the model. Default command also scores UCI Default of Credit Card Clients (id 350) as a separate frame. Full command scores Home Credit aggregates as a separate frame. Populations are not stacked.

Data flow: `python -m scorecheck` prints the scale banner, writes detail tables, `ground_truth`, and `application_features`, scores, and (once Feature 006 exists) writes the PDF. Ground truth never joins into model features.

Integration points: Vendor score API (full-book `vendor.score`, or the Feature 004 regime reader; score + three reason codes only); LLM API only at Feature 007; UCI 350 on the default command; Home Credit on the full command. Give Me Some Credit is not loaded.

Interface contracts: `application_features` column list in `docs/design.md` §2; vendor score API returns exactly a score and three reason codes; approved reason-code list and policy text for the agent, created before Feature 007; generator output is deterministic for a given seed (logical-table hash).

## Stack and dependencies

Tech stack: Python 3, pandas, numpy (`scorecheck._streams.Streams` is the only caller of `np.random.default_rng` in `src/`), LightGBM, XGBoost, scikit-learn `HistGradientBoostingClassifier`, an in-house weight-of-evidence scorecard, ReportLab for the PDF (fpdf2 only if ReportLab fails layout), an LLM API at Feature 007. Not `optbinning`. Not WeasyPrint.

The loop scripts use the Python 3 standard library only. From the project root:

- `python scripts/verify_checks.py`
- `python scripts/lock_checks.py`
- `python scripts/refresh_check_manifest.py`

Do not assume other packages, CLIs, env vars, or services exist unless they are named in this file.

## Conventions

- Track work in `features.md`. Build one feature per loop.
- Write checks before implementation. Locked copies live in `checks/approved/`.
- Loop rules live in `program.md`. Recurring mistakes are appended under Learned rules after a human confirms them.
- Files listed as immutable zones need explicit human approval before any edit.

## Constraints and non-goals

### Immutable zones

- Vendor score internals: the vendor model module may only be reached through its score + three reason codes API (full-book `vendor.score`, or the Feature 004 regime reader); downstream code never reads inside it
- Behavioural-data schema (documented, with a fixed seed so every result can be reproduced)
- Approved reason-code list and policy text used by the Layer 4 agent
- checks/approved/ and MANIFEST.sha256

### Scope boundaries

- Consumer borrowers only (thin-file individuals and households); no MSME or firm-level scoring
- Synthetic data plus one public dataset only; no CreditBPO code, data, clients or methods beyond published general practice
- No Kayana, Maya or Trusting Social data or internals; the vendor score is a simulated black box and they are never named as partners or users
- Never claim the in-house model beats any real vendor; the write-up claims a decision method, not a verdict on a named company
- The Layer 4 agent may only use approved reason codes and policy text, must never invent a figure or reason, and is review-only (a human signs every decline)
- Governance mappings (EU AI Act, RA 10173, RA 9510, BSP circulars) must be checked against source text, never written from memory

### Non-goals

- MSME or firm-level credit scoring
- Any real vendor, lender or telco data
- A verdict on whether a named company's score is good or bad
- Autonomous credit decisions; the agent never issues a decline without a human
- Training foundation models

## Success

- Public repo from the first commit, with Layer 1 generator and documented schema
- Layers 2 and 3 run end to end from one command
- README a credit analyst can run in ten minutes, with a limitations section
- Layer 4 harness with a results table (faithfulness to reason codes, reading level, policy compliance, cost and latency per decision)
- Validation pack PDF generated by the repo, plus a model risk note with governance mapping checked against sources
- Default command: 50,000-household panel plus UCI 350, README states the scale. Full command: 200,000 households plus Home Credit. Give Me Some Credit is not used. Licence was set aside on 2026-10-25; grain decided the files.

Confirm two separate things before calling a feature done: the locked checks pass, and the behavior a person actually uses exists and is connected to the rest of the app.
