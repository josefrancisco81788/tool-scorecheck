"""E6: the learning-curve table and the gap arithmetic."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from support.experiment import LINES

ROOT = Path(__file__).resolve().parents[2]


def _fixture_module():
    spec = importlib.util.spec_from_file_location("feature_004_fixtures", ROOT / "docs" / "choices" / "feature-004-fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gap_matches_the_sklearn_fixture():
    from scorecheck.experiment import Gap, gap

    fixture = _fixture_module()
    got = gap(fixture.LABELS, fixture.VENDOR, fixture.CHALLENGER)
    assert isinstance(got, Gap)
    assert got.auc == pytest.approx(fixture.EXPECTED["auc_gap"], abs=1e-12)
    assert got.log_loss == pytest.approx(fixture.EXPECTED["log_loss_gap"], abs=1e-12)
    assert got.brier == pytest.approx(fixture.EXPECTED["brier_gap"], abs=1e-12)


def test_negative_auc_gap_is_kept():
    from scorecheck.experiment import gap

    fixture = _fixture_module()
    got = gap(fixture.LABELS, fixture.VENDOR, fixture.CHALLENGER)
    assert got.auc < 0
    assert got.auc_low <= got.auc <= got.auc_high


def test_gap_field_names():
    from scorecheck.experiment import Gap

    assert Gap._fields == (
        "auc", "log_loss", "brier", "auc_low", "auc_high", "log_loss_low", "log_loss_high", "brier_low", "brier_high",
    )


def test_one_class_labels_have_no_gap():
    from scorecheck.experiment import gap

    assert gap(np.zeros(5, dtype=int), np.linspace(0.1, 0.5, 5), np.linspace(0.2, 0.6, 5)) is None
    assert gap(np.ones(5, dtype=int), np.linspace(0.1, 0.5, 5), np.linspace(0.2, 0.6, 5)) is None


def test_curve_columns_and_shape(experiment_2000):
    curves = experiment_2000.curves
    assert list(curves.columns) == [
        "regime", "checkpoint", "line", "holdout_n", "holdout_bads", "vendor_fit_n", "vendor_fit_bads",
        "vendor_fit_test_cell_n", "line_fit_n", "line_fit_bads", "line_fit_test_cell_n", "vendor_auc", "line_auc",
        "auc_gap", "auc_gap_low", "auc_gap_high", "vendor_log_loss", "line_log_loss", "log_loss_gap",
        "log_loss_gap_low", "log_loss_gap_high", "vendor_brier", "line_brier", "brier_gap", "brier_gap_low",
        "brier_gap_high",
    ]
    assert len(curves) == 84
    assert set(curves["line"]) == set(LINES)


def test_curve_metrics_equal_sklearn_on_the_held_out_scores(experiment_2000):
    curves = experiment_2000.curves
    heldout = experiment_2000.heldout
    for row in curves.itertuples(index=False):
        part = heldout[(heldout["regime"] == row.regime) & (heldout["checkpoint"] == row.checkpoint)]
        label = part["bad_6m"].astype(int).to_numpy()
        vendor = part["vendor_probability"].to_numpy()
        line = part[row.line].to_numpy()
        assert row.vendor_auc == pytest.approx(roc_auc_score(label, vendor), abs=1e-12)
        assert row.line_auc == pytest.approx(roc_auc_score(label, line), abs=1e-12)
        assert row.auc_gap == pytest.approx(row.vendor_auc - row.line_auc, abs=1e-12)
        assert row.vendor_log_loss == pytest.approx(log_loss(label, vendor), abs=1e-12)
        assert row.line_log_loss == pytest.approx(log_loss(label, line), abs=1e-12)
        assert row.log_loss_gap == pytest.approx(row.vendor_log_loss - row.line_log_loss, abs=1e-12)
        assert row.vendor_brier == pytest.approx(brier_score_loss(label, vendor), abs=1e-12)
        assert row.line_brier == pytest.approx(brier_score_loss(label, line), abs=1e-12)
        assert row.brier_gap == pytest.approx(row.vendor_brier - row.line_brier, abs=1e-12)


def test_gaps_are_the_raw_signed_difference(experiment_2000):
    curves = experiment_2000.curves
    assert np.isfinite(curves[["auc_gap", "log_loss_gap", "brier_gap"]].to_numpy()).all()
    # Nothing is clipped at zero or dropped: the table holds vendor minus challenger as it came out.
    for metric in ("auc", "log_loss", "brier"):
        assert np.allclose(curves[f"{metric}_gap"], curves[f"vendor_{metric}"] - curves[f"line_{metric}"], atol=1e-12)
