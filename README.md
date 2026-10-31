# ScoreCheck

ScoreCheck is an open testbed for the lender's side of an alternative-data consumer credit score. Feature 001 builds the synthetic Philippine behavioural panel and the application-time features a lender would see.

## Run it

From the repo root, with Python 3.12 or newer:

```text
pip install -r requirements.txt
python -m scorecheck
```

That is the default run. Its first line of output is:

```text
This run uses the default scale of 50,000 households. The full run is 200,000 households.
```

The full run is:

```text
python -m scorecheck --scale full
```

Its first line of output is:

```text
This run uses the full scale of 200,000 households. The default run is 50,000 households.
```

After the banner, the command prints six stage names, one per line: `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`. `experiment`, `report`, `validate`, and `explain` are not built yet. `explain` does not draft a decline.

Each run writes one directory, `data/processed/<run id>/`, relative to the directory you run the command from. The run id is the first 16 hex characters of the SHA-256 of `"{seed}|{n_households}|24"`. The directory holds eight Parquet tables and `run_config.json`:

- `household`, `person`, `sim`, `electricity_account`, `ewallet_account`, `month_behaviour`, and `ground_truth` from the panel generator
- `application_features`, one row per person, built only from what a lender could know at origination

The same command also writes two sibling directories. `data/vendor/<run id>/` holds the vendor ledger (`ledger.parquet` and `bind.json`). `data/models/<run id>/` holds the in-house challenger scores (`scores.parquet` and `bind.json`): LightGBM, XGBoost, histogram gradient boosting, each unconstrained and with a monotone refit, plus the points scorecard, beside the vendor probability. `external_score_1`, `external_score_2`, and `external_score_3` stay null. The challenger file is a shadow record. It does not approve or decline anyone.

The seed is fixed in `src/scorecheck/config.py`, so the same command gives the same tables on any machine. For the default run the challenger directory is `data/models/31a32519f30491a4/`. Read one row with `scorecheck.models.line`.

## Tests

```text
python -m pytest
```

That runs the unit suite, the advisory eval suite, and the integration test that runs the default command. See `docs/testing-standards.md` for the split.
