"""Feature 002 rule V3 as narrowed in Feature 004: a batch read and regime refits inside vendor/."""

import numpy as np
import pandas as pd
import pytest

from scorecheck import logical_hash as logical_hash_module
from support.vendor import copied_run, read_features, two_class, write_features


@pytest.fixture(scope="module")
def run_40(tmp_path_factory):
    from scorecheck import config
    from support.runs import generate_run

    return generate_run(config.SEED, 40, tmp_path_factory.mktemp("run40"))


def _published(run_300, tmp_path):
    from scorecheck.vendor import publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    publish(run_dir)
    return run_dir


def test_read_published_equals_score_for_every_application(run_40, tmp_path):
    from scorecheck.vendor import regime, score

    run_dir = _published(run_40, tmp_path)
    assert len(read_features(run_dir)) <= 300
    ledger = regime.read_published(run_dir)
    assert list(ledger.columns) == ["application_id", "probability", "reason_1", "reason_2", "reason_3"]
    assert ledger["application_id"].is_monotonic_increasing
    assert len(ledger) == len(read_features(run_dir))
    for row in ledger.itertuples(index=False):
        decision = score(run_dir, int(row.application_id))
        assert decision.probability == row.probability
        assert (decision.reason_1.value, decision.reason_2.value, decision.reason_3.value) == (
            row.reason_1, row.reason_2, row.reason_3,
        )


def test_read_published_hashes_once(run_300, tmp_path, monkeypatch):
    from scorecheck.vendor import regime, score

    run_dir = _published(run_300, tmp_path)
    calls = []
    real = logical_hash_module.logical_bytes

    def counting(table):
        calls.append(1)
        return real(table)

    monkeypatch.setattr(logical_hash_module, "logical_bytes", counting)
    regime.read_published(run_dir)
    assert len(calls) == 1
    calls.clear()
    score(run_dir, int(read_features(run_dir)["application_id"].iloc[0]))
    score(run_dir, int(read_features(run_dir)["application_id"].iloc[1]))
    assert len(calls) == 2


def test_read_published_before_publish_and_when_stale(run_300, tmp_path):
    from scorecheck.vendor import LedgerMissing, StaleLedger, regime

    fresh = copied_run(run_300.run_dir, tmp_path / "fresh")
    with pytest.raises(LedgerMissing):
        regime.read_published(fresh)

    run_dir = _published(run_300, tmp_path / "stale")
    edited = read_features(run_dir)
    edited["income"] = edited["income"] + 1.0
    write_features(run_dir, edited)
    with pytest.raises(StaleLedger):
        regime.read_published(run_dir)


def test_rank_reasons_matrix_equals_rank_reasons():
    from scorecheck import vendor
    from scorecheck.vendor import regime

    names = list(vendor.COLUMN_GROUPS)
    rng = np.random.default_rng(11)
    contrib = rng.normal(size=(200, len(names)))
    contrib[::7] = 0.0                      # all-tied rows
    contrib[1::5, :10] = 0.0                # partly tied rows
    contrib[2::9] = np.round(contrib[2::9], 0)
    got = regime.rank_reasons_matrix(contrib, names)
    assert got.shape == (200, 3)
    for index in range(len(contrib)):
        expected = vendor.rank_reasons({name: contrib[index, j] for j, name in enumerate(names)})
        assert tuple(got[index]) == tuple(code.value for code in expected)


def test_refit_returns_none_when_the_labels_cannot_train(run_300, tmp_path):
    from scorecheck.vendor import regime

    run_dir = _published(run_300, tmp_path)
    refitter = regime.Refitter(run_dir)
    ids = refitter.application_id
    assert refitter.fit(np.array([], dtype=np.int64), np.array([], dtype=np.int64)) is None
    assert refitter.fit(ids[:50], np.zeros(50, dtype=np.int64)) is None
    assert refitter.fit(ids[:50], np.ones(50, dtype=np.int64)) is None


def test_refit_on_everything_reproduces_the_published_ledger(run_300, tmp_path):
    from scorecheck.vendor import regime

    run_dir = _published(run_300, tmp_path)
    published = regime.read_published(run_dir)
    refitter = regime.Refitter(run_dir)
    labels = read_features(run_dir).sort_values("application_id", kind="mergesort")["default_label"].to_numpy()
    got = refitter.fit(refitter.application_id, labels)
    pd.testing.assert_frame_equal(got, published)


def test_refit_on_a_subset_scores_the_whole_book(run_300, tmp_path):
    from scorecheck.vendor import regime

    run_dir = _published(run_300, tmp_path)
    refitter = regime.Refitter(run_dir)
    ids = refitter.application_id[::2]
    labels = (np.arange(len(ids)) % 2).astype(np.int64)
    got = refitter.fit(ids, labels)
    assert np.array_equal(got["application_id"].to_numpy(), refitter.application_id)
    assert got["probability"].between(0.0, 1.0).all()
    for column in ("reason_1", "reason_2", "reason_3"):
        assert set(got[column]) <= {"credit_stress", "capacity", "thin_file", "alt_activity", "private_factor"}
    assert (got[["reason_1", "reason_2", "reason_3"]].nunique(axis=1) >= 1).all()
    assert all(len({a, b, c}) == 3 for a, b, c in zip(got["reason_1"], got["reason_2"], got["reason_3"]))


def test_write_then_read_one_application(run_300, tmp_path):
    from scorecheck import vendor
    from scorecheck.vendor import regime

    run_dir = _published(run_300, tmp_path)
    ledger = regime.read_published(run_dir)
    refitter = regime.Refitter(run_dir)
    target = tmp_path / "regime"
    regime.write(target, ledger, refitter.features_hash, regime.fit_ids_hash(refitter.application_id))
    assert sorted(p.name for p in target.iterdir()) == ["bind.json", "ledger.parquet"]
    first = int(ledger["application_id"].iloc[0])
    decision = regime.read(run_dir, target, first)
    assert decision == vendor.score(run_dir, first)
    with pytest.raises(vendor.UnknownApplicant):
        regime.read(run_dir, target, -1)


def test_fit_ids_hash_fixture():
    from scorecheck.vendor import regime

    assert regime.fit_ids_hash([30, 10, 20]) == "761a58240947f3caf8c0af75e1e8cadf0496ed1c17cee2fdf7df3cbe2088c462"
    assert regime.fit_ids_hash([]) == "1bcaeedcda3bf388ccc9cef0cb4b5e38e19d3fb03a007a5a90bc05f149691df9"
    assert regime.fit_ids_hash([10, 20, 30]) == regime.fit_ids_hash([30, 10, 20])
