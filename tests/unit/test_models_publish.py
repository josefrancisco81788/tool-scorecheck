import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scorecheck import config, logical_hash
from scorecheck._streams import Streams
from support.models import read_scores, scores_dir, scores_hash
from support.runs import generate_run
from support.vendor import (
    copied_run,
    feature_hash,
    ledger_dir,
    ledger_hash,
    one_class,
    read_features,
    two_class,
    write_features,
)

ROOT = Path(__file__).resolve().parents[2]
MATRIX = (
    "utilization", "open_credit_count", "delinquency_count_30", "delinquency_count_60",
    "delinquency_count_90", "on_time_rate", "income", "dependents", "credit_amount",
    "installment_to_income", "payment_to_obligation_ratio", "history_months", "sim_count",
    "prepaid_flag", "electricity_late_rate", "electricity_disconnect_count",
    "remittance_inflow_mean", "ewallet_net_flow_mean", "shared_account_flag",
)
MONOTONE = {
    "utilization", "delinquency_count_30", "delinquency_count_60", "delinquency_count_90",
    "installment_to_income",
}
CONSTRAINTS = tuple(1 if name in MONOTONE else 0 for name in MATRIX)
DEMOGRAPHICS = ("age_years", "gender", "education", "marital_status", "region")
EXTERNAL = ("external_score_1", "external_score_2", "external_score_3")
LIGHTGBM_KEYS = {
    "objective", "deterministic", "force_row_wise", "device_type", "num_threads", "feature_fraction",
    "bagging_fraction", "bagging_freq", "num_leaves", "learning_rate", "verbose", "seed", "bagging_seed",
    "feature_fraction_seed", "data_random_seed",
}
XGB_KEYS = {
    "n_estimators", "learning_rate", "max_leaves", "grow_policy", "tree_method", "subsample",
    "colsample_bytree", "n_jobs", "random_state", "objective", "verbosity", "monotone_constraints",
}
HIST_KEYS = {
    "loss", "learning_rate", "max_iter", "max_leaf_nodes", "min_samples_leaf", "l2_regularization",
    "max_features", "max_bins", "categorical_features", "early_stopping", "random_state", "verbose",
    "monotonic_cst",
}
SCORE_COLUMNS = [
    "application_id", "vendor_probability", "lightgbm", "lightgbm_monotone", "xgboost",
    "xgboost_monotone", "hist_gradient_boosting", "hist_gradient_boosting_monotone",
    "scorecard_probability", "scorecard_points",
]


class LibraryCapture:
    def __init__(self) -> None:
        self.train = []
        self.dataset = 0
        self.xgb = []
        self.xgb_fit = []
        self.hist = []
        self.hist_fit = []
        self.logistic = []
        self.events = []


def _freeze(mapping: dict) -> dict:
    frozen = {}
    for key, value in mapping.items():
        if isinstance(value, (list, tuple)):
            frozen[key] = tuple(value)
        else:
            frozen[key] = value
    return frozen


def _spy_libraries(monkeypatch) -> LibraryCapture:
    import lightgbm
    import sklearn.ensemble
    import sklearn.linear_model
    import xgboost

    capture = LibraryCapture()
    real_train = lightgbm.train
    real_dataset = lightgbm.Dataset
    real_xgb = xgboost.XGBClassifier
    real_hist = sklearn.ensemble.HistGradientBoostingClassifier
    real_logistic = sklearn.linear_model.LogisticRegression

    def dataset(*args, **kwargs):
        capture.dataset += 1
        capture.events.append("lightgbm.Dataset")
        return real_dataset(*args, **kwargs)

    def train(params, train_set, num_boost_round=100, **kwargs):
        capture.events.append("lightgbm.train")
        capture.train.append((_freeze(dict(params)), num_boost_round, dict(kwargs)))
        return real_train(params, train_set, num_boost_round=num_boost_round, **kwargs)

    def xgb(**kwargs):
        capture.events.append("XGBClassifier")
        capture.xgb.append(_freeze(kwargs))
        model = real_xgb(**kwargs)
        real_fit = model.fit

        def fit(*args, **fit_kwargs):
            capture.xgb_fit.append(dict(fit_kwargs))
            return real_fit(*args, **fit_kwargs)

        model.fit = fit
        return model

    def hist(**kwargs):
        capture.events.append("HistGradientBoostingClassifier")
        capture.hist.append(_freeze(kwargs))
        model = real_hist(**kwargs)
        real_fit = model.fit

        def fit(*args, **fit_kwargs):
            capture.hist_fit.append(dict(fit_kwargs))
            return real_fit(*args, **fit_kwargs)

        model.fit = fit
        return model

    def logistic(*args, **kwargs):
        capture.events.append("LogisticRegression")
        capture.logistic.append(_freeze(kwargs))
        return real_logistic(*args, **kwargs)

    monkeypatch.setattr(lightgbm, "Dataset", dataset)
    monkeypatch.setattr(lightgbm, "train", train)
    monkeypatch.setattr(xgboost, "XGBClassifier", xgb)
    monkeypatch.setattr(sklearn.ensemble, "HistGradientBoostingClassifier", hist)
    monkeypatch.setattr(sklearn.linear_model, "LogisticRegression", logistic)
    return capture


def _publish_subprocess(run_dir: Path) -> None:
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from scorecheck.models import publish\n"
        "publish(Path(sys.argv[1]))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(run_dir)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr


def _assert_equal_frame(left: pd.DataFrame, right: pd.DataFrame) -> None:
    assert list(left.columns) == list(right.columns)
    for name in left.columns:
        assert np.array_equal(left[name].to_numpy(), right[name].to_numpy())


def test_publish_is_silent(run_300, tmp_path, capsys):
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    one = copied_run(run_300.run_dir, tmp_path / "one")
    two = copied_run(run_300.run_dir, tmp_path / "two")
    one_class(one, 0)
    two_class(two)
    vendor_publish(one)
    vendor_publish(two)
    capsys.readouterr()
    publish(one)
    one_out = capsys.readouterr()
    publish(two)
    two_out = capsys.readouterr()
    assert one_out.out == "" and one_out.err == ""
    assert two_out.out == "" and two_out.err == ""


def test_scores_path(tmp_path):
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    assert config.SEED == 20261024
    run = generate_run(config.SEED, 200, tmp_path / "processed")
    two_class(run.run_dir)
    vendor_publish(run.run_dir)
    publish(run.run_dir)
    scores = scores_dir(run.run_dir)
    assert rundir_id() == "6e6c82611fa89cf4"
    assert scores == run.run_dir.parent.with_name("models") / run.run_dir.name
    assert scores == tmp_path / "models" / "6e6c82611fa89cf4"
    assert sorted(p.name for p in scores.iterdir()) == ["bind.json", "scores.parquet"]
    payload = json.loads((scores / "bind.json").read_text(encoding="utf-8"))
    assert list(payload) == ["features_hash"]
    assert payload["features_hash"] == feature_hash(run.run_dir)
    frame = read_scores(run.run_dir)
    assert list(frame.columns) == SCORE_COLUMNS
    assert frame["application_id"].dtype == np.int64
    assert frame["application_id"].is_monotonic_increasing
    assert frame["application_id"].duplicated().sum() == 0
    for name in SCORE_COLUMNS[1:-1]:
        assert frame[name].dtype == np.float64
        assert np.isfinite(frame[name].to_numpy()).all()
        assert frame[name].between(0.0, 1.0).all()
    assert frame["scorecard_points"].dtype == np.float64
    assert np.isfinite(frame["scorecard_points"].to_numpy()).all()
    ledger = ledger_dir(run.run_dir)
    assert sorted(p.name for p in ledger.iterdir()) == ["bind.json", "ledger.parquet"]
    assert sorted(p.name for p in (tmp_path / "processed").iterdir()) == [run.run_dir.name]


def rundir_id() -> str:
    from scorecheck import rundir

    return rundir.run_id(config.SEED, 200)


def test_publish_leaves_run_dir_unchanged(run_300, tmp_path, monkeypatch):
    from scorecheck import vendor
    from scorecheck.models import publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    vendor.publish(run_dir)
    before_names = sorted(p.name for p in run_dir.iterdir())
    before_features = feature_hash(run_dir)
    before_ledger = ledger_hash(pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet"))
    calls = []
    monkeypatch.setattr(vendor, "publish", lambda *args, **kwargs: calls.append(1))
    publish(run_dir)
    assert calls == []
    assert sorted(p.name for p in run_dir.iterdir()) == before_names
    assert feature_hash(run_dir) == before_features
    assert ledger_hash(pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet")) == before_ledger
    assert "scores.parquet" not in before_names
    assert not (run_dir / "scores.parquet").exists()
    assert not (ledger_dir(run_dir) / "scores.parquet").exists()
    assert scores_dir(run_dir).parent.name == "models"


def test_vendor_score_is_copied_through_the_api(tmp_path, monkeypatch):
    import lightgbm
    import sklearn.ensemble
    import sklearn.linear_model
    import xgboost

    from scorecheck.models import publish
    from scorecheck.vendor import ReasonCode, VendorDecision, publish as vendor_publish

    run_dir = generate_run(config.SEED, 70, tmp_path / "processed").run_dir
    two_class(run_dir)
    vendor_publish(run_dir)
    assert len(read_features(run_dir)) <= 300
    events = []

    def score(path, application_id):
        events.append(("vendor.score", int(application_id)))
        return VendorDecision(
            0.25, ReasonCode.credit_stress, ReasonCode.capacity, ReasonCode.thin_file
        )

    def watch(name, real):
        def wrapped(*args, **kwargs):
            events.append((name,))
            return real(*args, **kwargs)

        return wrapped

    monkeypatch.setattr("scorecheck.vendor.score", score)
    monkeypatch.setattr(lightgbm, "train", watch("lightgbm.train", lightgbm.train))
    monkeypatch.setattr(xgboost, "XGBClassifier", watch("XGBClassifier", xgboost.XGBClassifier))
    monkeypatch.setattr(
        sklearn.ensemble,
        "HistGradientBoostingClassifier",
        watch("HistGradientBoostingClassifier", sklearn.ensemble.HistGradientBoostingClassifier),
    )
    monkeypatch.setattr(
        sklearn.linear_model,
        "LogisticRegression",
        watch("LogisticRegression", sklearn.linear_model.LogisticRegression),
    )
    publish(run_dir)
    score_at = [index for index, item in enumerate(events) if item[0] == "vendor.score"]
    trainer_at = [index for index, item in enumerate(events) if item[0] != "vendor.score"]
    assert score_at and trainer_at
    assert max(score_at) < min(trainer_at)
    expected = sorted(int(value) for value in read_features(run_dir)["application_id"])
    assert [events[index][1] for index in score_at] == expected
    assert np.all(read_scores(run_dir)["vendor_probability"].to_numpy() == 0.25)


def test_challenger_matrix(run_300, tmp_path, monkeypatch):
    import lightgbm

    from scorecheck.features import challenger_matrix
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    features = read_features(run_300.run_dir)
    shuffled = features.sample(frac=1.0, random_state=0)
    matrix = challenger_matrix(shuffled)
    assert list(matrix.columns) == list(MATRIX)
    ordered = features.sort_values("application_id", kind="mergesort").reset_index(drop=True)
    _assert_equal_frame(matrix, ordered.loc[:, list(MATRIX)].reset_index(drop=True))

    filled = features.copy()
    for name in EXTERNAL:
        filled[name] = 1.0
    _assert_equal_frame(challenger_matrix(filled), matrix)

    edited = features.copy()
    edited["age_years"] = edited["age_years"] + 1000
    edited["gender"] = np.where(edited["gender"] == "female", "male", "female")
    edited["education"] = np.where(edited["education"] == "college", "high_school", "college")
    edited["marital_status"] = np.where(edited["marital_status"] == "single", "married", "single")
    edited["region"] = np.where(edited["region"] == "NCR", "CAR", "NCR")
    _assert_equal_frame(challenger_matrix(edited), matrix)

    extra = features.copy()
    extra["ability"] = 1.0
    extra["willingness"] = 1.0
    extra["vendor_signal"] = 1.0
    extra["true_default"] = 1
    extra["private_factor"] = 1.0
    leaked = challenger_matrix(extra)
    for name in ("ability", "willingness", "vendor_signal", "true_default", "private_factor"):
        assert name not in leaked.columns
    _assert_equal_frame(leaked, matrix)

    labels = []
    real_dataset = lightgbm.Dataset

    def dataset(data, label=None, **kwargs):
        if label is not None:
            labels.append(np.asarray(label).copy())
        return real_dataset(data, label=label, **kwargs)

    monkeypatch.setattr(lightgbm, "Dataset", dataset)
    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    vendor_publish(run_dir)
    before = challenger_matrix(read_features(run_dir))
    publish(run_dir)
    first_label = labels[-1].copy()
    flipped = read_features(run_dir)
    flipped["default_label"] = 1 - flipped["default_label"]
    write_features(run_dir, flipped)
    vendor_publish(run_dir)
    publish(run_dir)
    assert list(challenger_matrix(read_features(run_dir)).columns) == list(before.columns)
    _assert_equal_frame(challenger_matrix(read_features(run_dir)), before)
    assert not np.array_equal(labels[-1], first_label)
    assert np.array_equal(
        labels[-1],
        read_features(run_dir).sort_values("application_id", kind="mergesort")["default_label"].to_numpy(),
    )


def test_publish_ignores_ground_truth(run_300, tmp_path):
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    vendor_publish(run_dir)
    (run_dir / "ground_truth.parquet").unlink()
    publish(run_dir)
    assert (scores_dir(run_dir) / "scores.parquet").is_file()
    assert (scores_dir(run_dir) / "bind.json").is_file()


def test_external_scores_stay_null(run_300, tmp_path):
    from scorecheck.features import challenger_matrix
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    before_columns = list(read_features(run_dir).columns)
    vendor_publish(run_dir)
    publish(run_dir)
    features = read_features(run_dir)
    assert list(features.columns) == before_columns
    for name in EXTERNAL:
        assert features[name].isna().all()
    matrix = challenger_matrix(features)
    for name in EXTERNAL + DEMOGRAPHICS:
        assert name not in matrix.columns
    for name in DEMOGRAPHICS:
        assert name in features.columns


def _assert_fit_contract(capture: LibraryCapture, start: dict[str, int], seeds: dict[str, int]) -> dict:
    train = capture.train[start["train"]:]
    xgb = capture.xgb[start["xgb"]:]
    hist = capture.hist[start["hist"]:]
    logistic = capture.logistic[start["logistic"]:]
    assert len(train) == 2
    assert len(xgb) == 2
    assert len(hist) == 2
    assert len(logistic) == 1
    assert len(capture.xgb_fit[start["xgb"]:]) == 2
    assert len(capture.hist_fit[start["hist"]:]) == 2
    plain, monotone = train
    assert set(plain[0]) == LIGHTGBM_KEYS
    assert set(monotone[0]) == LIGHTGBM_KEYS | {"monotone_constraints", "monotone_constraints_method"}
    for params, num_boost_round, kwargs in train:
        assert params["objective"] == "binary"
        assert params["deterministic"] is True
        assert params["force_row_wise"] is True
        assert params["device_type"] == "cpu"
        assert params["num_threads"] == 1 and type(params["num_threads"]) is int
        assert params["feature_fraction"] == 1
        assert params["bagging_fraction"] == 1
        assert params["bagging_freq"] == 0 and type(params["bagging_freq"]) is int
        assert params["num_leaves"] == 15 and type(params["num_leaves"]) is int
        assert params["learning_rate"] == 0.1
        assert params["verbose"] == -1 and type(params["verbose"]) is int
        for key in ("seed", "bagging_seed", "feature_fraction_seed", "data_random_seed"):
            assert params[key] == seeds["lightgbm"]
            assert type(params[key]) is int
        assert num_boost_round == 40 and type(num_boost_round) is int
        assert "early_stopping_rounds" not in kwargs
        assert "callbacks" not in kwargs
    assert "monotone_constraints" not in plain[0]
    assert "monotone_constraints_method" not in plain[0]
    assert monotone[0]["monotone_constraints"] == CONSTRAINTS
    assert all(type(value) is int for value in monotone[0]["monotone_constraints"])
    assert monotone[0]["monotone_constraints_method"] == "advanced"

    for kwargs, constrained in zip(xgb, (False, True)):
        assert set(kwargs) == XGB_KEYS
        assert kwargs["n_estimators"] == 40
        assert kwargs["learning_rate"] == 0.1
        assert kwargs["max_leaves"] == 15
        assert kwargs["grow_policy"] == "lossguide"
        assert kwargs["tree_method"] == "hist"
        assert kwargs["subsample"] == 1
        assert kwargs["colsample_bytree"] == 1
        assert kwargs["n_jobs"] == 1 and type(kwargs["n_jobs"]) is int
        assert kwargs["random_state"] == seeds["xgboost"] and type(kwargs["random_state"]) is int
        assert kwargs["objective"] == "binary:logistic"
        assert kwargs["verbosity"] == 0 and type(kwargs["verbosity"]) is int
        assert "early_stopping_rounds" not in kwargs
        if constrained:
            assert kwargs["monotone_constraints"] == CONSTRAINTS
            assert type(kwargs["monotone_constraints"]) is tuple
            assert all(type(value) is int for value in kwargs["monotone_constraints"])
        else:
            assert kwargs["monotone_constraints"] is None
    for fit_kwargs in capture.xgb_fit[start["xgb"]:]:
        assert "eval_set" not in fit_kwargs

    for kwargs, constrained in zip(hist, (False, True)):
        assert set(kwargs) == HIST_KEYS
        assert kwargs["loss"] == "log_loss"
        assert kwargs["learning_rate"] == 0.1
        assert kwargs["max_iter"] == 40
        assert kwargs["max_leaf_nodes"] == 15
        assert kwargs["min_samples_leaf"] == 20
        assert kwargs["l2_regularization"] == 0.0
        assert kwargs["max_features"] == 1.0
        assert kwargs["max_bins"] == 255
        assert kwargs["categorical_features"] is None
        assert kwargs["early_stopping"] is False
        assert kwargs["random_state"] == seeds["hist_gradient_boosting"]
        assert type(kwargs["random_state"]) is int
        assert kwargs["verbose"] == 0 and type(kwargs["verbose"]) is int
        if constrained:
            assert kwargs["monotonic_cst"] == CONSTRAINTS
            assert all(type(value) is int for value in kwargs["monotonic_cst"])
        else:
            assert kwargs["monotonic_cst"] is None
    assert logistic[0]["random_state"] == seeds["scorecard"]
    assert type(logistic[0]["random_state"]) is int
    return {"train": train, "xgb": xgb, "hist": hist, "logistic": logistic}


def test_library_contract(run_300, tmp_path, monkeypatch):
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for name, version in (("xgboost", "3.4.1"), ("scikit-learn", "1.9.1"), ("lightgbm", "4.7.0")):
        pin = f"{name}=={version}"
        assert pin in toml
        assert pin in requirements
        assert importlib.metadata.version(name) == version
    assert 'requires-python = ">=3.12"' in toml
    streams = Streams(config.SEED, "models")
    seeds = {
        name: int(streams(name).integers(0, 2**31))
        for name in ("lightgbm", "xgboost", "hist_gradient_boosting", "scorecard")
    }
    capture = _spy_libraries(monkeypatch)
    recorded = {}
    for households, source in ((300, run_300.run_dir), (200, None)):
        if households == 300:
            run_dir = copied_run(source, tmp_path / "hh300")
        else:
            run_dir = generate_run(config.SEED, households, tmp_path / "hh200").run_dir
        two_class(run_dir)
        vendor_publish(run_dir)
        start = {
            "train": len(capture.train),
            "xgb": len(capture.xgb),
            "hist": len(capture.hist),
            "logistic": len(capture.logistic),
        }
        publish(run_dir)
        recorded[households] = _assert_fit_contract(capture, start, seeds)
    assert recorded[200] == recorded[300]


def test_one_class_scores(run_300, tmp_path, monkeypatch, capsys):
    import lightgbm
    import sklearn.ensemble
    import sklearn.linear_model
    import xgboost

    from scorecheck.models import line, publish
    from scorecheck.vendor import publish as vendor_publish

    def refuse(*args, **kwargs):
        raise AssertionError("one-class publish called a trainer")

    monkeypatch.setattr(lightgbm, "train", refuse)
    monkeypatch.setattr(lightgbm, "Dataset", refuse)
    monkeypatch.setattr(xgboost, "XGBClassifier", refuse)
    monkeypatch.setattr(sklearn.ensemble, "HistGradientBoostingClassifier", refuse)
    monkeypatch.setattr(sklearn.linear_model, "LogisticRegression", refuse)
    monkeypatch.setattr("scorecheck.models.binned_weight_of_evidence", refuse)
    monkeypatch.setattr("scorecheck.models.points_to_double_the_odds", refuse)
    run_dir = copied_run(run_300.run_dir, tmp_path)
    for label, probability in ((0, 0.0), (1, 1.0)):
        one_class(run_dir, label)
        vendor_publish(run_dir)
        capsys.readouterr()
        publish(run_dir)
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == ""
        frame = read_scores(run_dir)
        for name in SCORE_COLUMNS[1:-1]:
            assert np.all(frame[name].to_numpy() == probability)
        assert frame["scorecard_points"].isna().all()
        application_id = int(frame["application_id"].iloc[0])
        assert line(run_dir, application_id).scorecard_points is None


def test_same_machine_scores_hash(run_300, tmp_path):
    from scorecheck.vendor import publish as vendor_publish

    one = copied_run(run_300.run_dir, tmp_path / "one")
    two = copied_run(run_300.run_dir, tmp_path / "two")
    one_class(one, 0)
    two_class(two)
    vendor_publish(one)
    vendor_publish(two)
    for run_dir in (one, two):
        _publish_subprocess(run_dir)
        first = scores_hash(read_scores(run_dir))
        _publish_subprocess(run_dir)
        second = scores_hash(read_scores(run_dir))
        assert first == second


def test_atomic_swap(run_300, tmp_path, monkeypatch):
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    one_class(run_dir, 0)
    vendor_publish(run_dir)
    scores = scores_dir(run_dir)
    calls = []
    real_replace = os.replace

    def spy(src, dst):
        source = Path(src)
        assert sorted(p.name for p in source.iterdir()) == ["bind.json", "scores.parquet"]
        calls.append((source, Path(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    publish(run_dir)
    assert len(calls) == 1
    assert calls[0][1] == scores
    assert not calls[0][0].exists()
    assert {p.name for p in scores.parent.iterdir()} == {scores.name}
    monkeypatch.undo()

    previous = {name: (scores / name).read_bytes() for name in ("scores.parquet", "bind.json")}
    one_class(run_dir, 1)
    vendor_publish(run_dir)

    def fail_stage(src, dst):
        if "staging" in Path(src).name and Path(dst) == scores:
            raise OSError("replace failed")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", fail_stage)
    with pytest.raises(OSError, match="replace failed"):
        publish(run_dir)
    assert {p.name for p in scores.parent.iterdir()} == {scores.name}
    for name, payload in previous.items():
        assert (scores / name).read_bytes() == payload


def test_large_book_skips_per_row_vendor_score(tmp_path, monkeypatch):
    from scorecheck import vendor
    from scorecheck.models import publish

    run_dir = generate_run(config.SEED, 301, tmp_path / "processed").run_dir
    two_class(run_dir)
    vendor.publish(run_dir)
    assert len(read_features(run_dir)) > 300

    def refuse(*args, **kwargs):
        raise AssertionError("large book called vendor.score")

    monkeypatch.setattr(vendor, "score", refuse)
    publish(run_dir)
    assert np.all(read_scores(run_dir)["vendor_probability"].to_numpy() == 0.5)


def test_scores_hash_uses_logical_hash(run_300, tmp_path):
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    one_class(run_dir, 0)
    vendor_publish(run_dir)
    publish(run_dir)
    frame = read_scores(run_dir)
    assert scores_hash(frame) == logical_hash.logical_hash(frame)
    assert frame["scorecard_points"].isna().all()
