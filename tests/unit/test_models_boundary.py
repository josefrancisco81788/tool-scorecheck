import hashlib
from pathlib import Path

import pytest

from scorecheck import config
from support.models import scores_dir
from support.runs import generate_run
from support.vendor import copied_run, ledger_dir, ledger_hash, read_features, two_class, write_features

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_SHA256 = "2f3cd09aeebd85f7b9634bc9d588a39ac812bcc70ff9feb21ddd43664b7a0fbc"
SCORE_COLUMNS = [
    "application_id", "vendor_probability", "lightgbm", "lightgbm_monotone", "xgboost",
    "xgboost_monotone", "hist_gradient_boosting", "hist_gradient_boosting_monotone",
    "scorecard_probability", "scorecard_points",
]
BANNED = ("approval", "decision", "decline", "reason_1", "reason_2", "reason_3")


def test_models_do_not_open_the_vendor_interior(tmp_path, monkeypatch):
    import lightgbm

    from scorecheck.models import publish
    from scorecheck.vendor import LedgerMissing, StaleLedger, publish as vendor_publish

    text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src" / "scorecheck" / "models").rglob("*.py"))
    assert "scorecheck.vendor" + "._private" not in text
    assert "ledger.parquet" not in text
    assert "pred_contrib" not in text

    calls = []
    real_train = lightgbm.train

    def spy(*args, **kwargs):
        calls.append("train")
        return real_train(*args, **kwargs)

    monkeypatch.setattr(lightgbm, "train", spy)
    run_dir = generate_run(config.SEED, 70, tmp_path / "missing").run_dir
    assert len(read_features(run_dir)) <= 300
    assert not scores_dir(run_dir).exists()
    with pytest.raises(LedgerMissing):
        publish(run_dir)
    assert calls == []
    assert not scores_dir(run_dir).exists()

    stale = generate_run(config.SEED, 70, tmp_path / "stale").run_dir
    two_class(stale)
    vendor_publish(stale)
    calls.clear()
    edited = read_features(stale)
    edited["income"] = edited["income"] + 1.0
    write_features(stale, edited)
    with pytest.raises(StaleLedger):
        publish(stale)
    assert calls == []
    assert not scores_dir(stale).exists()


def test_shadow_does_not_decide(run_300, tmp_path, monkeypatch):
    import pandas as pd

    from scorecheck import explain
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    vendor_publish(run_dir)
    before = ledger_hash(pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet"))

    def refuse(*args, **kwargs):
        raise AssertionError("publish called explain.draft")

    monkeypatch.setattr(explain, "draft", refuse)
    publish(run_dir)
    frame = pd.read_parquet(scores_dir(run_dir) / "scores.parquet")
    assert list(frame.columns) == SCORE_COLUMNS
    for name in BANNED:
        assert name not in frame.columns
    after = ledger_hash(pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet"))
    assert after == before
    from scorecheck.models import line

    line(run_dir, int(frame["application_id"].iloc[0]))


def test_no_stored_model(run_300, tmp_path):
    from scorecheck import models
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    vendor_publish(run_dir)
    models.publish(run_dir)
    assert sorted(p.name for p in scores_dir(run_dir).iterdir()) == ["bind.json", "scores.parquet"]
    for name in ("Booster", "booster", "XGBClassifier", "HistGradientBoostingClassifier"):
        assert not hasattr(models, name)


def test_public_surface():
    from scorecheck import models

    assert models.__all__ == [
        "publish", "line", "ChallengerLines", "ScoresMissing", "StaleScores", "UnknownApplicant",
    ]


def test_generate_run_stops_at_from_panel(tmp_path, monkeypatch):
    from scorecheck import models

    def refuse(*args, **kwargs):
        raise AssertionError("generate_run called models.publish")

    monkeypatch.setattr(models, "publish", refuse)
    run = generate_run(config.SEED, 300, tmp_path / "processed")
    assert not scores_dir(run.run_dir).exists()
    assert not ledger_dir(run.run_dir).exists()


def test_golden_script_stops_at_from_panel():
    text = (ROOT / "scripts" / "write_golden_panel.py").read_text(encoding="utf-8")
    assert "features.from_panel" in text
    for banned in ("models.publish", "scorecheck.models", "vendor.publish", "scorecheck.vendor"):
        assert banned not in text
    digest = hashlib.sha256((ROOT / "tests" / "fixtures" / "golden" / "panel.json").read_bytes()).hexdigest()
    assert digest == GOLDEN_SHA256
