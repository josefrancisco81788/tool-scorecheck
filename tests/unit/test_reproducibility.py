import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from scorecheck import config
from scorecheck.logical_hash import LogicalHashError, logical_hash
from support.runs import ALL_TABLE_NAMES, PanelRun, generate_run

WORKED_DIGEST = "492c75a4c990cada69f18ffcaabb27d2e53edd18a5ddf87e19491ba7aba584b2"
GENERATE = (
    "import sys; from scorecheck import config, features, panel; "
    "features.from_panel(panel.generate(config.SEED, 300, sys.argv[1]))"
)


def _subprocess_run(data_dir, hash_seed: str) -> PanelRun:
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}
    subprocess.run([sys.executable, "-c", GENERATE, str(data_dir)], check=True, env=env, timeout=300)
    (run_dir,) = list(data_dir.iterdir())
    return PanelRun(run_dir)


def test_same_seed_same_hash(tmp_path):
    first = _subprocess_run(tmp_path / "hashseed0", "0")
    second = _subprocess_run(tmp_path / "hashseed1", "1")
    assert first.run_dir != second.run_dir
    for table in ALL_TABLE_NAMES:
        assert logical_hash(first[table]) == logical_hash(second[table]), table


def test_second_seed_differs(run_300, tmp_path):
    other = generate_run(config.SEED + 1, 300, tmp_path)
    for table in ("ground_truth", "application_features"):
        assert logical_hash(other[table]) != logical_hash(run_300[table]), table


@pytest.mark.parametrize("table", ["person", "ground_truth", "month_behaviour", "application_features"])
def test_hash_is_logical(run_300, tmp_path, table):
    frame = run_300[table]
    digest = logical_hash(frame)

    assert logical_hash(frame.sample(frac=1.0, random_state=11).reset_index(drop=True)) == digest
    assert logical_hash(frame[list(reversed(frame.columns))]) == digest
    frame.to_parquet(tmp_path / "copy.parquet", index=False)
    assert logical_hash(pd.read_parquet(tmp_path / "copy.parquet")) == digest

    changed = frame.copy()
    changed.loc[0, "age_years" if "age_years" in changed else "month"] += 1
    assert logical_hash(changed) != digest


def test_worked_example_digest():
    frame = pd.DataFrame({
        "region": ["NCR", "Region VII, Cebu", "NCR"],
        "person_id": np.array([2, 1, 1], dtype=np.int64),
        "wallet_inflow": [1500.1234567, np.nan, 0.5],
        "shared": [True, False, True],
    })
    assert logical_hash(frame) == WORKED_DIGEST


def test_bad_int_cast_produces_no_digest(run_300):
    person = run_300["person"]
    non_whole = person.assign(age_years=person["age_years"].astype(float))
    non_whole.loc[0, "age_years"] = 30.5
    with pytest.raises(LogicalHashError):
        logical_hash(non_whole)
    null = person.assign(origination_month=person["origination_month"].astype(float))
    null.loc[0, "origination_month"] = np.nan
    with pytest.raises(LogicalHashError):
        logical_hash(null)
