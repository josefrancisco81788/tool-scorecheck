"""Write tests/fixtures/golden/panel.json from a fresh run.

A changed hash needs a line in tests/fixtures/golden/CHANGELOG.md that says why it changed.
"""

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

from scorecheck import config, features, panel
from scorecheck.logical_hash import logical_hash

N_HOUSEHOLDS = 250
TABLES = (
    "household", "person", "sim", "electricity_account", "ewallet_account", "month_behaviour", "ground_truth",
    "application_features",
)
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "golden" / "panel.json"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = panel.generate(config.SEED, N_HOUSEHOLDS, tmp)
        features.from_panel(run_dir)
        hashes = {name: logical_hash(pd.read_parquet(run_dir / f"{name}.parquet")) for name in TABLES}
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"seed": config.SEED, "n_households": N_HOUSEHOLDS, "hashes": hashes}
    FIXTURE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {FIXTURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
