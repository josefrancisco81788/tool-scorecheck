"""R6: bad rate and expected loss at an equal approval rate."""

import numpy as np
import pandas as pd
import pytest

from scorecheck.report import _constants as c
from scorecheck.report import _tables
from support.report import EIGHT, frame


def test_approval_is_exact_and_ties_break_by_application_id():
    score = np.array([0.5, 0.1, 0.1, 0.1, 0.9])
    ids = np.array([5, 4, 2, 3, 1])
    approved = _tables.approve_share(score, ids, 0.6)
    assert approved.sum() == 3
    assert list(np.flatnonzero(approved)) == [1, 2, 3]
    assert _tables.approve_share(score, ids, 0.4).tolist() == [False, False, True, True, False]


def test_expected_loss_is_bad_times_loan_times_sixty_percent():
    assert c.LOSS_GIVEN_DEFAULT == 0.60
    loss = _tables.expected_loss(EIGHT)
    assert loss.sum() == pytest.approx((2000 + 5000) * 0.6)


def test_hand_checked_equal_approval_rows():
    table = _tables.equal_approval({"data_owner": EIGHT})
    rows = table[table["approval_rate"] == 0.9].set_index("model")
    # Seven of eight approved. The vendor declines row 6, the scorecard declines row 5.
    assert rows.loc["vendor", "approved"] == 7
    assert rows.loc["vendor", "approved_bads"] == 2
    assert rows.loc["vendor", "expected_loss"] == pytest.approx(0.6 * (2000 + 5000))
    assert rows.loc["scorecard_probability", "approved_bads"] == 2
    assert rows.loc["scorecard_probability", "defaults_avoided_vs_vendor"] == 0


def test_a_worse_challenger_shows_added_defaults_and_higher_loss():
    worse = frame(vendor=[0.5, 0.1, 0.2, 0.3, 0.4], line=[0.1, 0.5, 0.2, 0.3, 0.4], bad=[1, 0, 0, 0, 0])
    table = _tables.equal_approval({"data_owner": worse})
    row = table[(table["approval_rate"] == 0.8) & (table["model"] == "scorecard_probability")].iloc[0]
    assert row["approved"] == 4
    assert row["defaults_avoided_vs_vendor"] == -1
    assert row["expected_loss_delta_vs_vendor"] == pytest.approx(600.0)
    assert row["bad_rate_delta_vs_vendor"] == pytest.approx(0.25)


def test_report_equal_approval_covers_vendor_and_every_line(report_2000, experiment_2000):
    table = pd.read_csv(report_2000 / "equal_approval.csv")
    assert set(table["approval_rate"]) == {0.7, 0.8, 0.9}
    assert set(table["model"]) == {"vendor", *c.LINES}
    held = experiment_2000.heldout
    n = len(held[(held["regime"] == "data_owner") & (held["checkpoint"] == 24)])
    for rate, rows in table.groupby("approval_rate"):
        assert (rows["approved"] == round(rate * n)).all()
    vendor = table[table["model"] == "vendor"]
    assert (vendor["defaults_avoided_vs_vendor"] == 0).all()
    assert (vendor["expected_loss_delta_vs_vendor"] == 0).all()
