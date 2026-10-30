# Features — Tool - ScoreCheck

One feature per loop. Leave the next feature at `Not started` until the current one is `Complete`.

Status values: `Not started`, `Checks in draft`, `Checks locked`, `In progress`, `Complete`.

## Feature 001 — Synthetic behavioural panel

Status: Complete

Requirements:
- Given a seed and generator config, when the panel generator runs, then the default run writes 50,000 households over 24 months and the full run writes about 200,000. The command banner, the README, and the report header state which scale ran. Behaviour and default are driven by ability, willingness, shocks, and a vendor-only signal. Ground truth stays apart from the model columns. The output conforms to `application_features`, includes the Philippine quirks (shared accounts, multiple SIMs, mostly prepaid, remittance spikes), and the same seed reproduces the same logical table.

Checks: locked in `checks/approved/feature-001.md`

## Feature 002 — Black-box vendor score API

Status: Checks locked

Requirements:
- Given a vendor gradient-boosted model trained on the panel, when downstream code requests a score for an applicant, then it receives only a score and three reason codes, with no access to the model's internals

Checks: locked in `checks/approved/feature-002.md`

## Feature 003 — In-house challenger in shadow mode

Status: Not started

Requirements:
- Given the same applicants scored by the vendor, when LightGBM, XGBoost, and histogram gradient boosting each fit unconstrained and, where the library supports it, with a monotone refit, plus the points scorecard, score them using only the data owner's features, then all four lines are recorded beside the vendor score without changing any decision

Checks: not written

## Feature 004 — Outcomes-ownership experiment

Status: Not started

Requirements:
- Given two regimes over 24 simulated months, one where repayment outcomes flow only to the vendor and one where the data owner keeps them too, when the experiment runs, then it produces learning curves showing how the vendor-versus-challenger gap moves in each regime
- The hypothesis is recorded in the report and is not a target the generator is adjusted to hit

Checks: not written

## Feature 005 — Champion and challenger decision report

Status: Not started

Requirements:
- Given vendor and challenger scores with outcomes, when the report is generated, then it shows by segment and by length of behavioural history (thin-file versus thick-file) where the vendor still adds lift, where the challenger has caught up, and what a phased switch would cost in approval rate and expected loss

Checks: not written

## Feature 006 — Lender validation pack

Status: Not started

Requirements:
- Given scores and outcomes for both models, including a simulated year-two shift (new lender channel, El Nino shock to rural incomes, telco pricing change), when the validation pack is generated, then it reports ranking performance overall and by segment, calibration by segment, PSI and characteristic-level drift, reject inference, fairness checks with a proxy-risk note, and approval and loss trade-off curves at several cut-offs, and renders them as a PDF. The default command scores UCI Default of Credit Card Clients (id 350) on its own frame. The full command scores Home Credit aggregates on their own frame. Give Me Some Credit is not used.

Checks: not written

## Feature 007 — Constrained decline-explanation agent

Status: Not started

Requirements:
- Given a score, its reason codes and the policy rules, when the agent drafts a borrower-facing decline explanation and a short credit memo, then the output uses only approved reason codes and policy text, invents no figures or reasons, is marked for human sign-off, and is scored on the harness for faithfulness, reading level, policy compliance, cost and latency

Checks: not written

