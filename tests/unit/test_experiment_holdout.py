"""E4 and E5: the holdout never trains a model, and every point is measured on the same target."""

import numpy as np

from support.experiment import CHECKPOINTS, LINES, REGIMES, bad_6m


def test_holdout_is_one_in_five(experiment_2000):
    out = experiment_2000.outcomes
    assert (out["holdout"] == (out["application_id"] % 5 == 0)).all()
    assert out["holdout"].any()


def test_no_holdout_in_any_fit(experiment_2000):
    out = experiment_2000.outcomes
    assert not out.loc[out["holdout"], "label_observed"].any()
    assert not out.loc[out["holdout"], "test_cell"].any()
    assert len(experiment_2000.fit_calls) > 0
    for _, ids, _ in experiment_2000.fit_calls:
        assert (ids % 5 != 0).all()


def test_every_point_is_scored_on_the_whole_holdout(experiment_2000):
    heldout = experiment_2000.heldout
    truth = bad_6m(experiment_2000.run_dir)
    ids = experiment_2000.features["application_id"]
    holdout_ids = np.sort(ids[ids % 5 == 0].to_numpy())
    assert len(holdout_ids) > 100
    for regime in REGIMES:
        for checkpoint in CHECKPOINTS:
            part = heldout[(heldout["regime"] == regime) & (heldout["checkpoint"] == checkpoint)]
            assert np.array_equal(np.sort(part["application_id"].to_numpy()), holdout_ids)
            assert np.array_equal(
                part["bad_6m"].astype(int).to_numpy(), truth.loc[part["application_id"]].astype(int).to_numpy()
            )
            for column in ("vendor_probability", *LINES):
                assert part[column].between(0.0, 1.0).all()
    out = experiment_2000.outcomes
    declined = out[(out["checkpoint"] == 24) & out["holdout"] & out["on_book"] & ~out["approved"]]
    assert len(declined) > 0
    assert declined["application_id"].isin(heldout["application_id"]).all()


def test_holdout_counts_never_move(experiment_2000):
    curves = experiment_2000.curves
    assert curves["holdout_n"].nunique() == 1
    assert curves["holdout_bads"].nunique() == 1
    truth = bad_6m(experiment_2000.run_dir)
    ids = experiment_2000.features["application_id"]
    ids = ids[ids % 5 == 0]
    assert curves["holdout_n"].iloc[0] == len(ids)
    assert curves["holdout_bads"].iloc[0] == int(truth.loc[ids].sum())
