# Features — Tool - ScoreCheck

One feature per loop. Leave the next feature at `Not started` until the current one is `Complete`.

Status values: `Not started`, `Checks in draft`, `Checks locked`, `In progress`, `Complete`.

## Feature 001 — Synthetic behavioural panel

Status: Complete

Requirements:
- Given a seed and generator config, when the panel generator runs, then the default run writes 50,000 households over 24 months and the full run writes about 200,000. The command banner, the README, and the report header state which scale ran. Behaviour and default are driven by ability, willingness, shocks, and a vendor-only signal. Ground truth stays apart from the model columns. The output conforms to `application_features`, includes the Philippine quirks (shared accounts, multiple SIMs, mostly prepaid, remittance spikes), and the same seed reproduces the same logical table.

Checks: locked in `checks/approved/feature-001.md`

## Feature 002 — Black-box vendor score API

Status: Complete

Requirements:
- Given a vendor gradient-boosted model trained on the panel, when downstream code requests a score for an applicant, then it receives only a score and three reason codes, with no access to the model's internals

Checks: locked in `checks/approved/feature-002.md`

## Feature 003 — In-house challenger in shadow mode

Status: Complete

Requirements:
- Given the same applicants scored by the vendor, when LightGBM, XGBoost, and histogram gradient boosting each fit unconstrained and, where the library supports it, with a monotone refit, plus the points scorecard, score them using only the data owner's features, then all four lines are recorded beside the vendor score without changing any decision
- The scores file is an in-sample shadow record on a fully labelled book. It is not the held-out vendor-versus-challenger gap. Features 004 and 005 own that gap

Checks: locked in `checks/approved/feature-003.md`

Results: `results/feature-003/`

## Feature 004 — Outcomes-ownership experiment

Status: Complete

Requirements:
- Given two regimes over 24 simulated months, one where repayment outcomes flow only to the vendor and one where the data owner keeps them too, when the experiment runs, then it produces learning curves showing how the vendor-versus-challenger gap moves in each regime
- An account is bad if it defaults within 6 months of origination, counted only once it has been on the book 6 months
- Every point on the curve is measured on the same target: the whole holdout, including applicants the lender would decline, against that 6-month outcome. A point moves only because the models changed
- Each point reports training size, the number of bads in each fit and in the holdout, and a confidence interval on the gap
- A random 5% of the applicants the cutoff would decline are approved as a test cell and tracked, so their real outcomes exist for Features 005 and 006
- The hypothesis is recorded in the report and is not a target the generator is adjusted to hit
- Hidden outcomes live in `data/experiment/<run id>/outcomes.parquet`, keyed by application, checkpoint, and regime. A hidden row has `label_observed` 0 there and an empty matured label. `application_features` is not rewritten
- A vendor refit is a writer inside `vendor/` that takes the run directory and the application ids allowed into that fit, and writes `data/experiment/<run id>/<regime>/`. It is not another `vendor.publish`. Challenger refit code stays under `models/` and does not overwrite `data/models/<run id>/`
- The simulated lender's cutoff is re-pinned to decline about 20% each time the vendor is refit; it uses scores only

Checks: locked in `checks/approved/feature-004.md`. Engineering choices: `docs/choices/feature-004.md`

Results: `results/feature-004/`

## Feature 005 — Champion and challenger decision report

Status: Complete

Requirements:
- Given vendor and challenger scores with outcomes, when the report is generated, then it shows by segment and by length of behavioural history (thin-file versus thick-file) where the vendor still adds lift, where the challenger has caught up, and what a phased switch would cost in approval rate and expected loss
- A swap-set analysis: which applicants the challenger would approve that the champion declines (swap-ins) and the reverse (swap-outs), with the size and bad rate of each group. Swap-in risk uses the Feature 004 test-cell outcomes where they exist
- Bad rate and expected loss at an equal approval rate: with the approval rate held the same, how many fewer defaults, or how much lower expected loss, the challenger delivers. AUC alone is not the decision

Checks: locked in `checks/approved/feature-005.md`. Engineering choices: `docs/choices/feature-005.md`

Results: `results/feature-005/`

## Feature 006 — Lender validation pack

Status: Not started

Requirements:
- Given scores and outcomes for both models, including a simulated year-two shift (new lender channel, El Nino shock to rural incomes, telco pricing change), when the validation pack is generated, then it reports ranking performance overall and by segment, calibration by segment, PSI and characteristic-level drift, reject inference, fairness checks with a proxy-risk note, and approval and loss trade-off curves at several cut-offs, and renders them as a PDF. The default command scores UCI Default of Credit Card Clients (id 350) on its own frame. The full command scores Home Credit aggregates on their own frame. Give Me Some Credit is not used.
- Ranking is reported as AUC, Gini, and KS
- Calibration is checked by segment: whether a predicted default rate is matched by the observed rate for rural applicants, thin files, and each region
- Stability uses PSI and characteristic-level drift, especially across the simulated year-two shift
- All segment-level evidence comes from this feature. Feature 004's curves are overall numbers only
- Reject inference is checked against the Feature 004 test cell, whose declined-but-approved applicants have real outcomes

Checks: not written

## Feature 007 — Constrained decline-explanation agent

Status: Not started

Requirements:
- Given a score, its reason codes and the policy rules, when the agent drafts a borrower-facing decline explanation and a short credit memo, then the output uses only approved reason codes and policy text, invents no figures or reasons, is marked for human sign-off, and is scored on the harness for faithfulness, reading level, policy compliance, cost and latency

Checks: not written

## Feature 008 — Performance estimate before outcomes mature

Status: Not started

Requirements:
- Given scores from both models and only the outcomes each regime has observed so far, when the estimator runs at each Feature 004 checkpoint, then it estimates ranking and bad rate for the applicants whose 6-month outcomes have not matured yet, and the report compares each estimate with the realised value once those outcomes arrive
- The estimate uses calibrated default probabilities. The vendor score is mapped to a probability using observed outcomes only. The vendor model is reached through its score API and nothing else
- The report states each regime's blind time: how many months a lender in that regime waits before it can measure the model directly
- Under the year-two shift the estimate is expected to drift from the realised value, because the method assumes the link between score and default does not change. The report shows that gap and does not tune it away
- Builds after Feature 006, whose segment calibration it reuses. It does not depend on Feature 007

Checks: not written
