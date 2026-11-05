# Checks — feature-004: Outcomes-ownership experiment

Status: draft

Feature: feature-004

About one page. Plain language. Engineering choices and the test plan live in `docs/choices/feature-004.md`, which is not locked.

## Product answers

- **Bad definition.** An account is bad if it defaults within 6 months of taking the loan. It counts only once the account has been open 6 months. On the default book 7.3% of accounts are bad (measured 2026-11-05).
- **Approval cutoff.** The simulated lender declines about 20% of applicants. Approval means the vendor's predicted chance of default is below a cutoff. Until the vendor is first refit the cutoff is `0.0185`, the 80th percentile of the published vendor scores on the default book. Each time the vendor is refit, the cutoff is reset to the 80th percentile of the new model's scores on the applicants it is about to decide, so about 20% are declined throughout (a refit model predicts the 6-month bad rate, which is on a higher scale). The cutoff is set from scores only and never looks at outcomes.
- **Random test cell.** A random 5% of the applicants the cutoff would decline are approved anyway and tracked like any other loan. That's about 700 applicants on the default book.
- **Batch vendor read.** The vendor ledger may be read for the whole book at once, inside `vendor/`. This needs the narrowed Feature 002 rule V3.

## Behavior

- [ ] E1. The experiment runs two regimes over the 24 simulated months, with a point every quarter (months 4, 8, 12, 16, 20, 24). In `vendor_only`, only the vendor learns from repayment outcomes; the data owner's challengers stay as first fitted. In `data_owner`, the vendor and the challengers both learn from the same outcomes. Month 4 is the starting baseline: no account has been open 6 months yet, so no model is refit there.
- [ ] E2. The lender approves or declines each applicant from the vendor score alone, using the cutoff above, plus the random 5% test cell. Test-cell approvals are marked as such. On the default book about 80% are approved by the cutoff at every checkpoint. Changing repayment outcomes does not change who is approved at the first checkpoint.
- [ ] E3. A model only learns from outcomes the lender could actually have seen. That means approved applicants, test cell included, whose loans have been open at least 6 months by that checkpoint, labelled with the 6-month bad definition. Declined applicants' repayment never reaches any model.
- [ ] E4. One applicant in five (`application_id % 5 == 0`) is the holdout. The holdout is never used to train any model in either regime.
- [ ] E5. Every point on every curve is measured on the same target: the whole holdout, including applicants the lender would decline, against their 6-month bad outcome. A point moves only because the models changed, not because the people or the label changed.
- [ ] E6. The run writes a learning-curve table under `data/experiment/<run id>/`. For each regime, checkpoint, and challenger line it gives the vendor's and the challenger's AUC, log loss, and Brier score on the holdout, and the gap (vendor minus challenger). A gap that favours the challenger, or goes against the hypothesis, is kept as it came out.
- [ ] E7. Each point also carries the numbers behind it: the number of accounts and of bad accounts in the vendor fit and in the challenger fit, the number of test-cell accounts in those fits, the holdout size and bad count, and a 95% confidence interval on each gap.
- [ ] E8. The hypothesis ("the vendor leads early, and the gap narrows only where the data owner keeps the outcomes") is written beside the curves as a hypothesis. Nothing in the generator or the models is adjusted to make the curves match it.
- [ ] E9. Which outcomes were hidden is recorded per applicant, checkpoint, and regime in `data/experiment/<run id>/outcomes.parquet`, including whether each approval came from the test cell. The shared `application_features` table is not rewritten.
- [ ] E10. Vendor refits happen inside `vendor/`, and everything outside `vendor/` still reaches the vendor only through a score plus three reason codes. Challenger refits live in `models/`. The Feature 002 vendor ledger and the Feature 003 shadow scores are left exactly as they were.
- [ ] E11. Running the experiment twice with the same seed on the same machine gives the same curves, confidence intervals, test cell, and outcomes table.

## Integration

- [ ] `python -m scorecheck` runs the experiment after the challengers, still prints only the banner and the six stage names, and still finishes within the existing 600-second limit.

## Regression

- [ ] The tests and locked checks of Features 001–003 still pass. The one deliberate change is the narrowed Feature 002 rule V3 above.

## Completeness

- [ ] A person runs `python -m scorecheck` and finds a learning-curve table for both regimes under `data/experiment/<run id>/`, with sizes, bad counts, and confidence intervals, plus the outcomes table and the hypothesis note. From the table they can read how the vendor-versus-challenger gap moves in each regime and how sure each point is. A passing unit test alone does not satisfy this check.
