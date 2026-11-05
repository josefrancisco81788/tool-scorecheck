"""E1: two regimes, six quarterly checkpoints, no refit at month 4, frozen vendor_only challengers."""

import numpy as np

from support.experiment import CHECKPOINTS, LINES, REGIMES


def test_constants():
    from scorecheck import experiment

    assert experiment.REGIMES == REGIMES == ("vendor_only", "data_owner")
    assert experiment.CHECKPOINTS == CHECKPOINTS == (4, 8, 12, 16, 20, 24)
    assert experiment.BAD_WINDOW_MONTHS == 6
    assert experiment.APPROVAL_MAX_PROBABILITY == 0.0185
    assert experiment.TEST_CELL_SHARE == 0.05


def test_public_surface():
    from scorecheck import experiment

    assert experiment.__all__ == [
        "run", "approve", "gap", "Gap", "CHECKPOINTS", "REGIMES", "APPROVAL_MAX_PROBABILITY",
        "TEST_CELL_SHARE", "BAD_WINDOW_MONTHS", "HYPOTHESIS",
    ]


def test_curve_grid(experiment_2000):
    curves = experiment_2000.curves
    assert len(curves) == 2 * 6 * 7 == 84
    assert list(zip(curves["regime"], curves["checkpoint"], curves["line"])) == [
        (r, c, l) for r in REGIMES for c in CHECKPOINTS for l in LINES
    ]


def test_no_refit_at_month_4(experiment_2000):
    fits = experiment_2000.fits
    at_four = fits[fits["checkpoint"] == 4]
    assert not at_four.empty
    assert (~at_four["trained"]).all()
    assert (at_four["n"] == 0).all()
    outcomes = experiment_2000.outcomes
    month_four = outcomes[outcomes["checkpoint"] == 4]
    assert not month_four["label_observed"].any()
    assert month_four["matured_label"].isna().all()


def test_vendor_only_challengers_stay_as_first_fitted(experiment_2000):
    fits = experiment_2000.fits
    challenger = fits[fits["arm"] == "challenger"]
    only = challenger[challenger["regime"] == "vendor_only"]
    assert list(only["checkpoint"]) == [0]
    owner = challenger[challenger["regime"] == "data_owner"]
    assert owner["checkpoint"].tolist() == [0, 4, 8, 12, 16, 20, 24]
    assert owner["trained"].sum() >= 3

    heldout = experiment_2000.heldout
    frozen = heldout[heldout["regime"] == "vendor_only"]
    first = frozen[frozen["checkpoint"] == 4].set_index("application_id")
    for checkpoint in CHECKPOINTS[1:]:
        later = frozen[frozen["checkpoint"] == checkpoint].set_index("application_id")
        for line in LINES:
            assert np.array_equal(later.loc[first.index, line].to_numpy(), first[line].to_numpy())

    moving = heldout[heldout["regime"] == "data_owner"]
    final = moving[moving["checkpoint"] == 24].set_index("application_id")
    assert any(
        not np.array_equal(final.loc[first.index, line].to_numpy(), first[line].to_numpy()) for line in LINES
    )


def test_both_regimes_start_from_the_same_models(experiment_2000):
    heldout = experiment_2000.heldout
    one = heldout[(heldout["regime"] == "vendor_only") & (heldout["checkpoint"] == 4)].reset_index(drop=True)
    two = heldout[(heldout["regime"] == "data_owner") & (heldout["checkpoint"] == 4)].reset_index(drop=True)
    for column in ("application_id", "vendor_probability", *LINES):
        assert np.array_equal(one[column].to_numpy(), two[column].to_numpy())


def test_vendor_learns_in_both_regimes(experiment_2000):
    fits = experiment_2000.fits
    vendor = fits[fits["arm"] == "vendor"]
    for regime in REGIMES:
        rows = vendor[vendor["regime"] == regime]
        assert rows["checkpoint"].tolist() == [0, 4, 8, 12, 16, 20, 24]
        assert rows.loc[rows["checkpoint"] >= 12, "trained"].all()
    a = vendor[vendor["regime"] == "vendor_only"].drop(columns="regime").reset_index(drop=True)
    b = vendor[vendor["regime"] == "data_owner"].drop(columns="regime").reset_index(drop=True)
    assert a.equals(b)
