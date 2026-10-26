# Golden panel changelog

Every change to a hash in `panel.json` needs a line here that says why it changed.

- 2026-10-26: First fixture. Seed 20261024, 250 households, written by `scripts/write_golden_panel.py` for feature 001.
- 2026-10-26: `ground_truth` and `application_features` changed because the origination hazard no longer counts months before application, and the delinquency counts now draw one uniform per person.
