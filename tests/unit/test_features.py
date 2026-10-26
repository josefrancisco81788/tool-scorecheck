import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scorecheck import features
from scorecheck.logical_hash import logical_hash
from support.runs import PANEL_TABLE_NAMES

CORE = [
    "application_id", "person_id", "age_years", "income", "dependents", "credit_amount",
    "installment_to_income", "utilization", "open_credit_count", "delinquency_count_30",
    "delinquency_count_60", "delinquency_count_90", "history_months", "on_time_rate",
    "payment_to_obligation_ratio", "gender", "education", "marital_status", "region", "default_label",
    "label_observed",
]
VENDOR = ["external_score_1", "external_score_2", "external_score_3"]
ALT_DATA = [
    "sim_count", "prepaid_flag", "electricity_late_rate", "electricity_disconnect_count",
    "remittance_inflow_mean", "ewallet_net_flow_mean", "shared_account_flag",
]
DISCONNECTED = {"disconnected_restored_30d", "unpaid_past_30d"}
PANEL_FILES = [f"{name}.parquet" for name in PANEL_TABLE_NAMES] + ["run_config.json"]


@pytest.fixture(scope="module")
def read_back(run_300) -> pd.DataFrame:
    return run_300["application_features"]


def test_feature_columns(run_300, tmp_path):
    run_dir = tmp_path / "run"
    shutil.copytree(run_300.run_dir, run_dir, ignore=shutil.ignore_patterns("application_features.parquet"))
    returned = features.from_panel(run_dir)
    assert (run_dir / "application_features.parquet").is_file()
    assert set(returned.columns) == set(CORE + VENDOR + ALT_DATA)
    assert len(returned.columns) == 31
    assert "origination_month" not in returned.columns


def test_features_file_matches_return(run_300, tmp_path, read_back):
    run_dir = tmp_path / "run"
    shutil.copytree(run_300.run_dir, run_dir)
    returned = features.from_panel(run_dir)
    assert logical_hash(pd.read_parquet(run_dir / "application_features.parquet")) == logical_hash(returned)
    assert logical_hash(read_back) == logical_hash(returned)
    assert read_back["application_id"].duplicated().sum() == 0
    assert read_back["person_id"].duplicated().sum() == 0
    assert set(read_back["person_id"]) == set(run_300["person"]["person_id"])


def test_labels_at_origination(run_300, read_back):
    assert (read_back["label_observed"] == 1).all()
    label = run_300.origination_rows.set_index("person_id")["true_default"]
    assert (read_back["default_label"].to_numpy() == read_back["person_id"].map(label).to_numpy()).all()


def _expected_alt_data(run) -> pd.DataFrame:
    person = run["person"]
    sim = run["sim"]
    mb = run["month_behaviour"].merge(person[["person_id", "origination_month"]], on="person_id")
    pre = mb[mb["month"] < mb["origination_month"]].copy()
    pre["late"] = pre["electricity_state"] != "on_time"
    pre["disconnected"] = pre["electricity_state"].isin(DISCONNECTED)
    pre["net"] = pre["wallet_inflow"] - pre["wallet_outflow"]
    by_person = pre.groupby("person_id")
    first_sim = sim.sort_values("sim_id").drop_duplicates("person_id").set_index("person_id")["prepaid"]
    shared = pd.concat([run["electricity_account"], run["ewallet_account"]]).groupby("household_id")["shared"].any()
    return pd.DataFrame({
        "sim_count": sim.groupby("person_id").size(),
        "prepaid_flag": first_sim.astype(int),
        "electricity_late_rate": by_person["late"].mean(),
        "electricity_disconnect_count": by_person["disconnected"].sum(),
        "remittance_inflow_mean": by_person["wallet_inflow"].mean(),
        "ewallet_net_flow_mean": by_person["net"].mean(),
        "shared_account_flag": person.set_index("person_id")["household_id"].map(shared).astype(int),
    })


def test_alt_data_recomputed(run_300, read_back):
    expected = _expected_alt_data(run_300)
    actual = read_back.set_index("person_id")
    for column in ALT_DATA:
        got = actual[column].astype(float)
        want = expected[column].reindex(got.index).astype(float)
        assert want.notna().all(), column
        assert np.allclose(got.to_numpy(), want.to_numpy(), rtol=0.0, atol=1e-6), column


def _cell_values(column: str, rows: pd.DataFrame) -> np.ndarray:
    return np.array([
        int.from_bytes(hashlib.sha256(f"{column}|{p}|{m}".encode("utf-8")).digest()[:4], "big")
        for p, m in zip(rows["person_id"].tolist(), rows["month"].tolist())
    ], dtype=np.int64)


def _after(rows):
    return rows["month"] > rows["origination_month"]


def _from_origination(rows):
    return rows["month"] >= rows["origination_month"]


def _before(rows):
    return rows["month"] < rows["origination_month"]


ROUNDS = [
    ("ability", "ground_truth", _after, "value"),
    ("willingness", "ground_truth", _after, "value"),
    ("vendor_signal", "ground_truth", _after, "value"),
    ("true_default", "ground_truth", _after, "one"),
    ("topup_amount", "month_behaviour", _from_origination, "value"),
    ("wallet_inflow", "month_behaviour", _from_origination, "value"),
    ("wallet_outflow", "month_behaviour", _from_origination, "value"),
    ("region_month_shock", "ground_truth", _after, "flip"),
    ("post_origination_shock", "ground_truth", _after, "flip"),
    ("electricity_state", "month_behaviour", _from_origination, "state"),
    ("control", "month_behaviour", _before, "value"),
]


def _edit(frame: pd.DataFrame, column: str, mask: pd.Series, how: str) -> None:
    if how == "value":
        values = _cell_values(column, frame.loc[mask].sort_values(["person_id", "month"]))
        steps = np.diff(values)
        assert (steps > 0).any() and (steps < 0).any(), column
        ordered = frame.loc[mask].sort_values(["person_id", "month"]).index
        frame.loc[ordered, column] = values.astype(np.float64)
    elif how == "one":
        frame.loc[mask, column] = 1
    elif how == "flip":
        frame.loc[mask, column] = ~frame.loc[mask, column]
    else:
        frame.loc[mask, column] = np.where(frame.loc[mask, column] == "on_time", "unpaid_past_30d", "on_time")


def _features_in_new_process(source: Path, round_dir: Path, table: str, frame: pd.DataFrame) -> str:
    round_dir.mkdir()
    for name in PANEL_FILES:
        if name != f"{table}.parquet":
            shutil.copy2(source / name, round_dir / name)
    frame.drop(columns="origination_month").to_parquet(round_dir / f"{table}.parquet", index=False)
    assert sorted(p.name for p in round_dir.iterdir()) == sorted(PANEL_FILES)
    subprocess.run(
        [sys.executable, "-c", "import sys; from scorecheck import features; features.from_panel(sys.argv[1])",
         str(round_dir)],
        check=True,
        timeout=300,
    )
    return logical_hash(pd.read_parquet(round_dir / "application_features.parquet"))


def test_post_origination_invariance(run_300, tmp_path):
    baseline = logical_hash(run_300["application_features"])
    origination = run_300["person"][["person_id", "origination_month"]]
    frames = {
        table: run_300[table].merge(origination, on="person_id", how="left")
        for table in ("ground_truth", "month_behaviour")
    }
    pristine = {table: frame.copy() for table, frame in frames.items()}

    for label, table, window, how in ROUNDS:
        column = "wallet_inflow" if label == "control" else label
        frame = frames[table]
        mask = window(frame)
        assert mask.any(), label
        original = frame[column].copy()
        _edit(frame, column, mask, how)

        assert sorted(frame[column].tolist()) != sorted(original.tolist()), label
        if label == "true_default":
            assert frame.loc[mask, column].sum() > original[mask].sum()

        digest = _features_in_new_process(run_300.run_dir, tmp_path / label, table, frame)
        if label == "control":
            assert digest != baseline, "control edit before origination left the features unchanged"
        else:
            assert digest == baseline, f"{label} edit after origination changed the features"

        frame[column] = original
        pd.testing.assert_frame_equal(frame, pristine[table])


def test_vendor_columns_null(read_back):
    for column in VENDOR:
        assert read_back[column].isna().all(), column


def test_detail_ties(run_300, read_back):
    person = run_300["person"].set_index("person_id")
    region = run_300["household"].set_index("household_id")["region"]
    assert (read_back["age_years"].to_numpy() == read_back["person_id"].map(person["age_years"]).to_numpy()).all()
    expected_region = read_back["person_id"].map(person["household_id"]).map(region)
    assert (read_back["region"].to_numpy() == expected_region.to_numpy()).all()


def test_core_columns(read_back):
    for column in CORE:
        assert read_back[column].isna().sum() == 0, column
        if column != "label_observed":
            assert read_back[column].nunique() >= 2, column
    assert read_back["history_months"].min() <= 3
    assert read_back["history_months"].max() >= 12


def test_no_ground_truth_leak(run_300):
    shared = set(run_300["application_features"].columns) & set(run_300["ground_truth"].columns)
    assert shared == {"person_id"}
