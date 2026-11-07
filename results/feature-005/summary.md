# Champion and challenger decision report

This report compares a simulated vendor score with in-house challenger models on a synthetic Philippine behavioural panel. The vendor is a simulation built for this testbed and the panel is generated data. Nothing here says how any real vendor or any real borrower population would behave.

Every number is measured on the held-out applicants at month 24 (17,467 applicants, 1,577 bad on the 6-month outcome) in the `data_owner` regime, where the data owner keeps the repayment outcomes. The same tables for the `vendor_only` regime are in the CSV files. The named challenger is the in-house scorecard. Expected loss is the bad outcome times the loan amount times an assumed loss-given-default of 60%; that 60% is an assumption, not a measurement. Loan amounts are in the panel's own currency units.

## Where the vendor still adds lift

Ranking lift is the vendor's AUC minus the challenger's AUC, with a paired 95% interval. Overall the vendor's AUC is 0.797 and the scorecard's is 0.746, a lift of +0.052 (+0.043 to +0.060): vendor leads.

Across the 32 groups (region, income band, urban or rural, gender, age band, thin or thick file), against the scorecard: vendor leads in 29, caught up in 3, challenger ahead in 0. A group with fewer than 50 bad accounts is marked sparse.

- Caught up (interval contains zero): region Central Visayas, region Eastern Visayas (sparse), region Northern Mindanao.
- Challenger ahead (interval entirely below zero): none.

Thin files (6 months of history or less): 6,210 applicants, 584 bad, lift +0.057 (vendor leads). Thick files: 11,257 applicants, 993 bad, lift +0.046 (vendor leads).

Against the other six lines the vendor leads in 30 to 31 of the 32 groups. All of them are in `lift_by_group.csv` and `full_lines.csv`.

## What a phased switch costs

A share of applicants is decided by the scorecard and the rest by the vendor, using the same probability cutoff for both. Changes are against the vendor alone at that cutoff.

| Cutoff | Scorecard share | Approval rate | Change | Expected loss | Change |
|---|---|---|---|---|---|
| 0.075 | 25% | 68.4% | +1.7 points | 27.4M | +3.6M (+14.9%) |
| 0.075 | 50% | 70.2% | +3.5 points | 31.4M | +7.5M (+31.5%) |
| 0.075 | 75% | 71.7% | +5.0 points | 34.3M | +10.4M (+43.6%) |
| 0.075 | 100% | 73.9% | +7.1 points | 38.4M | +14.5M (+60.8%) |
| 0.1 | 25% | 77.7% | +1.7 points | 38.1M | +5.5M (+16.8%) |
| 0.1 | 50% | 79.2% | +3.3 points | 43.5M | +10.9M (+33.5%) |
| 0.1 | 75% | 80.7% | +4.7 points | 47.1M | +14.5M (+44.5%) |
| 0.1 | 100% | 82.3% | +6.3 points | 51.7M | +19.1M (+58.6%) |
| 0.117 | 25% | 81.8% | +1.6 points | 43.4M | +4.8M (+12.4%) |
| 0.117 | 50% | 83.2% | +3.1 points | 49.5M | +10.9M (+28.2%) |
| 0.117 | 75% | 84.7% | +4.6 points | 53.1M | +14.6M (+37.7%) |
| 0.117 | 100% | 86.4% | +6.2 points | 57.5M | +18.9M (+48.9%) |

At a full switch, compared with the vendor at the same cutoff, the scorecard approves more, loses more. The cutoffs are fixed probabilities, so the two models approve different shares of applicants; the equal-approval table below holds the approval rate the same.

## Swap sets at an 80% approval rate

The scorecard would approve 1,116 applicants the vendor declines (swap-ins) and decline 1,116 the vendor approves (swap-outs). Swap-ins went bad at 20.5% (229 of 1,116, 95% interval 18.3% to 23.0%) and swap-outs at 7.9% (88 of 1,116).

Cross-check: the Feature 004 test cell holds 717 vendor-declined applicants who were approved at random and have a matured outcome. Their real bad rate is 21.8% (156 bad, 95% interval 18.9% to 24.9%). The test cell is a check on the declined population. It is not a score of the same people, and the challenger has no held-out score for them.

## At an equal approval rate

Each model approves exactly the same number of applicants (the lowest-risk by its own score). Defaults avoided is the vendor's approved bad accounts minus the model's; a negative number means the model lets more defaults through.

| Approval rate | Model | Bad rate | Expected loss | Defaults avoided | Loss change |
|---|---|---|---|---|---|
| 70% | vendor | 3.89% | 26.4M | - | - |
| 70% | scorecard | 4.83% | 34.5M | -115 | +8.1M (+30.6%) |
| 70% | other six lines | 4.90% to 5.03% | 35.4M to 36.2M | -139 to -123 | +34.0% to +37.0% |
| 80% | vendor | 4.82% | 38.3M | - | - |
| 80% | scorecard | 5.83% | 47.7M | -141 | +9.4M (+24.5%) |
| 80% | other six lines | 5.88% to 5.97% | 49.1M to 50.0M | -160 to -147 | +28.1% to +30.4% |
| 90% | vendor | 6.18% | 56.7M | - | - |
| 90% | scorecard | 6.86% | 64.2M | -106 | +7.6M (+13.3%) |
| 90% | other six lines | 6.93% to 7.01% | 64.2M to 65.6M | -130 to -117 | +13.2% to +15.7% |

## How to read this

Results are reported as they came out. Where the scorecard or another challenger does worse than the vendor, that is the finding. AUC alone is not the decision; the approval-rate, default and loss tables are. This report makes no claim that the in-house model is better than any real vendor.

Files: `lift_by_group.csv`, `phased_switch.csv`, `swap_sets.csv`, `equal_approval.csv`, `full_lines.csv`.
