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

Layer 1 seeded synthetic panel generator (households x 24 months, latent creditworthiness factor) -> canonical schema -> Layer 2 vendor black-box GBM behind a score API plus in-house challenger (monotonic GBM and points scorecard) in shadow mode, outcomes-ownership experiment, champion/challenger decision report -> Layer 3 validation pack / evidence kit (metrics + PDF) -> Layer 4 constrained LLM agent drafting decline explanations and credit memos, scored on a harness. Layers 2-3 run end to end from one command.

Data flow: Seeded generator -> panel in canonical schema -> vendor model (behind score API) and challenger models score the same applicants -> outcomes fed back per regime over 24 months -> evidence kit computes metrics and renders validation pack PDF -> Layer 4 agent reads score + reason codes + policy text and drafts explanation for human review

Integration points: Vendor score API (score + three reason codes only); LLM API for Layer 4; one public credit dataset (Home Credit Default Risk or Give Me Some Credit, licence to be checked)

Interface contracts: Documented canonical behavioural-data schema; vendor score API returns exactly a score and three reason codes; approved reason-code list and policy text for the agent; generator output is deterministic for a given seed

## Stack and dependencies

Tech stack: Python 3 with pandas and numpy for the panel, scikit-learn plus a GBM library with monotonic constraints (TODO confirm LightGBM or XGBoost) for vendor and challenger, a points-scorecard implementation, an LLM API for Layer 4, and a PDF report generator (TODO confirm)

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

- Vendor score internals: the vendor model module may only be reached through its score + three reason codes API; downstream code never reads inside it
- Canonical behavioural-data schema (documented contract the validation layer depends on, so it can later run on other models)
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

- Public repo from the first commit, with Layer 1 generator and canonical schema
- Layers 2 and 3 run end to end from one command
- README a credit analyst can run in ten minutes, with a limitations section
- Layer 4 harness with a results table (faithfulness to reason codes, reading level, policy compliance, cost and latency per decision)
- Validation pack PDF generated from the evidence kit, plus a model risk note with governance mapping checked against sources
- One public dataset run whose licence allows public redistribution of results (check Home Credit Default Risk and Give Me Some Credit terms first)

Confirm two separate things before calling a feature done: the locked checks pass, and the behavior a person actually uses exists and is connected to the rest of the app.
