# Golden panel changelog

Every change to a hash in `panel.json` needs a line here that says why it changed.

- 2026-10-26: First fixture. Seed 20261024, 250 households, written by `scripts/write_golden_panel.py` for feature 001.
- 2026-10-26: `ground_truth` and `application_features` changed because the origination hazard no longer counts months before application, and the delinquency counts now draw one uniform per person.
- 2026-11-07: `report_2000.json` is new for feature 005. It holds headline numbers of the champion and challenger report on the 2,000-household book (seed 20261024), written once from `scorecheck.report.run` after the Feature 004 experiment. Counts are exact; rates match to 1e-6.
