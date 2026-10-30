# D. Modelling and validation

Jose's rule, 2026-10-25: fit more than one gradient-boosted library and compare them. Do not standardise on one. The scorecard stays in the comparison. Explanation does not choose the model.

## Findings

### LightGBM has the more controllable monotone option; both libraries move when threads move

Claim: LightGBM's `monotone_constraints_method` has `basic`, `intermediate`, and `advanced`. The docs say `basic` "does not slow down the training speed at all, but over-constrains the predictions." XGBoost applies one constraint implementation and warns that under the histogram method constraints "may wipe out all available split candidates." Auguste, Smirnov, and Malory (arXiv:2011.00986) show that a greedy monotone split with a midpoint bound is far from the least-restrictive bound.

Evidence: https://lightgbm.readthedocs.io/en/latest/Parameters.html, https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html, https://arxiv.org/html/2011.00986v1, accessed 2026-10-24.

Confidence: `verified`.

ScoreCheck: the default fit for each library is unconstrained. Where the library supports it, a second fit uses monotone constraints on utilization, delinquency, and installment-to-income (higher burden, higher predicted default). The report shows both. scikit-learn `HistGradientBoostingClassifier` is the third library, with `random_state` set.

### The scorecard should be local code

Claim: `optbinning` 1.0.0 (2026-09-12, Apache-2.0) depends on OR-Tools `>= 9.15`. Earlier 9.12 builds broke its constraint program. Deterministic CP-SAT is claimed from 1.0.0.

Evidence: PyPI `optbinning` and the project's release notes, https://pypi.org/project/optbinning/ and https://gnpalencia.org/optbinning/release_notes.html, accessed 2026-10-24. GitHub issue 347 for the OR-Tools breakage.

Confidence: `verified` for the dependency and the issue. "Use our own code" is the recommendation Jose accepted.

ScoreCheck: decision-tree or quantile pre-bins, pool adjacent bins that break the requested direction, weight of evidence with 0.5 smoothing, logistic regression, points scaled as `Factor = PDO / ln(2)` and `Offset = BasePoints - Factor * ln(BaseOdds)` (Siddiqi). Information value bands from the same source: under 0.02 unpredictive, 0.02–0.10 weak, 0.10–0.30 medium, 0.30–0.50 strong, above 0.50 check leakage. Those bands are industry rules of thumb.

Status 30 Oct 2026: the decision is ten quantile bins, adjacent merge on the five monotone columns, points to double the odds 20, base points 600, base odds 50 goods to one bad. The sentence above is the proposal.

### What makes the outcomes experiment invalid

The experiment is two regimes over the synthetic months. In one, repayment labels return only to the vendor arm. In the other, the data owner refits on those labels too. Learning curves are the vendor-minus-challenger gap against month.

The run is not evidence if any of these is true:

- Vendor and challenger are given the same columns, including `external_score_*`.
- Ability alone is a sufficient statistic for default, so the pre-application features already match the vendor.
- Rejected loans' true defaults are used in training in one regime and not the other, contrary to the regime rule.
- The approval rule is allowed to see the eventual default.
- Shocks are copied onto the features with the coefficient the report then calls a finding.
- Hyperparameters or the data-generating process are changed until the curves match the Notion sentence.

The Notion page states that sentence as the expected write-up: the vendor leads early, and the gap narrows only in the regime where the data owner keeps the outcomes. https://app.notion.com/p/402087d04d3d81deb1bcf60268996523, read 2026-10-24. Confidence: `verified` as the page text. It is a hypothesis. The report prints the curves the seed produced.

Selection: labels exist only for approved loans. Both regimes share the same approval rule, fit on the vendor score at each month, frozen before that month's defaults realise. The data-owner regime may refit the challenger on matured labels. The vendor-only regime may not. Held-out people, scored and never used for refitting, are the curve. Because the generator stores `true_default` for declines, reject-inference error can be measured against that oracle. The oracle column is not a model feature.

### Reject inference

Claim: Ehrhardt, Biernacki, Vandewalle, Heinrich, and Beben (Journal of Applied Statistics, 2021) show fuzzy augmentation is equivalent to the model fit on financed clients only, hard reclassification stays biased, and parcelling's uplift factors cannot be identified when rejection depends on something the model does not see. On a real book of about 260,000 loans, no method they tried beat logistic regression on the financed clients in a uniform way. Hand and Henley asked in 1993 whether reject inference can work. It cannot recover an unobserved cause of both rejection and default.

Evidence: https://doi.org/10.1080/02664763.2021.1929090, accessed 2026-10-24. Quote under 15 words: "no method works significantly and uniformly better than logistic regression on financed clients."

Confidence: `verified` for the paper. The 260,000 figure is the paper's CACF illustration as reported in the track notes.

ScoreCheck: implement accepted-only, hard cutoff, fuzzy augmentation, inverse-probability weights, and parcelling. Score each against `ground_truth` on the declined slice. Publish the bias. Do not present a method as recovering the truth.

### Stability and calibration thresholds

Claim: PSI under 0.10, 0.10 to 0.25, and at or above 0.25 are the bands in Siddiqi and in Lewis. Siddiqi calls them "industry rules of thumb, and not definitive" (as quoted by Yurdakul). Yurdakul and Naranjo (Journal of Risk Model Validation, 2020) give a chi-square approximation: with 10 bins and 100 people in each sample, the null expectation of PSI is about 0.18, so the 0.10 band false-alarms. Van Calster and others (BMC Medicine, 2019) advise against the Hosmer–Lemeshow test as the calibration verdict and cite large samples before a calibration curve is stable. Wilson intervals stay defined when a segment has few defaults.

Evidence: Yurdakul and Naranjo, https://files.wmich.edu/s3fs-public/attachments/u730/2022/PSIfinal.pdf. Van Calster et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC6912996/. Accessed 2026-10-24.

Confidence: `verified` for the papers. The exact false-alarm percents in the track notes should be recomputed from the formula when the pack is built, not copied as constants.

ScoreCheck: print the rule-of-thumb band and the sample-size critical value. Flag any segment with fewer than 30 observed defaults as sparse. Use a Wilson interval on the segment default rate. Brier score and a reliability curve are the calibration displays. Characteristic stability uses the same divergence on each canonical column.

### Year-two shift

The three shocks named in the PRD are config, not hard-coded branches: a new channel (mix shift in `region` or a channel column), a rural income shock (ability scaled down for `urban_rural = rural` over a stated month range), and a telco price change (top-up amounts scaled). Seed and config reproduce them. They are applied in the synthetic panel only. Home Credit has no calendar to hang them on.

### Fairness

BSP Circular 1160, section 1003, prohibits discrimination on race, age, financial capacity, ethnicity, origin, gender, disability, health, sexual orientation, religion, and political affiliation, and then allows a distinction "when making a risk assessment on a specific financial product or service." https://www.bsp.gov.ph/Regulations/Issuances/2022/1160.pdf, accessed 2026-10-24. Confidence: `verified`.

ScoreCheck: the pack reports approval rate and default capture by gender, age band, and region, where those columns are non-null. The proxy note measures association between `prepaid_flag`, `region`, and `education` and the outcome, and says a model can track a prohibited attribute through those columns even when the attribute is not an input. The note does not claim a legal breach. It states the measured association.

## Recommendations

Comparison set on every run: LightGBM, XGBoost, `HistGradientBoostingClassifier`, and the in-house scorecard. Metrics: AUC, log loss, Brier, and the segment calibration table. The decision report quotes all four. It does not drop three because one won on AUC.
