"""Golden: headline numbers of the report on the 2,000-household book (seed 20261024).

A change to `tests/fixtures/golden/report_2000.json` needs a line in `tests/fixtures/golden/CHANGELOG.md`.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "report_2000.json"


def snapshot(report_dir: Path) -> dict:
    """Counts exactly and rates to six places, for the data_owner regime."""
    def read(name):
        frame = pd.read_csv(report_dir / name)
        return frame[frame["regime"] == "data_owner"]

    lift = read("lift_by_group.csv")
    lift = lift[lift["named_challenger"] & lift["segment"].isin(["all", "history"])]
    equal = read("equal_approval.csv")
    equal = equal[(equal["approval_rate"] == 0.8) & equal["model"].isin(["vendor", "scorecard_probability"])]
    switch = read("phased_switch.csv")
    switch = switch[(switch["cutoff"] == 0.1) & switch["switch_share"].isin([0.5, 1.0])]
    swap = read("swap_sets.csv")
    return {
        "lift": lift[["segment", "group", "n", "bads", "vendor_auc", "challenger_auc", "auc_lift", "verdict"]]
        .to_dict("records"),
        "equal_approval_80": equal[["model", "approved", "approved_bads", "expected_loss"]].to_dict("records"),
        "phased_switch_cutoff_0.10": switch[
            ["switch_share", "approved", "approved_bads", "expected_loss", "expected_loss_delta"]
        ].to_dict("records"),
        "swap_sets": swap[["group", "n", "bads"]].to_dict("records"),
    }


def _close(actual, expected, path=""):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path
        for key in expected:
            _close(actual[key], expected[key], f"{path}/{key}")
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path
        for i, (a, e) in enumerate(zip(actual, expected)):
            _close(a, e, f"{path}[{i}]")
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, abs=1e-6, rel=1e-6), path
    else:
        assert actual == expected, path


def test_report_matches_golden(report_2000):
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(snapshot(report_2000), default=lambda v: v.item()))
    _close(actual, expected)
