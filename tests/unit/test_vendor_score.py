import shutil

import pandas as pd
import pytest

from scorecheck import config
from support.runs import generate_run
from support.vendor import copied_run, ledger_dir, one_class, read_features, two_class, write_features

TOKENS = {"credit_stress", "capacity", "thin_file", "alt_activity", "private_factor"}


def test_score_returns_decision(run_300, tmp_path, monkeypatch):
    import lightgbm

    from scorecheck.vendor import ReasonCode, VendorDecision, publish, rank_reasons, score
    from support.vendor import spy_lightgbm

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    capture = spy_lightgbm(monkeypatch)

    publish(run_dir)
    assert capture.contrib is not None
    assert capture.contrib.shape[1] == len(capture.feature_name) + 1
    ordered = read_features(run_dir).sort_values("application_id", kind="mergesort")
    ledger = pd.read_parquet(ledger_dir(run_dir) / "ledger.parquet")
    for index, application_id in enumerate(ordered["application_id"].tolist()):
        decision = score(run_dir, int(application_id))
        assert isinstance(decision, VendorDecision)
        probability, reason_1, reason_2, reason_3 = decision
        assert isinstance(probability, float)
        assert 0.0 <= probability <= 1.0
        codes = (reason_1, reason_2, reason_3)
        assert all(isinstance(code, ReasonCode) for code in codes)
        assert len(set(codes)) == 3
        assert {code.value for code in codes} <= TOKENS
        row = ledger.loc[ledger["application_id"] == application_id].iloc[0]
        assert probability == float(row["probability"])
        assert codes == (row["reason_1"], row["reason_2"], row["reason_3"])
        mapping = {
            name: float(capture.contrib[index, column])
            for column, name in enumerate(capture.feature_name)
        }
        assert codes == rank_reasons(mapping)

    def refuse(*args, **kwargs):
        raise AssertionError("score called lightgbm")

    monkeypatch.setattr(lightgbm, "train", refuse)
    monkeypatch.setattr(lightgbm.Booster, "predict", refuse)
    again = score(run_dir, int(ordered["application_id"].iloc[0]))
    assert isinstance(again, VendorDecision)


def test_ledger_errors(run_300, tmp_path):
    from scorecheck.vendor import LedgerMissing, StaleLedger, UnknownApplicant, publish, score

    run_dir = copied_run(run_300.run_dir, tmp_path)
    ledger = ledger_dir(run_dir)
    assert not ledger.exists()
    with pytest.raises(LedgerMissing):
        score(run_dir, 1)
    assert not ledger.exists()

    one_class(run_dir, 0)
    publish(run_dir)
    parquet = ledger / "ledger.parquet"
    bind = ledger / "bind.json"
    parquet_bytes = parquet.read_bytes()
    bind_bytes = bind.read_bytes()
    parquet.unlink()
    with pytest.raises(LedgerMissing):
        score(run_dir, 1)
    parquet.write_bytes(parquet_bytes)
    bind.unlink()
    with pytest.raises(LedgerMissing):
        score(run_dir, 1)
    bind.write_bytes(bind_bytes)

    application_id = int(read_features(run_dir)["application_id"].max()) + 1
    with pytest.raises(UnknownApplicant):
        score(run_dir, application_id)
    assert parquet.is_file() and bind.is_file()

    frame = read_features(run_dir)
    frame["income"] = frame["income"] + 1.0
    write_features(run_dir, frame)
    with pytest.raises(StaleLedger):
        score(run_dir, int(frame["application_id"].iloc[0]))

    errors = (LedgerMissing, StaleLedger, UnknownApplicant)
    for error in errors:
        assert issubclass(error, Exception)
    for left in errors:
        for right in errors:
            if left is not right:
                assert not issubclass(left, right)


def test_replaced_run_is_not_served(run_300, tmp_path):
    from scorecheck.vendor import StaleLedger, publish, score

    run_dir = copied_run(run_300.run_dir, tmp_path / "served")
    one_class(run_dir, 0)
    publish(run_dir)
    application_id = int(read_features(run_dir)["application_id"].iloc[0])
    assert score(run_dir, application_id).probability == 0.0

    frame = read_features(run_dir)
    frame["income"] = frame["income"] + 1.0
    write_features(run_dir, frame)
    with pytest.raises(StaleLedger):
        score(run_dir, application_id)

    one_class(run_dir, 1)
    publish(run_dir)
    assert score(run_dir, application_id).probability == 1.0

    other = generate_run(config.SEED + 1, 300, tmp_path / "other")
    shutil.copytree(other.run_dir, run_dir, dirs_exist_ok=True)
    with pytest.raises(StaleLedger):
        score(run_dir, application_id)
