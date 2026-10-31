import numpy as np
import pandas as pd

import pytest

from support.models import read_scores, scores_dir
from support.vendor import copied_run, one_class, read_features, two_class, write_features

PROBABILITY_FIELDS = (
    "vendor_probability",
    "lightgbm",
    "lightgbm_monotone",
    "xgboost",
    "xgboost_monotone",
    "hist_gradient_boosting",
    "hist_gradient_boosting_monotone",
    "scorecard_probability",
)


def _points(value) -> float | None:
    return None if pd.isna(value) else float(value)


def test_line_returns_scores(run_300, tmp_path, monkeypatch):
    import lightgbm

    from scorecheck import vendor
    from scorecheck.models import ChallengerLines, line, publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    vendor.publish(run_dir)
    publish(run_dir)
    frame = read_scores(run_dir)

    def refuse_score(*args, **kwargs):
        raise AssertionError("line called vendor.score")

    def refuse_train(*args, **kwargs):
        raise AssertionError("line called lightgbm.train")

    monkeypatch.setattr(vendor, "score", refuse_score)
    monkeypatch.setattr(lightgbm, "train", refuse_train)
    ids = frame["application_id"].tolist()
    for application_id in (ids[0], ids[len(ids) // 2], ids[-1]):
        got = line(run_dir, int(application_id))
        assert isinstance(got, ChallengerLines)
        row = frame.loc[frame["application_id"] == application_id].iloc[0]
        for name in PROBABILITY_FIELDS:
            assert getattr(got, name) == float(row[name])
            assert 0.0 <= getattr(got, name) <= 1.0
        assert got.scorecard_points == _points(row["scorecard_points"])


def test_scores_errors(run_300, tmp_path):
    from scorecheck.models import ScoresMissing, StaleScores, UnknownApplicant, line, publish
    from scorecheck.vendor import LedgerMissing, StaleLedger
    from scorecheck.vendor import UnknownApplicant as VendorUnknownApplicant
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path / "missing")
    scores = scores_dir(run_dir)
    with pytest.raises(ScoresMissing):
        line(run_dir, 1)
    assert not scores.exists()

    present = copied_run(run_300.run_dir, tmp_path / "present")
    two_class(present)
    vendor_publish(present)
    publish(present)
    directory = scores_dir(present)
    kept = {name: (directory / name).read_bytes() for name in ("scores.parquet", "bind.json")}
    (directory / "scores.parquet").unlink()
    with pytest.raises(ScoresMissing):
        line(present, 1)
    (directory / "bind.json").unlink()
    (directory / "scores.parquet").write_bytes(kept["scores.parquet"])
    with pytest.raises(ScoresMissing):
        line(present, 1)
    (directory / "bind.json").write_bytes(kept["bind.json"])

    frame = read_scores(present)
    missing = int(frame["application_id"].max()) + 1
    with pytest.raises(UnknownApplicant):
        line(present, missing)
    assert {name: (directory / name).read_bytes() for name in kept} == kept

    edited = read_features(present)
    edited["income"] = edited["income"] + 1.0
    write_features(present, edited)
    known = int(frame["application_id"].iloc[0])
    with pytest.raises(StaleScores):
        line(present, known)

    classes = (ScoresMissing, StaleScores, UnknownApplicant)
    vendor_errors = (LedgerMissing, StaleLedger, VendorUnknownApplicant)
    for left in classes:
        assert issubclass(left, Exception)
        for right in classes:
            if left is not right:
                assert not issubclass(left, right)
        for vendor_error in vendor_errors:
            assert not issubclass(left, vendor_error)


def test_replaced_features_are_not_served(run_300, tmp_path):
    from scorecheck.models import StaleScores, line, publish
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    one_class(run_dir, 0)
    vendor_publish(run_dir)
    publish(run_dir)
    application_id = int(read_features(run_dir)["application_id"].iloc[0])
    assert line(run_dir, application_id).lightgbm == 0.0
    edited = read_features(run_dir)
    edited["income"] = edited["income"] + 1.0
    write_features(run_dir, edited)
    with pytest.raises(StaleScores):
        line(run_dir, application_id)
    one_class(run_dir, 1)
    vendor_publish(run_dir)
    publish(run_dir)
    got = line(run_dir, application_id)
    for name in PROBABILITY_FIELDS:
        assert getattr(got, name) == 1.0
