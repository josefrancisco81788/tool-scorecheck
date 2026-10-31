import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from scorecheck import config, rundir
from scorecheck.vendor import ReasonCode, score

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
    assert lines == [config.BANNERS["default"], *STAGES]

    processed = tmp_path / "data" / "processed"
    runs = [p for p in processed.iterdir()]
    run_id = rundir.run_id(config.SEED, 50000)
    assert run_id == "31a32519f30491a4"
    assert [p.name for p in runs] == [run_id]
    run_dir = runs[0]
    assert run_dir.is_dir()
    assert {p.name for p in run_dir.iterdir()} == {*(f"{table}.parquet" for table in TABLES), "run_config.json"}
    ledger = tmp_path / "data" / "vendor" / run_id
    assert {p.name for p in ledger.iterdir()} == {"ledger.parquet", "bind.json"}

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
    for name in ("external_score_1", "external_score_2", "external_score_3"):
        assert t["application_features"][name].isna().all()
    application_id = int(t["application_features"]["application_id"].iloc[0])
    probability, reason_1, reason_2, reason_3 = score(run_dir, application_id)
    assert isinstance(probability, float) and 0.0 <= probability <= 1.0
    codes = (reason_1, reason_2, reason_3)
    assert len(set(codes)) == 3
    assert all(isinstance(code, ReasonCode) for code in codes)

    run_config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["scale"] == "default"
    assert run_config["n_households"] == 50000
