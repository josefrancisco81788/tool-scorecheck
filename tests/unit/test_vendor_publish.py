import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scorecheck import config, rundir, schema
from scorecheck._streams import Streams
from support.runs import generate_run
from support.vendor import (
    FitCapture,
    copied_run,
    feature_hash,
    ledger_dir,
    ledger_hash,
    one_class,
    read_features,
    spy_lightgbm,
    two_class,
    write_features,
)

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_GROUPS = {
    "utilization": "credit_stress",
    "open_credit_count": "credit_stress",
    "delinquency_count_30": "credit_stress",
    "delinquency_count_60": "credit_stress",
    "delinquency_count_90": "credit_stress",
    "on_time_rate": "credit_stress",
    "income": "capacity",
    "dependents": "capacity",
    "credit_amount": "capacity",
    "installment_to_income": "capacity",
    "payment_to_obligation_ratio": "capacity",
    "history_months": "thin_file",
    "sim_count": "alt_activity",
    "prepaid_flag": "alt_activity",
    "electricity_late_rate": "alt_activity",
    "electricity_disconnect_count": "alt_activity",
    "remittance_inflow_mean": "alt_activity",
    "ewallet_net_flow_mean": "alt_activity",
    "shared_account_flag": "alt_activity",
    "private_factor": "private_factor",
}
DEMOGRAPHICS = ("age_years", "gender", "education", "marital_status", "region")
EXTERNAL = ("external_score_1", "external_score_2", "external_score_3")
LEAKED = ("ability", "willingness", "region_month_shock", "post_origination_shock", "true_default")
LIGHTGBM_KEYS = {
    "objective", "deterministic", "force_row_wise", "device_type", "num_threads", "feature_fraction",
    "bagging_fraction", "bagging_freq", "num_leaves", "learning_rate", "verbose", "seed", "bagging_seed",
    "feature_fraction_seed", "data_random_seed",
}


def _publish_subprocess(run_dir: Path) -> None:
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from scorecheck.vendor import publish\n"
        "publish(Path(sys.argv[1]))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(run_dir)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr


def _origination_signal(run_dir: Path) -> pd.Series:
    person = pd.read_parquet(run_dir / "person.parquet", columns=["person_id", "origination_month"])
    truth = pd.read_parquet(run_dir / "ground_truth.parquet", columns=["person_id", "month", "vendor_signal"])
    aligned = truth.merge(person, on="person_id")
    kept = aligned.loc[aligned["month"] == aligned["origination_month"]]
    return kept.set_index("person_id")["vendor_signal"]


def _column(capture: FitCapture, name: str) -> np.ndarray:
    return capture.matrix[:, capture.feature_name.index(name)]


def test_publish_is_silent(run_300, tmp_path, capsys):
    from scorecheck.vendor import publish

    one = copied_run(run_300.run_dir, tmp_path / "one")
    two = copied_run(run_300.run_dir, tmp_path / "two")
    one_class(one, 0)
    two_class(two)
    capsys.readouterr()
    publish(one)
    one_out = capsys.readouterr()
    publish(two)
    two_out = capsys.readouterr()
    assert one_out.out == "" and one_out.err == ""
    assert two_out.out == "" and two_out.err == ""


def test_ledger_path(tmp_path):
    from scorecheck.vendor import publish

    assert rundir.run_id(config.SEED, 200) == "6e6c82611fa89cf4"
    run = generate_run(config.SEED, 200, tmp_path / "processed")
    publish(run.run_dir)
    ledger = ledger_dir(run.run_dir)
    assert ledger == run.run_dir.parent.with_name("vendor") / run.run_dir.name
    assert ledger == tmp_path / "vendor" / "6e6c82611fa89cf4"
    assert sorted(p.name for p in ledger.iterdir()) == ["bind.json", "ledger.parquet"]
    payload = json.loads((ledger / "bind.json").read_text(encoding="utf-8"))
    assert list(payload) == ["features_hash"]
    assert payload["features_hash"] == feature_hash(run.run_dir)
    frame = pd.read_parquet(ledger / "ledger.parquet")
    assert list(frame.columns) == ["application_id", "probability", "reason_1", "reason_2", "reason_3"]
    assert frame["application_id"].dtype == np.int64
    assert frame["probability"].dtype == np.float64
    assert frame["application_id"].is_monotonic_increasing
    assert frame["application_id"].duplicated().sum() == 0
    assert np.isfinite(frame["probability"]).all()
    assert frame["probability"].between(0.0, 1.0).all()


def test_publish_leaves_run_dir_unchanged(run_300, tmp_path):
    from scorecheck.vendor import publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    before = {p.name for p in run_dir.iterdir()}
    publish(run_dir)
    after = {p.name for p in run_dir.iterdir()}
    assert after == before
    assert "ledger.parquet" not in after
    assert "bind.json" not in after


def test_external_scores_stay_null(run_300, tmp_path, monkeypatch):
    from scorecheck.vendor import publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    capture = spy_lightgbm(monkeypatch)
    publish(run_dir)
    features = read_features(run_dir)
    for name in EXTERNAL:
        assert features[name].isna().all()
        assert name not in capture.feature_name
    first = capture.matrix.copy()
    filled = features.copy()
    for name in EXTERNAL:
        filled[name] = 1.0
    write_features(run_dir, filled)
    publish(run_dir)
    assert np.array_equal(capture.matrix, first)


def test_origination_read(run_300, tmp_path, monkeypatch):
    from scorecheck.vendor import publish

    run_dir = copied_run(run_300.run_dir, tmp_path / "fit")
    two_class(run_dir)
    before_hash = feature_hash(run_dir)
    capture = spy_lightgbm(monkeypatch)
    publish(run_dir)
    assert feature_hash(run_dir) == before_hash
    ordered = read_features(run_dir).sort_values("application_id", kind="mergesort")
    expected = ordered["person_id"].map(_origination_signal(run_dir)).to_numpy(dtype=np.float64)
    assert np.array_equal(_column(capture, "private_factor"), expected)
    assert np.array_equal(capture.label, ordered["default_label"].to_numpy())
    features = read_features(run_dir)
    ledger = pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet")
    for name in ("vendor_signal", "private_factor"):
        assert name not in features.columns
        assert name not in ledger.columns
    assert "private_factor" in capture.feature_name
    for name in ("vendor_signal", *LEAKED):
        assert name not in capture.feature_name
        assert name not in features.columns
        assert name not in ledger.columns

    private = _column(capture, "private_factor").copy()
    label = capture.label.copy()
    person = pd.read_parquet(run_dir / "person.parquet", columns=["person_id", "origination_month"])
    truth = pd.read_parquet(run_dir / "ground_truth.parquet").merge(person, on="person_id")
    off = truth["month"] != truth["origination_month"]
    truth.loc[off, "vendor_signal"] = truth.loc[off, "vendor_signal"] + 1000.0
    truth.drop(columns=["origination_month"]).to_parquet(run_dir / "ground_truth.parquet", index=False)
    publish(run_dir)
    assert np.array_equal(_column(capture, "private_factor"), private)

    truth = pd.read_parquet(run_dir / "ground_truth.parquet").merge(person, on="person_id")
    on = truth["month"] == truth["origination_month"]
    truth.loc[on, "vendor_signal"] = truth.loc[on, "vendor_signal"] + 1000.0
    truth.drop(columns=["origination_month"]).to_parquet(run_dir / "ground_truth.parquet", index=False)
    publish(run_dir)
    assert np.array_equal(_column(capture, "private_factor"), private + 1000.0)
    after_signal = capture.matrix.copy()

    truth = pd.read_parquet(run_dir / "ground_truth.parquet")
    truth["ability"] = truth["ability"] + 1000.0
    truth["willingness"] = truth["willingness"] + 1000.0
    truth["region_month_shock"] = ~truth["region_month_shock"].astype(bool)
    truth["post_origination_shock"] = ~truth["post_origination_shock"].astype(bool)
    truth["true_default"] = 1 - truth["true_default"]
    truth.to_parquet(run_dir / "ground_truth.parquet", index=False)
    publish(run_dir)
    assert np.array_equal(capture.matrix, after_signal)
    assert np.array_equal(capture.label, label)

    flipped = read_features(run_dir)
    flipped["default_label"] = 1 - flipped["default_label"]
    write_features(run_dir, flipped)
    publish(run_dir)
    flipped_ordered = flipped.sort_values("application_id", kind="mergesort")
    assert np.array_equal(capture.label, flipped_ordered["default_label"].to_numpy())
    assert not np.array_equal(capture.label, label)

    bare = copied_run(run_300.run_dir, tmp_path / "bare")
    bare_hash = feature_hash(bare)
    bare_person = pd.read_parquet(bare / "person.parquet", columns=["person_id", "origination_month"])
    bare_victim = int(bare_person["person_id"].iloc[0])
    bare_month = int(bare_person.loc[bare_person["person_id"] == bare_victim, "origination_month"].iloc[0])
    bare_truth = pd.read_parquet(bare / "ground_truth.parquet")
    kept = ~((bare_truth["person_id"] == bare_victim) & (bare_truth["month"] == bare_month))
    bare_truth.loc[kept].to_parquet(bare / "ground_truth.parquet", index=False)
    assert not ledger_dir(bare).exists()
    with pytest.raises(schema.SchemaError):
        publish(bare)
    assert not ledger_dir(bare).exists()
    assert feature_hash(bare) == bare_hash


def test_demographics_leave_the_matrix(run_300, tmp_path, monkeypatch):
    from scorecheck.vendor import ReasonCode, publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    before_hash = feature_hash(run_dir)
    capture = spy_lightgbm(monkeypatch)
    publish(run_dir)
    features = read_features(run_dir)
    assert feature_hash(run_dir) == before_hash
    for name in DEMOGRAPHICS:
        assert name not in capture.feature_name
        assert name in features.columns
    assert "application_profile" not in capture.feature_name
    ledger = pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet")
    tokens = set(ledger["reason_1"]) | set(ledger["reason_2"]) | set(ledger["reason_3"])
    assert "application_profile" not in tokens
    with pytest.raises(ValueError):
        ReasonCode("application_profile")
    first = capture.matrix.copy()
    edited = features.copy()
    edited["age_years"] = edited["age_years"] + 1000
    edited["gender"] = np.where(edited["gender"] == "female", "male", "female")
    edited["education"] = np.where(edited["education"] == "college", "high_school", "college")
    edited["marital_status"] = np.where(edited["marital_status"] == "single", "married", "single")
    edited["region"] = np.where(edited["region"] == "NCR", "CAR", "NCR")
    write_features(run_dir, edited)
    publish(run_dir)
    assert np.array_equal(capture.matrix, first)


def test_group_map(run_300, tmp_path, monkeypatch):
    from scorecheck import vendor

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    assert vendor.COLUMN_GROUPS == EXPECTED_GROUPS
    capture = spy_lightgbm(monkeypatch)
    vendor.publish(run_dir)
    assert set(capture.feature_name) == set(vendor.COLUMN_GROUPS)
    bare = copied_run(run_300.run_dir, tmp_path / "bare")
    before_hash = feature_hash(bare)
    groups = dict(vendor.COLUMN_GROUPS)
    del groups["private_factor"]
    monkeypatch.setattr(vendor, "COLUMN_GROUPS", groups)
    assert not ledger_dir(bare).exists()
    with pytest.raises(schema.SchemaError):
        vendor.publish(bare)
    assert not ledger_dir(bare).exists()
    assert feature_hash(bare) == before_hash


def test_person_id_is_only_the_join_key(run_300, tmp_path, monkeypatch):
    from scorecheck.vendor import UnknownApplicant, publish, score

    run_dir = copied_run(run_300.run_dir, tmp_path)
    frame = read_features(run_dir)
    frame["application_id"] = frame["application_id"] + 1_000_000
    write_features(run_dir, frame)
    two_class(run_dir)
    capture = spy_lightgbm(monkeypatch)
    publish(run_dir)
    person_id = int(read_features(run_dir)["person_id"].iloc[0])
    rewritten = set(read_features(run_dir)["application_id"])
    assert person_id not in rewritten
    with pytest.raises(UnknownApplicant):
        score(run_dir, person_id)
    decision = score(run_dir, person_id + 1_000_000)
    ledger = pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet")
    row = ledger.loc[ledger["application_id"] == person_id + 1_000_000].iloc[0]
    assert decision.probability == float(row["probability"])
    assert (decision.reason_1, decision.reason_2, decision.reason_3) == (
        row["reason_1"], row["reason_2"], row["reason_3"],
    )
    before = _column(capture, "private_factor").copy()
    ordered = read_features(run_dir).sort_values("application_id", kind="mergesort")
    person = pd.read_parquet(run_dir / "person.parquet", columns=["person_id", "origination_month"])
    month = int(person.loc[person["person_id"] == person_id, "origination_month"].iloc[0])
    truth = pd.read_parquet(run_dir / "ground_truth.parquet")
    hit = (truth["person_id"] == person_id) & (truth["month"] == month)
    truth.loc[hit, "vendor_signal"] = truth.loc[hit, "vendor_signal"] + 1000.0
    truth.to_parquet(run_dir / "ground_truth.parquet", index=False)
    publish(run_dir)
    after = _column(capture, "private_factor")
    row_index = int(np.flatnonzero(ordered["person_id"].to_numpy() == person_id)[0])
    assert after[row_index] - before[row_index] == 1000.0
    others = np.delete(after - before, row_index)
    assert np.all(others == 0.0)


def test_one_class_ledger(run_300, tmp_path, monkeypatch, capsys):
    import lightgbm

    from scorecheck.vendor import publish, score

    def refuse(*args, **kwargs):
        raise AssertionError("one-class publish called lightgbm")

    monkeypatch.setattr(lightgbm, "train", refuse)
    monkeypatch.setattr(lightgbm, "Dataset", refuse)
    monkeypatch.setattr(lightgbm.Booster, "predict", refuse)
    run_dir = copied_run(run_300.run_dir, tmp_path)
    for label, probability in ((0, 0.0), (1, 1.0)):
        one_class(run_dir, label)
        capsys.readouterr()
        publish(run_dir)
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == ""
        ledger = pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet")
        assert np.all(ledger["probability"].to_numpy() == probability)
        assert (ledger["reason_1"] == "credit_stress").all()
        assert (ledger["reason_2"] == "capacity").all()
        assert (ledger["reason_3"] == "thin_file").all()
        application_id = int(ledger["application_id"].iloc[0])
        decision = score(run_dir, application_id)
        assert decision.probability == probability
        assert (decision.reason_1, decision.reason_2, decision.reason_3) == (
            "credit_stress", "capacity", "thin_file",
        )


def test_lightgbm_contract(run_300, tmp_path, monkeypatch):
    import importlib.metadata

    from scorecheck.vendor import publish

    assert "lightgbm==4.7.0" in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "lightgbm==4.7.0" in (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert importlib.metadata.version("lightgbm") == "4.7.0"
    expected_seed = int(Streams(config.SEED, "vendor")("lightgbm").integers(0, 2**31))
    capture = spy_lightgbm(monkeypatch)
    params = {}
    for households, source in ((300, None), (200, tmp_path / "hh200")):
        if households == 300:
            run_dir = copied_run(run_300.run_dir, tmp_path / "hh300")
        else:
            run_dir = generate_run(config.SEED, households, source).run_dir
        two_class(run_dir)
        calls = capture.train_calls
        publish(run_dir)
        assert capture.train_calls == calls + 1
        assert capture.dataset_calls >= 1
        assert set(capture.params) == LIGHTGBM_KEYS
        assert capture.params["objective"] == "binary"
        assert capture.params["deterministic"] is True
        assert capture.params["force_row_wise"] is True
        assert capture.params["device_type"] == "cpu"
        assert capture.params["num_threads"] == 1 and type(capture.params["num_threads"]) is int
        assert capture.params["feature_fraction"] == 1
        assert capture.params["bagging_fraction"] == 1
        assert capture.params["bagging_freq"] == 0 and type(capture.params["bagging_freq"]) is int
        assert capture.params["num_leaves"] == 15 and type(capture.params["num_leaves"]) is int
        assert capture.params["learning_rate"] == 0.1
        assert capture.params["verbose"] == -1 and type(capture.params["verbose"]) is int
        for key in ("seed", "bagging_seed", "feature_fraction_seed", "data_random_seed"):
            assert capture.params[key] == expected_seed
            assert type(capture.params[key]) is int
        assert capture.num_boost_round == 40 and type(capture.num_boost_round) is int
        assert "early_stopping_rounds" not in capture.train_kwargs
        assert "callbacks" not in capture.train_kwargs
        params[households] = dict(capture.params)
    assert params[200] == params[300]


def test_same_machine_ledger_hash(run_300, tmp_path):
    one = copied_run(run_300.run_dir, tmp_path / "one")
    two = copied_run(run_300.run_dir, tmp_path / "two")
    one_class(one, 0)
    two_class(two)
    for run_dir in (one, two):
        _publish_subprocess(run_dir)
        first = ledger_hash(pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet"))
        _publish_subprocess(run_dir)
        second = ledger_hash(pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet"))
        assert first == second


def test_reason_rank():
    from scorecheck.vendor import COLUMN_GROUPS, rank_reasons

    zeros = {name: 0.0 for name in COLUMN_GROUPS}
    assert rank_reasons(zeros) == ("credit_stress", "capacity", "thin_file")
    named = dict(zeros)
    named["income"] = 3
    named["history_months"] = 3
    named["private_factor"] = 2
    named["utilization"] = 1
    named["sim_count"] = 0.5
    assert rank_reasons(named) == ("capacity", "thin_file", "private_factor")
    missing = dict(zeros)
    del missing["income"]
    with pytest.raises(schema.SchemaError):
        rank_reasons(missing)


def test_atomic_swap(run_300, tmp_path, monkeypatch):
    import os

    from scorecheck.vendor import publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    one_class(run_dir, 0)
    ledger = ledger_dir(run_dir)
    calls = []
    real_replace = os.replace

    def spy(src, dst):
        source = Path(src)
        assert sorted(p.name for p in source.iterdir()) == ["bind.json", "ledger.parquet"]
        calls.append((source, Path(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    publish(run_dir)
    assert len(calls) == 1
    assert calls[0][1] == ledger
    assert not calls[0][0].exists()
    assert {p.name for p in ledger.parent.iterdir()} == {ledger.name}
    monkeypatch.undo()

    previous = {
        name: (ledger / name).read_bytes() for name in ("ledger.parquet", "bind.json")
    }
    one_class(run_dir, 1)

    def fail_stage(src, dst):
        if "staging" in Path(src).name and Path(dst) == ledger:
            raise OSError("replace failed")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", fail_stage)
    with pytest.raises(OSError, match="replace failed"):
        publish(run_dir)
    assert {p.name for p in ledger.parent.iterdir()} == {ledger.name}
    for name, payload in previous.items():
        assert (ledger / name).read_bytes() == payload
