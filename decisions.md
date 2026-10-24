# decisions.md — Tool - ScoreCheck

> Seeded from the Design Doc's architecture map on 2026-10-24. Update this as real decisions get made — this file is the running log, not a one-time snapshot.

## Architecture map (seed)

Layer 1 seeded synthetic panel generator (households x 24 months, latent creditworthiness factor) -> documented schema -> Layer 2 vendor black-box GBM behind a score API plus in-house challenger (monotonic GBM and points scorecard) in shadow mode, outcomes-ownership experiment, champion/challenger decision report -> Layer 3 validation pack (metrics + PDF) -> Layer 4 constrained LLM agent drafting decline explanations and credit memos, scored on a harness. Layers 2-3 run end to end from one command.

## Open architectural decisions

- [ ] Fill in from `docs/design.md` §5 once the Design Doc is generated (Stage 2 — recommended via Claude Code Plan Mode against docs/PRD.md).

## Decision log

| Date | Decision | Why | Alternatives considered |
|---|---|---|---|
| 2026-10-24 | Project scaffolded | Stage 4 init script run | n/a |
