"""E2: approve from the vendor score alone, plus a random 5% test cell."""

import numpy as np
import pandas as pd

from scorecheck import config
from scorecheck._streams import Streams
from support.experiment import prepare


def test_approve_edges():
    from scorecheck.experiment import APPROVAL_MAX_PROBABILITY, approve

    assert APPROVAL_MAX_PROBABILITY == 0.0185
    assert not approve(0.0185)
    assert approve(np.nextafter(0.0185, 0.0))
    assert not approve(np.nextafter(0.0185, 1.0))
    assert approve(0.0)
    assert not approve(1.0)
    got = approve(np.array([0.0, 0.0184, 0.0185, 0.5]))
    assert got.tolist() == [True, True, False, False]
    assert approve(0.05, 0.06)
    assert not approve(0.06, 0.06)
    assert approve(np.array([0.1, 0.3]), 0.2).tolist() == [True, False]


def _window_four(prepared):
    """Applications decided by the published ledger: originated in months 1 to 8."""
    from scorecheck.vendor import regime

    ledger = regime.read_published(prepared.run_dir)
    out = prepared.outcomes
    last = out[(out["regime"] == "data_owner") & (out["checkpoint"] == 24)].reset_index(drop=True)
    assert np.array_equal(last["application_id"].to_numpy(), ledger["application_id"].to_numpy())
    draw = Streams(config.SEED, "experiment")("test_cell").random(len(last))
    return last, ledger["probability"].to_numpy(), draw


def test_test_cell_is_five_percent_of_would_be_declines(experiment_2000):
    last, probability, draw = _window_four(experiment_2000)
    early = (last["origination_month"] <= 8).to_numpy()
    non_holdout = ~last["holdout"].to_numpy()
    declined = (probability >= 0.0185) & early & non_holdout
    expected_cell = declined & (draw < 0.05)
    assert np.array_equal(last["test_cell"].to_numpy() & early, expected_cell)
    approved_by_cutoff = (probability < 0.0185) & early
    assert np.array_equal(last["approved"].to_numpy()[early & non_holdout], (approved_by_cutoff | expected_cell)[early & non_holdout])
    share = expected_cell.sum() / declined.sum()
    assert 0.02 <= share <= 0.09
    assert not last.loc[last["holdout"], "test_cell"].any()


def test_cutoff_approves_most_of_a_small_book(experiment_2000):
    # The cutoff is a fixed number set at the 80th percentile of the default book. On the 2,000
    # household book the published ledger puts about 93% under it. The default-book share (about
    # 80%) is asserted in tests/integration/test_cli_run.py.
    last, probability, _ = _window_four(experiment_2000)
    early = (last["origination_month"] <= 8).to_numpy()
    share = float((probability[early] < 0.0185).mean())
    assert 0.85 <= share <= 0.97


def test_outcomes_do_not_change_month_4_approvals(run_300, tmp_path):
    flipped_source = tmp_path / "source"
    flipped_source.mkdir()
    import shutil

    shutil.copytree(run_300.run_dir, flipped_source / run_300.run_dir.name)
    flipped_dir = flipped_source / run_300.run_dir.name
    truth = pd.read_parquet(flipped_dir / "ground_truth.parquet")
    truth["true_default"] = 1 - truth["true_default"]
    truth.to_parquet(flipped_dir / "ground_truth.parquet", index=False)

    base = prepare(run_300.run_dir, tmp_path / "base")
    flip = prepare(flipped_dir, tmp_path / "flip")
    columns = ["application_id", "regime", "checkpoint", "approved", "test_cell", "on_book", "cutoff"]
    for checkpoint in (4, 8):
        a = base.outcomes[base.outcomes["checkpoint"] == checkpoint][columns].reset_index(drop=True)
        b = flip.outcomes[flip.outcomes["checkpoint"] == checkpoint][columns].reset_index(drop=True)
        assert a.equals(b), checkpoint
    assert not base.outcomes["matured_label"].equals(flip.outcomes["matured_label"])


def _window(origination_month):
    return np.ceil(origination_month / 4).astype(int)


def test_each_window_cutoff_is_the_80th_percentile_of_its_model(experiment_2000):
    out = experiment_2000.outcomes
    last = out[(out["regime"] == "data_owner") & (out["checkpoint"] == 24)].reset_index(drop=True)
    last = last.assign(window=_window(last["origination_month"]))
    trained = [r for r in experiment_2000.vendor_results if r is not None]
    month = last["origination_month"].to_numpy()
    found_refit_window = 0
    for window, rows in last.groupby("window"):
        cutoffs = rows["cutoff"].unique()
        assert len(cutoffs) == 1
        if window <= 2:
            assert cutoffs[0] == 0.0185
            continue
        in_window = (_window(month) == window)
        matches = [
            m for m in trained
            if float(np.quantile(m["probability"].to_numpy()[in_window], 0.8)) == cutoffs[0]
        ]
        assert matches, window
        found_refit_window += 1
    assert found_refit_window >= 2


def test_later_windows_decline_about_a_fifth(experiment_2000):
    out = experiment_2000.outcomes
    last = out[(out["regime"] == "data_owner") & (out["checkpoint"] == 24)]
    window = _window(last["origination_month"])
    declined = (~last["approved"]) | last["test_cell"]
    for number in (3, 4, 5):
        rows = window == number
        if rows.sum() >= 100:
            assert 0.15 <= declined[rows].mean() <= 0.25, number


def test_test_cell_is_about_five_percent_of_non_holdout_declines(experiment_2000):
    out = experiment_2000.outcomes
    last = out[(out["regime"] == "data_owner") & (out["checkpoint"] == 24)]
    declined = ((~last["approved"]) | last["test_cell"]) & ~last["holdout"] & last["on_book"]
    share = last["test_cell"].sum() / declined.sum()
    assert 0.03 <= share <= 0.07
