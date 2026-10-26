import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from scorecheck import config, rundir

STAGES = ["vendor", "models", "experiment", "report", "validate", "explain"]
TABLES = [
    "household", "person", "sim", "electricity_account", "ewallet_account", "month_behaviour", "ground_truth",
    "application_features",
]


@pytest.mark.integration
def test_cli_default_run(tmp_path):
    assert list(tmp_path.iterdir()) == []
    result = subprocess.run(
        [sys.executable, "-m", "scorecheck"], cwd=tmp_path, capture_output=True, text=True, timeout=600
    )
    assert result.returncode == 0, result.stderr

    lines = result.stdout.splitlines()
    assert lines[0] == config.BANNERS["default"]
    for stage in STAGES:
        assert lines[1:].count(stage) == 1, stage

    processed = tmp_path / "data" / "processed"
    runs = [p for p in processed.iterdir()]
    assert [p.name for p in runs] == [rundir.run_id(config.SEED, 50000)]
    run_dir = runs[0]
    assert run_dir.is_dir()
    for table in TABLES:
        assert (run_dir / f"{table}.parquet").is_file(), table

    t = {name: pd.read_parquet(run_dir / f"{name}.parquet") for name in TABLES}
    person_count = len(t["person"])
    assert len(t["household"]) == 50000
    assert person_count >= 50000
    assert set(t["household"]["household_id"]) <= set(t["person"]["household_id"])
    for table in ("month_behaviour", "ground_truth"):
        frame = t[table]
        assert len(frame) == 24 * person_count, table
        assert frame.duplicated(["person_id", "month"]).sum() == 0, table
        months = frame.sort_values(["person_id", "month"])["month"].to_numpy().reshape(-1, 24)
        assert months.shape[0] == person_count, table
        assert (months == np.arange(1, 25)).all(), table
        assert set(frame["person_id"]) == set(t["person"]["person_id"]), table
    assert len(t["sim"]) >= 1
    assert len(t["application_features"]) == person_count > 0

    run_config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["scale"] == "default"
    assert run_config["n_households"] == 50000
