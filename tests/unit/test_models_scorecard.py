import numpy as np

from support.vendor import copied_run, two_class

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
VALUES = np.arange(10, dtype=np.float64)
LEVEL_LABELS = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1], dtype=np.int64)
MERGE_LABELS = np.array([0, 1, 1, 0, 0, 0, 1, 1, 1, 1], dtype=np.int64)


def _formula(probability: float) -> float:
    factor = 20 / np.log(2)
    offset = 600 - factor * np.log(50)
    clipped = min(max(probability, 1e-6), 1.0 - 1e-6)
    odds = (1.0 - clipped) / clipped
    return float(offset + factor * np.log(odds))


def test_weight_of_evidence_fixtures():
    from scorecheck.models import binned_weight_of_evidence

    level = np.array([np.log(3)] * 5 + [-np.log(3)] * 5)
    for monotone in (False, True):
        got = binned_weight_of_evidence(VALUES, LEVEL_LABELS, monotone)
        np.testing.assert_allclose(got, level, atol=1e-12, rtol=0)

    plain = np.array([np.log(11 / 3), np.log(11 / 27), np.log(11 / 27), np.log(11 / 3), np.log(11 / 3),
                      np.log(11 / 3), np.log(11 / 27), np.log(11 / 27), np.log(11 / 27), np.log(11 / 27)])
    got = binned_weight_of_evidence(VALUES, MERGE_LABELS, False)
    np.testing.assert_allclose(got, plain, atol=1e-12, rtol=0)

    merged = np.array([np.log(27 / 7)] + [np.log(9 / 5)] * 5 + [np.log(3 / 7)] * 4)
    got = binned_weight_of_evidence(VALUES, MERGE_LABELS, True)
    np.testing.assert_allclose(got, merged, atol=1e-12, rtol=0)
    constant = np.zeros(4, dtype=np.float64)
    constant_labels = np.array([0, 0, 1, 1], dtype=np.int64)
    for monotone in (False, True):
        got = binned_weight_of_evidence(constant, constant_labels, monotone)
        np.testing.assert_allclose(got, np.zeros(4), atol=1e-12, rtol=0)
    assert "binned_weight_of_evidence" not in __import__("scorecheck").models.__all__


def test_scorecard_fit(run_300, tmp_path, monkeypatch):
    import sklearn.linear_model

    from scorecheck.models import binned_weight_of_evidence, points_to_double_the_odds, publish
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    labelled = two_class(run_dir)
    vendor_publish(run_dir)
    seen = []
    real_woe = binned_weight_of_evidence

    def wrapped(values, labels, monotone):
        out = real_woe(values, labels, monotone)
        seen.append((bool(monotone), np.asarray(out, dtype=np.float64).copy(), np.asarray(labels).copy()))
        return out

    recorded = {}
    real_logistic = sklearn.linear_model.LogisticRegression

    def logistic(*args, **kwargs):
        recorded["kwargs"] = dict(kwargs)
        model = real_logistic(*args, **kwargs)
        real_fit = model.fit

        def fit(x, y, *fit_args, **fit_kwargs):
            recorded["x"] = np.asarray(x, dtype=np.float64).copy()
            recorded["y"] = np.asarray(y).copy()
            return real_fit(x, y, *fit_args, **fit_kwargs)

        model.fit = fit
        return model

    monkeypatch.setattr("scorecheck.models.binned_weight_of_evidence", wrapped)
    monkeypatch.setattr(sklearn.linear_model, "LogisticRegression", logistic)
    publish(run_dir)

    assert len(seen) == len(MATRIX)
    for name, (monotone, _weights, labels) in zip(MATRIX, seen):
        assert monotone is (name in MONOTONE)
        assert np.array_equal(labels, labelled.sort_values("application_id", kind="mergesort")["default_label"].to_numpy())
    stacked = np.column_stack([weights for _monotone, weights, _labels in seen])
    np.testing.assert_allclose(recorded["x"], stacked, atol=1e-12, rtol=0)
    assert np.array_equal(
        recorded["y"],
        labelled.sort_values("application_id", kind="mergesort")["default_label"].to_numpy(),
    )
    assert set(recorded["kwargs"]) == {"C", "solver", "max_iter", "random_state"}
    assert recorded["kwargs"]["C"] == 1.0
    assert recorded["kwargs"]["solver"] == "lbfgs"
    assert recorded["kwargs"]["max_iter"] == 500

    assert abs(points_to_double_the_odds(0.2) - _formula(0.2)) <= 1e-9
    assert abs(points_to_double_the_odds(0.2) - points_to_double_the_odds(1 / 3) - 20) <= 1e-9
    assert "points_to_double_the_odds" not in __import__("scorecheck").models.__all__

    from support.models import read_scores

    frame = read_scores(run_dir)
    for probability, points in zip(frame["scorecard_probability"], frame["scorecard_points"]):
        assert abs(float(points) - points_to_double_the_odds(float(probability))) <= 1e-9
