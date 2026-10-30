# ScoreCheck research notes

Access dates: 2026-10-24 for the first pass, 2026-10-25 for the Hugging Face follow-up. Jose's decisions from 2026-10-25 are in [../plan.md](../plan.md) and [../../decisions.md](../../decisions.md).

## Findings that change the build

1. **Home Credit is the only public set with enough grain.** Ignoring licence, as decided: the application table plus bureau, POS, card, and installment history is monthly and relational, and the anonymized `EXT_SOURCE_*` scores can stand in for a vendor the challenger is not allowed to see. Give Me Some Credit is 10 columns and one snapshot. UCI Default of Credit Card Clients is clean and only six months wide, on people who already have cards. Hugging Face hosts mirrors of those sets and several synthetic telco or utility panels. It does not host a better real consumer panel. The 24-month outcomes loop still has to run on the synthetic panel, because none of the public sets is a monthly origination cohort with a label each month.

2. **The default command is 50,000 households, and the README and the report header have to say so.** Full scale stays 200,000. Training on raw Home Credit bureau-balance rows (about 27 million) does not fit the ten-minute command. That run is the full command. The ten-minute command uses the 50,000-household panel plus the small UCI file.

3. **The model table is the overlap of the public sets, not a Philippine-only layout.** Detail tables still hold households, SIMs, electricity, and wallets. Models train on one application row whose core columns can be filled from Home Credit, Give Me Some Credit, UCI 350, or the synthetic aggregate. Alternative-data columns are null on public rows. Ground truth stays in its own table.

4. **Compare three gradient-boosted libraries every time.** LightGBM, XGBoost, and scikit-learn's histogram booster. An in-house points scorecard is a fourth line. No library is the standard on its own. Monotone constraints are a paired variant, not the only model. Explanation is a later function and does not decide which model is fit.

5. **One latent factor would make the outcomes experiment uninformative.** The generator uses ability, willingness, shocks, and a vendor-only signal. The Notion sentence that the vendor leads early, and that the gap narrows only when the data owner keeps the outcomes, is a hypothesis. A run tuned to produce it is not evidence.

## Where this disagrees with the PRD

Proposed edits are in [../plan.md](../plan.md). Status 30 Oct 2026: the PRD and `features.md` now contain the 2026-10-25 wording. Keep the disagreement list below as the historical record from this note.

- The PRD points at Home Credit and Give Me Some Credit and then stops on licence. Licence is no longer the filter. Grain is. Home Credit is in. Give Me Some Credit is out of the pipeline.
- The PRD's single latent factor becomes two traits plus shocks.
- "About 200,000" households remains the full run. The ten-minute README runs 50,000 and says so on the page.
- The PRD requires a monotonic GBM as the challenger. The comparison set is three unconstrained boosters, with a monotone refit and a scorecard reported beside them. A later explanation function drafts reasons. Model class is not chosen for ease of explanation.

## Index

| File | Track |
|---|---|
| [a-schema-reproducibility.md](a-schema-reproducibility.md) | Canonical columns and what "same seed" requires |
| [b-synthetic-panel.md](b-synthetic-panel.md) | Philippine figures for the generator |
| [c-public-dataset.md](c-public-dataset.md) | Grain and quality, Kaggle and Hugging Face, licence set aside |
| [d-modelling-validation.md](d-modelling-validation.md) | Boosters, scorecard, outcomes experiment, validation metrics |
| [e-governance.md](e-governance.md) | EU AI Act and Philippine sources, and the decision to explain later |
| [f-constrained-agent.md](f-constrained-agent.md) | The later explanation function |
| [g-tooling-runtime.md](g-tooling-runtime.md) | ReportLab and the 50,000-household default |
| [sources.md](sources.md) | Sources |
