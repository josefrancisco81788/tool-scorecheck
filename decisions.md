# decisions.md — Tool - ScoreCheck

> Seeded from the Design Doc's architecture map on 2026-10-24. Update this as real decisions get made — this file is the running log, not a one-time snapshot.

## Architecture map (seed)

Layer 1 seeded synthetic panel generator (ability, willingness, shocks, and a vendor-only signal; default 50,000 households × 24 months, full about 200,000) -> documented schema -> Layer 2 vendor black-box GBM behind a score API plus in-house challengers (LightGBM, XGBoost, and histogram gradient boosting, each unconstrained and, where supported, with a monotone refit, plus a points scorecard) in shadow mode, outcomes-ownership experiment, champion/challenger decision report -> Layer 3 validation pack (metrics + PDF) -> Layer 4 constrained LLM agent drafting decline explanations and credit memos, scored on a harness. Layers 2-3 run end to end from one command.

## Open architectural decisions

- [x] Fill in from `docs/design.md` §5 once the Design Doc is generated (Stage 2 — recommended via Claude Code Plan Mode against docs/PRD.md).
- [x] Lock the `application_features` column list from [docs/research/a-schema-reproducibility.md](docs/research/a-schema-reproducibility.md) when the design doc is written. The rule is decided; the list is the proposal.
- [ ] Confirm Home Credit row counts and table completeness when the files are first downloaded. The ten-minute command uses UCI 350 until that load is measured.
- [ ] Re-check Claude API prices at Feature 007. Explanation does not gate earlier features.

## Decision log

| Date | Decision | Why | Alternatives considered |
|---|---|---|---|
| 2026-10-24 | Project scaffolded | Stage 4 init script run | n/a |
| 2026-10-25 | Public dataset by grain, licence ignored | Home Credit has monthly relational history and external scores; Give Me Some Credit has 10 columns and no time; UCI 350 is the small file for the ten-minute command. Hugging Face added mirrors and synthetic panels, not a better real consumer set | UCI only; Give Me Some Credit; Lending Club as primary; Nigerian synthetic telco sets |
| 2026-10-25 | Canonical schema from shared dataset attributes | One application row the public loaders and the synthetic aggregate both fill. Alternative-data columns null on public rows. Ground truth in its own table | A Philippine-only household schema as the training frame |
| 2026-10-25 | Compare LightGBM, XGBoost, and sklearn histogram boosting, plus an in-house scorecard | A single library hides a library effect. Monotone refits are reported beside unconstrained fits. The scorecard is one line, not the required winner | LightGBM only; optbinning |
| 2026-10-25 | Try ReportLab for the validation pack | Wheels install with pip. WeasyPrint needs Pango via MSYS2 on Windows | fpdf2 first; WeasyPrint; Quarto |
| 2026-10-25 | Default panel 50,000 households, disclosed in the README, command output, and report header | 200,000 with monthly refits and a SIM-month frame will not meet ten minutes on a laptop. Full scale stays 200,000 | Always generate 200,000 |
| 2026-10-25 | Two traits, shocks, and a vendor-only signal | One latent factor makes owning the outcomes uninformative. The Notion expected-finding sentence is a hypothesis, not a tuning target | Single latent factor |
| 2026-10-25 | Explanation is a later function and does not constrain model class | Opaque boosters stay in the comparison. Feature 007 still uses approved reason codes, invents no figure, and waits for a human signature | Require monotone models or a scorecard so every score is narratable |
| 2026-10-30 | Scorecard: ten quantile bins; PDO 20, base 600, odds 50; Python floor `>=3.12` at Feature 003 implement; hidden labels in an experiment table; regime refit outside `data/vendor/<run id>/` | Lock Feature 003 constants; keep Feature 001 `label_observed` = 1; preserve the locked two-file vendor ledger | Tree bins; keep Python 3.11 with an older XGBoost; rewrite `application_features`; second ledger inside `data/vendor/` |
