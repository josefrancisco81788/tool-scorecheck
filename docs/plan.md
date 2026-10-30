# Plan — next session and the decisions already made

Date: 2026-10-25. Research notes: [research/README.md](research/README.md). The PRD and the design doc are not edited here. Proposed PRD wording is listed so a later edit can apply it on purpose.

Status 30 Oct 2026: the PRD and `features.md` now contain the 2026-10-25 wording. Keep this note as the historical plan.

No step waits on another repo.

## Decisions made

1. **Licensing is not a filter.** Grain and quality are. Home Credit Default Risk is the public dataset for the full command: monthly bureau, POS, card, and installment history, and `EXT_SOURCE_*` as the vendor-only scores. Give Me Some Credit is out (10 columns, no time). UCI Default of Credit Card Clients (30,000 rows, six months, CC BY 4.0) is the public file inside the ten-minute command. Hugging Face was checked. Its useful pages are mirrors of these files. Its telco and utility panels are synthetic, several of them Nigerian, and they are not a second source. Lending Club stays optional for a later reject-file or vintage test, with an application-time column allow-list so post-origination fields cannot leak. Detail: [research/c-public-dataset.md](research/c-public-dataset.md).

2. **Is that grain enough?** Home Credit is enough for ranking, segments, thin versus thick (bureau depth), relative-month drift, and a vendor arm that sees external scores the challenger does not. It is not a 24-month origination panel and it has no calendar to attach an El Niño year to. Those stay on the synthetic panel. UCI is enough for a fast ranking, calibration, and fairness check, and too short for the rest. Give Me Some Credit is not enough.

3. **Schema comes from shared columns.** Models train on `application_features`: age, income, dependents, credit amount, installment-to-income, utilization, open-credit count, 30/60/90 delinquency counts, history length, on-time rate, payment-to-obligation ratio, and nullable gender, education, marital status, and region. Alternative-data columns (SIMs, prepaid, electricity, remittance, wallet, shared account) are filled only for synthetic rows. `external_score_1/2/3` are vendor-only. `ground_truth` is a separate table. Column list: [research/a-schema-reproducibility.md](research/a-schema-reproducibility.md). Lock it in the design doc before Feature 001 checks.

4. **Three boosters, every run.** LightGBM, XGBoost, and scikit-learn `HistGradientBoostingClassifier`, plus the in-house weight-of-evidence scorecard. Unconstrained fits are the default. A monotone refit is reported beside them where the library supports it. The report keeps all four lines. Explanation quality is not a reason to drop one.

5. **PDF.** Try ReportLab. fpdf2 only if ReportLab fails a layout check. Not WeasyPrint.

6. **Default panel is 50,000 households × 24 months.** Full scale remains 200,000. The README, the command's opening output, and the validation-pack header state which scale ran. There is no UI yet; the header is the place a later screen must show the same sentence.

7. **Accepted with the above.** Two traits (ability and willingness), plus shocks, plus a vendor-only signal. The Notion "expected finding" is a hypothesis, and a run tuned to match it does not count. In-house scorecard, not `optbinning`. Ground truth never joins into features. Reject-inference methods are scored against the synthetic oracle. PSI is shown with the 0.10 / 0.25 bands and with a sample-size critical value. Segments under 30 defaults are marked sparse.

8. **Explanation is a later function.** Feature 007 still drafts from approved reason codes, still invents no figure, and still waits for a person to sign. It does not constrain Features 002–006. The statutory hooks remain RA 9510 section 4(n), the Data Privacy Act IRR on automated decisions, and NPC Circular 20-01. They are mapped in the model-risk note. They are not implemented by refusing to train an opaque booster.

## PRD corrections to apply later

Do not apply them in this session.

Current success criterion: "One public dataset run whose licence allows public redistribution of results (check Home Credit Default Risk and Give Me Some Credit terms first)."

Proposed: "One public dataset run on Home Credit Default Risk in the full command, and on UCI Default of Credit Card Clients in the default command. Give Me Some Credit is not used. Licence was set aside by decision on 2026-10-25; the choice is grain and quality."

Current Feature 001 text: "about 200,000 households" and "driven by one latent creditworthiness factor".

Proposed: "the default run writes 50,000 households over 24 months, and the full run writes about 200,000; the README and the report header state which ran. Behaviour and default are driven by ability, willingness, shocks, and a vendor-only signal, with ground truth stored apart from the model columns. Output conforms to `application_features`."

Current challenger text: "the monotonic-constrained GBM and the points scorecard".

Proposed: "LightGBM, XGBoost, and histogram gradient boosting, each unconstrained and, where supported, with a monotone refit, plus the points scorecard, all scored on the same rows and all reported."

Current ten-minute criterion stays, with one added clause: the default command is the 50,000-household panel plus UCI 350, and the README says that Home Credit and 200,000 households are the full command.

The Notion page's expected-finding sentence is missing from the PRD. Proposed addition under the outcomes feature: "The hypothesis on the Notion page is recorded in the report and is not a target the generator is adjusted to hit."

## Order

1. Design session. Fill [design.md](design.md). Review time about 2 hours.
   - Section 1: `src/panel` (detail tables and ground truth), `src/features` (the canonical row), `src/vendor` (score and three codes only), `src/models` (three boosters and the scorecard), `src/experiment`, `src/validate` (metrics and ReportLab), `src/explain` (stub until Feature 007). Public loaders live next to features.
   - Section 2: the schema in research note A, including null alternative-data columns on public rows.
   - Section 3: one sequence per feature. Feature 001 writes detail, ground truth, and `application_features`, and prints the scale. Features 002–003 fit the four models with vendor columns withheld from challengers. Feature 004's sequence includes the invalidation list from research note D. Feature 006's default path loads UCI 350; the full path loads Home Credit aggregates.
   - Section 4: immutable zones touched are the schema, the vendor module boundary, and, later, the reason-code list. `checks/approved/` stays untouched until a feature is locked.
   - Section 5: only leftovers. The decisions in this file are made. Leftovers: confirm Home Credit row counts on download; re-quote BSP subsection numbers from the PDF in the model-risk note; re-check Claude prices at Feature 007.
2. Feature 001 only, after the design doc locks the columns. Draft checks, review about 1 hour, lock with `python scripts/lock_checks.py`, then implement. Checks to cover, in outline: same seed, same logical hash; second seed differs; canonical columns present and ground-truth columns absent; prepaid share near 96 percent; some people have more than one SIM; remittance shape follows the config multipliers; four electricity states; ability and willingness are rank-correlated with lender-visible columns and are not perfectly recovered; README text states that the default is 50,000 and the full run is 200,000; the generator prints that sentence. No firm entity.
3. Features 002–007 in order. Feature 004 does not start until the invalidation list is in the design doc. Feature 007 does not start until the approved reason codes and policy sentences exist.

## Risks

- If the canonical column list is widened so the challenger sees `external_score_*`, the outcomes experiment is void. The design doc should say the drop is a test, not a convention.
- Home Credit's employment sentinel and missing external scores will dominate a careless pipeline. The loader tests belong to the public-data feature, not to Feature 001.
- The ten-minute claim is an estimate until the first measured run. If 50,000 and six refits exceed ten minutes, cut the refit count before raising the household count.
- Final number of the BSP model-risk circular: unknown. Cite the 2025 draft or omit the number.
- Parked: Lending Club reject file; Docker and CI (stretch); the Ray Espinosa one-pager (outside the repo).

## Review hours

Design doc about 2 hours. Feature 001 checks about 1 hour. Each later feature's checks about 0.5 to 1 hour. Governance sentences in the model-risk note, checked against the PDFs, about 1.5 hours. Through the Feature 001 lock, about 3 hours from here, because the dataset, library, scale, and explanation decisions are already made.
