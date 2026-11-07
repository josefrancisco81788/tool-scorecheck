"""R3: a phased switch against the vendor alone, on a hand-checked fixture."""

import numpy as np
import pandas as pd
import pytest

from scorecheck.report import _constants as c
from scorecheck.report import _tables
from support.report import EIGHT

DRAW = np.arange(8) / 8.0


def _row(table, cutoff, share):
    rows = table[(table["cutoff"] == cutoff) & (table["switch_share"] == share)]
    assert len(rows) == 1
    return rows.iloc[0]


def test_hand_checked_rows():
    table = _tables.phased_switch({"data_owner": EIGHT}, DRAW)
    # Cutoff 0.075. The vendor approves rows 0, 1, 3, 5, 7: one bad (row 1, loan 2000), loss 1200.
    full = _row(table, 0.075, 1.0)
    assert full["vendor_approval_rate"] == pytest.approx(5 / 8)
    assert full["vendor_expected_loss"] == pytest.approx(1200.0)
    # The challenger approves rows 0, 2, 3, 6, 7: no bad.
    assert full["approval_rate"] == pytest.approx(5 / 8)
    assert full["approval_rate_delta"] == pytest.approx(0.0)
    assert full["expected_loss"] == pytest.approx(0.0)
    assert full["expected_loss_delta"] == pytest.approx(-1200.0)
    assert full["reading"] == "same approval, loses less"
    # A quarter: rows 0 and 1 go to the challenger. Row 0 approved, row 1 declined, the rest as the vendor.
    quarter = _row(table, 0.075, 0.25)
    assert quarter["decided_by_challenger"] == 2
    assert quarter["approved"] == 4
    assert quarter["approval_rate_delta"] == pytest.approx(-1 / 8)
    assert quarter["expected_loss_delta"] == pytest.approx(-1200.0)
    assert quarter["reading"] == "approves fewer, loses less"


def test_switch_at_zero_is_the_vendor_alone_and_at_one_the_challenger_alone():
    draw = np.random.default_rng(1).random(8)
    assert not _tables._switch_flags(8, draw, 0.0).any()
    assert _tables._switch_flags(8, draw, 1.0).all()
    table = _tables.phased_switch({"data_owner": EIGHT}, draw)
    for cutoff in c.SWITCH_CUTOFFS:
        full = _row(table, cutoff, 1.0)
        line = EIGHT[c.NAMED_LINE].to_numpy() < cutoff
        loss = EIGHT["bad_6m"].to_numpy() * EIGHT["credit_amount"].to_numpy() * c.LOSS_GIVEN_DEFAULT
        assert full["approved"] == line.sum()
        assert full["expected_loss"] == pytest.approx(loss[line].sum())


def test_switch_subsets_are_nested_and_deterministic():
    draw = np.random.default_rng(2).random(100)
    previous = np.zeros(100, dtype=bool)
    for share in c.SWITCH_SHARES:
        flags = _tables._switch_flags(100, draw, share)
        assert flags.sum() == round(share * 100)
        assert (flags | previous).sum() == flags.sum()
        previous = flags
    assert np.array_equal(_tables._switch_flags(100, draw, 0.5), _tables._switch_flags(100, draw, 0.5))


def test_cutoffs_and_shares_are_the_product_answers():
    assert c.SWITCH_SHARES == (0.25, 0.50, 0.75, 1.00)
    assert c.SWITCH_CUTOFFS == (0.075, 0.10, 0.117)


def test_report_table_shape(report_2000):
    table = pd.read_csv(report_2000 / "phased_switch.csv")
    assert len(table) == 2 * 3 * 4
    assert set(table["cutoff"]) == {0.075, 0.1, 0.117}
    assert (table["decided_by_challenger"] <= table["applicants"]).all()
