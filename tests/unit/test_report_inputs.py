"""R1: the report reads the held-out scores and the outcomes table, and nothing from the vendor."""

import re
from pathlib import Path

import pandas as pd

import scorecheck
from scorecheck import report

SRC = Path(scorecheck.__file__).parent / "report"
ALLOWED = {
    "heldout_scores.parquet", "outcomes.parquet", "application_features.parquet", "person.parquet",
    "household.parquet",
}


def test_report_opens_only_the_named_files(experiment_2000, monkeypatch):
    opened: list[str] = []
    real = pd.read_parquet

    def spy(path, *args, **kwargs):
        opened.append(Path(path).name)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_parquet", spy)
    report.run(experiment_2000.run_dir)
    assert set(opened) == ALLOWED
    assert "scores.parquet" not in opened and "ledger.parquet" not in opened


def test_report_source_never_reaches_into_the_vendor():
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"scorecheck\.vendor|import vendor|from scorecheck import .*\bvendor\b", text), path
        assert "_private" not in text, path
        assert "ledger.parquet" not in text, path
        assert "models.line" not in text, path
        assert "scores_dir" not in text, path
        assert "scores.parquet" not in text.replace("heldout_scores.parquet", ""), path


def test_report_uses_only_checkpoint_24_and_both_regimes(report_2000, experiment_2000):
    lift = pd.read_csv(report_2000 / "lift_by_group.csv")
    assert set(lift["regime"]) == {"data_owner", "vendor_only"}
    held = experiment_2000.heldout
    last = held[(held["regime"] == "data_owner") & (held["checkpoint"] == 24)]
    overall = lift[(lift["regime"] == "data_owner") & (lift["segment"] == "all")]
    assert (overall["n"] == len(last)).all()
    assert (overall["bads"] == int(last["bad_6m"].sum())).all()
