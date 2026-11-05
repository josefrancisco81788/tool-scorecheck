"""E11: two runs with the same seed on the same machine give the same experiment tables."""

import os
import subprocess
import sys

import pandas as pd

SCRIPT = """
import sys
from pathlib import Path
from scorecheck import config, experiment, features, panel, vendor

root = Path(sys.argv[1])
run_dir = panel.generate(config.SEED, 300, root / "processed")
features.from_panel(run_dir)
vendor.publish(run_dir)
print(experiment.run(run_dir))
"""

TABLES = ("curves.parquet", "outcomes.parquet", "fits.parquet", "heldout_scores.parquet")


def _run(root, hash_seed: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT, str(root)],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PYTHONHASHSEED": hash_seed},
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_two_runs_give_equal_tables(tmp_path):
    first = _run(tmp_path / "a", "1")
    second = _run(tmp_path / "b", "2")
    for name in TABLES:
        a = pd.read_parquet(f"{first}/{name}")
        b = pd.read_parquet(f"{second}/{name}")
        pd.testing.assert_frame_equal(a, b, check_exact=True)
    out_a = pd.read_parquet(f"{first}/outcomes.parquet")
    assert out_a["test_cell"].any()
    for name in ("hypothesis.txt",):
        assert open(f"{first}/{name}", "rb").read() == open(f"{second}/{name}", "rb").read()
    for regime in ("vendor_only", "data_owner"):
        for sub in (regime, f"{regime}/challengers"):
            for file in ("ledger.parquet", "scores.parquet"):
                try:
                    a = pd.read_parquet(f"{first}/{sub}/{file}")
                except FileNotFoundError:
                    continue
                b = pd.read_parquet(f"{second}/{sub}/{file}")
                pd.testing.assert_frame_equal(a, b, check_exact=True)
