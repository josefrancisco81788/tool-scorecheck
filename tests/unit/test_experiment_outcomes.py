"""E9: which outcomes were hidden is recorded per applicant, checkpoint, and regime."""

import pandas as pd

from scorecheck import rundir
from scorecheck.logical_hash import logical_hash
from support.experiment import CHECKPOINTS, REGIMES, experiment_dir

COLUMNS = [
    "application_id", "checkpoint", "regime", "origination_month", "holdout", "on_book", "approved",
    "test_cell", "label_observed", "matured_label", "cutoff",
]


def test_experiment_dir_is_a_sibling(tmp_path):
    run_dir = tmp_path / "processed" / "abc"
    assert rundir.experiment_dir(run_dir) == tmp_path / "experiment" / "abc"
    assert experiment_dir(run_dir) == rundir.experiment_dir(run_dir)


def test_outcomes_shape_and_order(experiment_2000):
    out = experiment_2000.outcomes
    n = len(experiment_2000.features)
    assert list(out.columns) == COLUMNS
    assert len(out) == len(REGIMES) * len(CHECKPOINTS) * n
    keys = list(zip(out["regime"], out["checkpoint"], out["application_id"]))
    expected = [(r, c, a) for r in REGIMES for c in CHECKPOINTS for a in sorted(experiment_2000.features["application_id"])]
    assert keys == expected
    assert str(out["matured_label"].dtype) == "Int64"
    for column in ("holdout", "on_book", "approved", "test_cell", "label_observed"):
        assert out[column].dtype == bool, column


def test_approval_and_test_cell_flags(experiment_2000):
    out = experiment_2000.outcomes
    assert (out["on_book"] == (out["origination_month"] <= out["checkpoint"])).all()
    assert not out.loc[~out["on_book"], ["approved", "test_cell", "label_observed"]].any().any()
    assert out.loc[out["test_cell"], "approved"].all()
    assert out["test_cell"].any()
    assert (out["approved"] & ~out["test_cell"]).any()
    assert (out["on_book"] & ~out["approved"]).any()


def test_decisions_do_not_change_after_the_window(experiment_2000):
    out = experiment_2000.outcomes
    one = out[out["regime"] == "data_owner"].pivot(index="application_id", columns="checkpoint", values="approved")
    for earlier, later in zip(CHECKPOINTS, CHECKPOINTS[1:]):
        decided = one[earlier]
        assert (one.loc[decided, later]).all()


def test_regimes_share_decisions(experiment_2000):
    out = experiment_2000.outcomes
    a = out[out["regime"] == "vendor_only"].drop(columns="regime").reset_index(drop=True)
    b = out[out["regime"] == "data_owner"].drop(columns="regime").reset_index(drop=True)
    assert a.equals(b)


def test_application_features_is_not_rewritten(run_300, tmp_path):
    from support.experiment import prepare

    path = run_300.run_dir / "application_features.parquet"
    before = logical_hash(pd.read_parquet(path))
    raw_before = path.read_bytes()
    prepared = prepare(run_300.run_dir, tmp_path)
    copied = prepared.run_dir / "application_features.parquet"
    assert logical_hash(pd.read_parquet(copied)) == before
    assert copied.read_bytes() == raw_before
    assert {p.name for p in prepared.run_dir.iterdir()} == {p.name for p in run_300.run_dir.iterdir()}
