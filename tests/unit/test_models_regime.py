"""Challenger refits for the Feature 004 experiment."""

import numpy as np
import pandas as pd
import pytest

from scorecheck import config
from support.models import read_scores
from support.vendor import copied_run, read_features

LINES = [
    "lightgbm", "lightgbm_monotone", "xgboost", "xgboost_monotone", "hist_gradient_boosting",
    "hist_gradient_boosting_monotone", "scorecard_probability",
]


@pytest.mark.parametrize("monotone", [False, True])
def test_woe_transform_equals_the_fit_time_weights_on_training_rows(monotone):
    from scorecheck import models
    from scorecheck.models import regime

    rng = np.random.default_rng(5)
    cases = [
        rng.normal(size=400),
        np.round(rng.normal(size=400), 1),              # many ties
        rng.integers(0, 3, 400).astype(float),          # few distinct values, bins collapse
        np.full(400, 2.0),                              # constant
        rng.exponential(size=400),
    ]
    for values in cases:
        labels = (rng.random(400) < 1 / (1 + np.exp(-values + 1.5))).astype(np.int64)
        expected = models.binned_weight_of_evidence(values, labels, monotone)
        got = regime.woe_transform(values, labels, monotone, values)
        assert np.array_equal(got, expected)


def test_woe_transform_applies_the_training_bins_to_unseen_rows():
    from scorecheck.models import regime

    values = np.arange(100, dtype=float)
    labels = (values >= 50).astype(np.int64)
    low = regime.woe_transform(values, labels, False, np.array([-5.0, 0.0, 99.0, 500.0]))
    train = regime.woe_transform(values, labels, False, values)
    assert low[0] == train[0] == low[1]
    assert low[2] == train[-1] == low[3]
    assert low[0] != low[2]


def test_refit_returns_none_when_the_labels_cannot_train(run_300):
    from scorecheck.models import regime

    features = read_features(run_300.run_dir)
    ids = features["application_id"].to_numpy()[:50]
    assert regime.refit(features, np.array([], dtype=np.int64), np.array([], dtype=np.int64), config.SEED) is None
    assert regime.refit(features, ids, np.zeros(50, dtype=np.int64), config.SEED) is None
    assert regime.refit(features, ids, np.ones(50, dtype=np.int64), config.SEED) is None


def test_refit_scores_the_whole_book(run_300):
    from scorecheck.models import regime

    features = read_features(run_300.run_dir)
    ordered = features.sort_values("application_id", kind="mergesort")
    ids = ordered["application_id"].to_numpy()[::2]
    labels = (np.arange(len(ids)) % 3 == 0).astype(np.int64)
    frame = regime.refit(features, ids, labels, config.SEED)
    assert list(frame.columns) == ["application_id", *LINES]
    assert np.array_equal(frame["application_id"].to_numpy(), ordered["application_id"].to_numpy())
    for line in LINES:
        assert frame[line].between(0.0, 1.0).all()
        assert frame[line].nunique() > 1


def test_refit_on_everything_reproduces_feature_003(run_2000, tmp_path):
    from scorecheck import models
    from scorecheck.models import regime

    run_dir = copied_run(run_2000.run_dir, tmp_path)
    models.publish(run_dir)
    published = read_scores(run_dir)
    features = read_features(run_dir)
    ordered = features.sort_values("application_id", kind="mergesort")
    got = regime.refit(features, ordered["application_id"].to_numpy(), ordered["default_label"].to_numpy(), config.SEED)
    for line in LINES:
        assert np.array_equal(got[line].to_numpy(), published[line].to_numpy()), line


def test_write_layout(run_300, tmp_path):
    from scorecheck.models import regime

    features = read_features(run_300.run_dir)
    ordered = features.sort_values("application_id", kind="mergesort")
    frame = regime.refit(features, ordered["application_id"].to_numpy(), ordered["default_label"].to_numpy(), config.SEED)
    target = tmp_path / "regime"
    regime.write(target, frame, "feature-hash", "fit-hash")
    folder = target / "challengers"
    assert sorted(p.name for p in folder.iterdir()) == ["bind.json", "scores.parquet"]
    pd.testing.assert_frame_equal(pd.read_parquet(folder / "scores.parquet"), frame)
