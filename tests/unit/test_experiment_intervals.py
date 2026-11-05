"""E7: the numbers behind each point, and the 95% intervals."""

import math

import numpy as np
import pandas as pd
import pytest

from support.experiment import CHECKPOINTS, REGIMES

DELONG_LABELS = np.array([0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1], dtype=np.int64)
DELONG_VENDOR = np.array([0.20, 0.30, 0.25, 0.40, 0.35, 0.45, 0.55, 0.50, 0.60, 0.48, 0.70, 0.42])
DELONG_LINE = np.array([0.10, 0.15, 0.12, 0.18, 0.20, 0.22, 0.80, 0.85, 0.78, 0.90, 0.88, 0.83])
PINNED_VARIANCE = 0.0015432098765432096


def naive_delong_variance(labels, a, b) -> float:
    """Variance of the AUC difference from the structural components, O(m * n)."""
    labels = np.asarray(labels)
    positive = np.flatnonzero(labels == 1)
    negative = np.flatnonzero(labels == 0)

    def psi(x, y):
        return 1.0 if x > y else 0.5 if x == y else 0.0

    def components(scores):
        v10 = np.array([np.mean([psi(scores[i], scores[j]) for j in negative]) for i in positive])
        v01 = np.array([np.mean([psi(scores[i], scores[j]) for i in positive]) for j in negative])
        return v10, v01

    a10, a01 = components(np.asarray(a))
    b10, b01 = components(np.asarray(b))
    d10, d01 = a10 - b10, a01 - b01
    return float(np.var(d10, ddof=1) / len(positive) + np.var(d01, ddof=1) / len(negative))


def test_delong_variance_equals_the_naive_computation():
    from scorecheck.experiment import _metrics

    rng = np.random.default_rng(3)
    for labels, a, b in [
        (DELONG_LABELS, DELONG_VENDOR, DELONG_LINE),
        (rng.integers(0, 2, 60), np.round(rng.random(60), 1), np.round(rng.random(60), 1)),
    ]:
        assert _metrics.delong_gap_variance(labels, a, b) == pytest.approx(naive_delong_variance(labels, a, b), rel=1e-12, abs=1e-15)


def test_delong_variance_pinned_literal():
    from scorecheck.experiment import _metrics

    value = _metrics.delong_gap_variance(DELONG_LABELS, DELONG_VENDOR, DELONG_LINE)
    assert value == pytest.approx(PINNED_VARIANCE, rel=1e-12)


def test_gap_interval_uses_that_variance():
    from scorecheck.experiment import gap

    got = gap(DELONG_LABELS, DELONG_VENDOR, DELONG_LINE)
    half = 1.96 * math.sqrt(naive_delong_variance(DELONG_LABELS, DELONG_VENDOR, DELONG_LINE))
    assert got.auc_high - got.auc == pytest.approx(half, rel=1e-9)
    assert got.auc - got.auc_low == pytest.approx(half, rel=1e-9)


def test_log_loss_and_brier_intervals_are_paired_normal_intervals():
    from scorecheck.experiment import gap

    eps = np.finfo(np.float64).eps
    labels = np.asarray(DELONG_LABELS)
    a = np.clip(np.asarray(DELONG_VENDOR), eps, 1 - eps)
    b = np.clip(np.asarray(DELONG_LINE), eps, 1 - eps)

    def loss(p):
        return -(labels * np.log(p) + (1 - labels) * np.log(1 - p))

    got = gap(labels, DELONG_VENDOR, DELONG_LINE)
    for diff, centre, low, high in [
        (loss(a) - loss(b), got.log_loss, got.log_loss_low, got.log_loss_high),
        ((a - labels) ** 2 - (b - labels) ** 2, got.brier, got.brier_low, got.brier_high),
    ]:
        half = 1.96 * diff.std(ddof=1) / math.sqrt(len(diff))
        assert high - centre == pytest.approx(half, rel=1e-9)
        assert centre - low == pytest.approx(half, rel=1e-9)


def _expected_fit(experiment, regime: str, checkpoint: int, arm: str) -> tuple[int, int, int]:
    """Counts of the fit behind the model scored at this point, from the outcomes table."""
    out = experiment.outcomes
    fits = experiment.fits
    mine = fits[(fits["regime"] == regime) & (fits["arm"] == arm) & (fits["checkpoint"] <= checkpoint) & fits["trained"]]
    mine = mine[mine["checkpoint"] > 0]
    if mine.empty:
        features = experiment.features
        keep = features["application_id"] % 5 != 0
        return int(keep.sum()), int(features.loc[keep, "default_label"].sum()), 0
    latest = int(mine["checkpoint"].max())
    rows = out[(out["regime"] == regime) & (out["checkpoint"] == latest) & out["label_observed"]]
    return len(rows), int(rows["matured_label"].sum()), int(rows["test_cell"].sum())


def test_counts_equal_the_actual_fit_sizes(experiment_2000):
    curves = experiment_2000.curves
    for row in curves.itertuples(index=False):
        n, bads, test_cell = _expected_fit(experiment_2000, row.regime, row.checkpoint, "vendor")
        assert (row.vendor_fit_n, row.vendor_fit_bads, row.vendor_fit_test_cell_n) == (n, bads, test_cell)
        arm_regime = row.regime
        n, bads, test_cell = _expected_fit(experiment_2000, arm_regime, row.checkpoint, "challenger")
        assert (row.line_fit_n, row.line_fit_bads, row.line_fit_test_cell_n) == (n, bads, test_cell)


def test_vendor_only_challenger_fit_is_the_starting_fit_forever(experiment_2000):
    curves = experiment_2000.curves
    frozen = curves[curves["regime"] == "vendor_only"]
    assert frozen[["line_fit_n", "line_fit_bads", "line_fit_test_cell_n"]].drop_duplicates().shape[0] == 1
    assert (frozen["line_fit_test_cell_n"] == 0).all()
    last = curves[(curves["regime"] == "data_owner") & (curves["checkpoint"] == 24)]
    assert (last["line_fit_n"] == last["vendor_fit_n"]).all()
    assert (last["line_fit_bads"] == last["vendor_fit_bads"]).all()
    assert (last["line_fit_test_cell_n"] == last["vendor_fit_test_cell_n"]).all()


def test_test_cell_accounts_appear_in_the_counts(experiment_2000):
    curves = experiment_2000.curves
    last = curves[curves["checkpoint"] == 24]
    assert (last["vendor_fit_test_cell_n"] > 0).all()
    assert (last["vendor_fit_test_cell_n"] < last["vendor_fit_n"]).all()


def test_each_interval_contains_its_gap(experiment_2000):
    curves = experiment_2000.curves
    for metric in ("auc", "log_loss", "brier"):
        gap_ = curves[f"{metric}_gap"]
        assert (curves[f"{metric}_gap_low"] <= gap_).all()
        assert (gap_ <= curves[f"{metric}_gap_high"]).all()
        assert (curves[f"{metric}_gap_high"] > curves[f"{metric}_gap_low"]).all()


def test_fits_table_matches_outcomes(experiment_2000):
    fits = experiment_2000.fits
    out = experiment_2000.outcomes
    assert list(fits.columns) == ["regime", "checkpoint", "arm", "trained", "n", "bads", "test_cell_n", "fit_ids_hash"]
    for regime in REGIMES:
        for checkpoint in CHECKPOINTS:
            rows = out[(out["regime"] == regime) & (out["checkpoint"] == checkpoint) & out["label_observed"]]
            for arm in ("vendor", "challenger"):
                mine = fits[(fits["regime"] == regime) & (fits["checkpoint"] == checkpoint) & (fits["arm"] == arm)]
                if arm == "challenger" and regime == "vendor_only":
                    assert mine.empty
                    continue
                assert len(mine) == 1
                item = mine.iloc[0]
                assert item["n"] == len(rows)
                assert item["bads"] == int(rows["matured_label"].sum())
                assert item["test_cell_n"] == int(rows["test_cell"].sum())
