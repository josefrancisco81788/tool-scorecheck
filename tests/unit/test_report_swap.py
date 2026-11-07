"""R4 and R5: swap sets at an 80% approval rate and the test-cell cross-check."""

import math

import pandas as pd
import pytest

from scorecheck.report import _tables
from support.report import EIGHT


def _wilson(bads, n):
    p, z = bads / n, 1.96
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def _cell(test_cell, observed, matured):
    return pd.DataFrame({
        "test_cell": test_cell, "label_observed": observed,
        "matured_label": pd.array(matured, dtype="Int64"),
    })


CELL = _cell([True, True, True, False], [True, True, False, True], [1, 0, None, 1])


def test_hand_checked_swap_sets():
    table = _tables.swap_sets({"data_owner": EIGHT}, {"data_owner": CELL})
    rows = table.set_index("group")
    # The vendor approves rows 0, 1, 2, 3, 5, 7. The scorecard approves rows 0, 1, 2, 3, 6, 7.
    assert (rows.loc["swap_in", "n"], rows.loc["swap_in", "bads"]) == (1, 0)
    assert (rows.loc["swap_out", "n"], rows.loc["swap_out", "bads"]) == (1, 0)
    assert (rows.loc["both_approve", "n"], rows.loc["both_approve", "bads"]) == (5, 1)
    assert (rows.loc["both_decline", "n"], rows.loc["both_decline", "bads"]) == (1, 1)
    assert rows.loc["swap_in", "n"] == rows.loc["swap_out", "n"]
    assert rows["n"].drop("test_cell").sum() == len(EIGHT)
    assert rows.loc["both_approve", "bad_rate"] == pytest.approx(0.2)


def test_test_cell_row_counts_only_matured_outcomes_and_has_a_wilson_interval():
    row = _tables.swap_sets({"data_owner": EIGHT}, {"data_owner": CELL}).set_index("group").loc["test_cell"]
    assert (row["n"], row["bads"]) == (2, 1)
    low, high = _wilson(1, 2)
    assert row["bad_rate"] == pytest.approx(0.5)
    assert row["bad_rate_low"] == pytest.approx(low) and row["bad_rate_high"] == pytest.approx(high)
    assert "cross-check" in row["meaning"] and "not a score" in row["meaning"]


def test_wilson_edges():
    assert all(math.isnan(x) for x in _tables.wilson(0, 0))
    low, high = _tables.wilson(0, 10)
    assert low == 0.0 and 0 < high < 0.35


def test_report_swap_sets_are_equal_in_size_and_include_the_test_cell(report_2000):
    table = pd.read_csv(report_2000 / "swap_sets.csv")
    for regime, rows in table.groupby("regime"):
        rows = rows.set_index("group")
        assert rows.loc["swap_in", "n"] == rows.loc["swap_out", "n"]
        assert set(rows.index) == {"swap_in", "swap_out", "both_approve", "both_decline", "test_cell"}
        assert (rows.loc["swap_in", "approval_rate"], rows.loc["swap_in", "line"]) == (0.8, "scorecard_probability")
        assert rows.loc["test_cell", "source"] == "test_cell_outcomes"
