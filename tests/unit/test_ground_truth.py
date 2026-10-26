import numpy as np
import pandas as pd

GROUND_TRUTH_COLUMNS = {
    "person_id", "month", "ability", "willingness", "region_month_shock", "post_origination_shock",
    "vendor_signal", "true_default",
}


def test_ground_truth_columns(run_300):
    assert set(run_300["ground_truth"].columns) == GROUND_TRUTH_COLUMNS


def test_ground_truth_grain(run_300):
    gt = run_300["ground_truth"]
    assert gt.duplicated(["person_id", "month"]).sum() == 0
    assert pd.api.types.is_integer_dtype(gt["month"])
    assert gt["month"].between(1, 24).all()
    assert len(gt) == 24 * len(run_300["person"])


def test_shock_columns(run_300):
    gt = run_300["ground_truth"]
    for column in ("region_month_shock", "post_origination_shock"):
        assert gt[column].dtype == bool, column
        assert set(gt[column]) == {True, False}, column


def test_no_shock_before_origination(run_300):
    gt = run_300["ground_truth"].merge(run_300["person"][["person_id", "origination_month"]], on="person_id")
    before = gt[gt["month"] < gt["origination_month"]]
    assert len(before) > 0
    assert not before["post_origination_shock"].any()


def test_true_default_absorbing(run_300):
    gt = run_300["ground_truth"]
    assert set(gt["true_default"].unique()) <= {0, 1}
    grid = gt.sort_values(["person_id", "month"])["true_default"].to_numpy().reshape(-1, 24)
    assert np.all(np.diff(grid, axis=1) >= 0)
