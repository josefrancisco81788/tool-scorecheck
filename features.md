# Features — Tool - ScoreCheck

One feature per loop. Leave the next feature at `Not started` until the current one is `Complete`.

Status values: `Not started`, `Checks in draft`, `Checks locked`, `In progress`, `Complete`.

## Feature 001 — Synthetic behavioural panel

Status: Not started

Requirements:
- Given a seed and generator config, when the panel generator runs, then it writes about 200,000 households over 24 months of electricity, mobile and e-wallet records in the canonical schema, driven by one latent creditworthiness factor with known default labels and Philippine data quirks (shared accounts, multiple SIMs, mostly prepaid, remittance spikes), and the same seed reproduces identical output

Checks: not written

## Feature 002 — Black-box vendor score API

Status: Not started

Requirements:
- Given a vendor gradient-boosted model trained on the panel, when downstream code requests a score for an applicant, then it receives only a score and three reason codes, with no access to the model's internals

Checks: not written

## Feature 003 — In-house challenger in shadow mode

Status: Not started

Requirements:
- Given the same applicants scored by the vendor, when the monotonic-constrained GBM and the points scorecard score them using only the data owner's features, then both challenger scores are recorded beside the vendor score without changing any decision

Checks: not written

## Feature 004 — Outcomes-ownership experiment

Status: Not started

Requirements:
- Given two regimes over 24 simulated months, one where repayment outcomes flow only to the vendor and one where the data owner keeps them too, when the experiment runs, then it produces learning curves showing how the vendor-versus-challenger gap moves in each regime

Checks: not written

## Feature 005 — Champion and challenger decision report

Status: Not started

Requirements:
- Given vendor and challenger scores with outcomes, when the report is generated, then it shows by segment and by length of behavioural history (thin-file versus thick-file) where the vendor still adds lift, where the challenger has caught up, and what a phased switch would cost in approval rate and expected loss

Checks: not written

## Feature 006 — Lender validation pack

Status: Not started

Requirements:
- Given scores and outcomes for both models, including a simulated year-two shift (new lender channel, El Nino shock to rural incomes, telco pricing change), when the evidence kit runs, then it reports ranking performance overall and by segment, calibration by segment, PSI and characteristic-level drift, reject inference, fairness checks with a proxy-risk note, and approval and loss trade-off curves at several cut-offs, and renders them as a PDF

Checks: not written

## Feature 007 — Constrained decline-explanation agent

Status: Not started

Requirements:
- Given a score, its reason codes and the policy rules, when the agent drafts a borrower-facing decline explanation and a short credit memo, then the output uses only approved reason codes and policy text, invents no figures or reasons, is marked for human sign-off, and is scored on the harness for faithfulness, reading level, policy compliance, cost and latency

Checks: not written

