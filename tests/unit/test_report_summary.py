"""R7: the summary states what the data is, and keeps a negative result as it came out."""

import re

import pandas as pd

from scorecheck.report import _summary

NAMES = ("lift_by_group.csv", "phased_switch.csv", "swap_sets.csv", "equal_approval.csv", "full_lines.csv")
AHEAD = "- Challenger ahead (interval entirely below zero): "


def test_summary_states_assumptions_and_makes_no_real_vendor_claim(report_2000):
    text = (report_2000 / "summary.md").read_text(encoding="utf-8")
    assert "simulated vendor" in text and "synthetic" in text
    assert "60%" in text and "assumption" in text
    assert "test cell" in text and "not a score of the same people" in text
    assert not re.search(r"\bbeat", text, re.IGNORECASE)
    assert "makes no claim that the in-house model is better than any real vendor" in text
    assert len(text.splitlines()) < 90


def test_negative_lift_is_reported_unchanged(report_2000):
    tables = {name: pd.read_csv(report_2000 / name) for name in NAMES}
    lift = tables["lift_by_group.csv"]
    head = (lift["regime"] == "data_owner") & lift["named_challenger"]
    columns = ["auc_lift", "auc_lift_low", "auc_lift_high", "verdict"]
    lift.loc[head & (lift["segment"] == "all"), columns] = [-0.0204, -0.03, -0.01, "challenger ahead"]
    lift.loc[head & (lift["group"] == "thin"), columns] = [-0.02, -0.03, -0.01, "challenger ahead"]
    text = _summary.build(tables, pd.DataFrame({"bad_6m": [0, 1, 0, 1]}))
    assert "-0.020" in text
    assert AHEAD in text
    assert "history thin" in text.split(AHEAD)[1].split("\n")[0]
