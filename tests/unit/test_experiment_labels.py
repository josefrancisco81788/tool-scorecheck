"""E3: a model only learns from approved, matured, non-holdout outcomes."""

import numpy as np

from support.experiment import bad_6m


def test_label_observed_is_exactly_the_matured_approved_non_holdout_set(experiment_2000):
    out = experiment_2000.outcomes
    expected = out["approved"] & ~out["holdout"] & (out["origination_month"] + 6 <= out["checkpoint"])
    assert out["label_observed"].equals(expected)
    assert out["label_observed"].any()
    declined = out[~out["approved"]]
    assert not declined["label_observed"].any()
    assert declined["matured_label"].isna().all()


def test_matured_label_is_the_six_month_bad(experiment_2000):
    out = experiment_2000.outcomes
    truth = bad_6m(experiment_2000.run_dir)
    seen = out[out["label_observed"]]
    assert seen["matured_label"].notna().all()
    assert np.array_equal(
        seen["matured_label"].astype(int).to_numpy(), truth.loc[seen["application_id"]].astype(int).to_numpy()
    )
    assert out.loc[~out["label_observed"], "matured_label"].isna().all()
    assert seen["matured_label"].sum() > 0


def test_fit_inputs_are_the_observed_labels(experiment_2000):
    out = experiment_2000.outcomes
    truth = bad_6m(experiment_2000.run_dir)
    non_holdout = int((experiment_2000.features["application_id"] % 5 != 0).sum())
    observed = [
        np.sort(rows["application_id"].to_numpy())
        for _, rows in out[out["label_observed"]].groupby(["regime", "checkpoint"])
    ]
    checked = 0
    for arm, ids, labels in experiment_2000.fit_calls:
        if len(ids) == non_holdout:
            continue  # a starting fit on the origination default label
        assert len(ids) == len(labels)
        assert any(np.array_equal(np.sort(ids), rows) for rows in observed)
        assert np.array_equal(labels.astype(int), truth.loc[ids].astype(int).to_numpy())
        checked += 1
    assert checked >= 6


def test_matured_means_open_six_months(experiment_2000):
    out = experiment_2000.outcomes
    seen = out[out["label_observed"]]
    assert (seen["origination_month"] + 6 <= seen["checkpoint"]).all()
    young = out[out["origination_month"] + 6 > out["checkpoint"]]
    assert not young["label_observed"].any()
