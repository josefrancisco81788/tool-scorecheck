# Checks — feature-005: Champion and challenger decision report

Status: draft

Feature: feature-005

About one page. Plain language. Engineering choices and the test plan live in `docs/choices/feature-005.md`, which is not locked.

## Product answers

- **Thin versus thick file.** Thin = 6 months of behavioural history or less; thick = more than 6. On the default book's holdout that is 6,210 thin applicants (584 bad) and 11,257 thick (993 bad).
- **Expected loss.** For each approved loan: bad outcome × loan amount × 60% loss-given-default. The loan amount is the exposure. The 60% is a stated assumption, printed in the report.
- **Named challenger.** The in-house scorecard heads every table. The other six challenger lines appear in one full table.
- **Cut-offs.** Equal approval rate at 70%, 80%, and 90%. Phased switch at 25%, 50%, 75%, and 100% of applicants decided by the challenger, at the same probability cutoff 0.075, 0.10, and 0.117.
- **Segments.** Region, income band, urban or rural, gender, and age band. A group with fewer than 50 bad accounts is marked sparse.

## Behavior

- [ ] R1. The report reads the held-out regime scores and the outcomes table from Feature 004, at the last checkpoint (month 24), for both regimes. It does not read the Feature 003 in-sample scores. Every number is measured on the holdout against the 6-month bad outcome.
- [ ] R2. For every segment and for thin and thick files, the report shows the vendor's ranking lift over the named challenger and over each other challenger, with the group's size and bad count. Where the vendor still leads, and where a challenger has caught up or passed it, is stated per group in plain words.
- [ ] R3. At each phased-switch step and cutoff above, the report shows the change in approval rate and in expected loss compared with the vendor alone. A switch can cost approval rate, expected loss, both, or neither; the report shows whichever it is.
- [ ] R4. The swap-set analysis names the applicants the challenger would approve and the vendor declines (swap-ins) and the reverse (swap-outs), at the 80% equal approval rate. Each group shows its size and bad rate.
- [ ] R5. Swap-in risk is shown two ways: the holdout's real outcomes, and the real bad rate of the Feature 004 test cell with its count and 95% interval. The report says the test cell is a cross-check on the declined population, not a score of the same people.
- [ ] R6. At an equal approval rate (70%, 80%, 90%), the report shows the vendor's and each challenger's bad rate and expected loss, and how many fewer or more defaults and how much lower or higher loss the challenger delivers. AUC alone is not given as the decision.
- [ ] R7. The report never says the in-house model beats a real vendor. It says it is a simulated vendor and a synthetic panel. When a challenger does worse, that is reported as it came out.
- [ ] R8. Running the report twice with the same seed gives the same tables.
- [ ] R9. The tables are written under the run's `data/experiment/<run id>/report/` as CSV files with a one-page plain-language summary. The default-book copy is kept in `results/feature-005/`.

## Integration

- [ ] `python -m scorecheck` builds the report after the experiment, as the `report` stage, still prints only the banner and the six stage names, and still finishes within the 600-second limit.

## Regression

- [ ] The tests and locked checks of Features 001–004 still pass. Nothing else changes.

## Completeness

- [ ] A person runs `python -m scorecheck` and finds the summary and the tables under the run's directory and under `results/feature-005/`. From them they can read where the vendor still adds lift, where a challenger has caught up, what a phased switch costs in approval rate and expected loss, and the bad rate and loss at an equal approval rate. A passing unit test alone does not satisfy this check.
