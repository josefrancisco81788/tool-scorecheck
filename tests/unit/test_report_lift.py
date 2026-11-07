"""R2: ranking lift of the vendor over each challenger, by segment and by file depth."""

import math

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from scorecheck.report import _constants as c
from scorecheck.report import _tables


def test_lift_matches_sklearn_and_interval_contains_it():
    rng = np.random.default_rng(3)
    labels = (rng.random(400) < 0.2).astype(int)
    vendor = labels * 0.6 + rng.random(400)
    line = labels * 0.3 + rng.random(400)
    v_auc, l_auc, gap, low, high = _tables.lift(labels, vendor, line)
    assert v_auc == pytest.approx(roc_auc_score(labels, vendor), abs=1e-12)
    assert l_auc == pytest.approx(roc_auc_score(labels, line), abs=1e-12)
    assert gap == pytest.approx(v_auc - l_auc, abs=1e-12)
    assert low < gap < high


def test_one_class_group_has_no_lift():
    out = _tables.lift([0, 0, 0], [0.1, 0.2, 0.3], [0.3, 0.2, 0.1])
    assert all(math.isnan(x) for x in out)
    assert _tables.verdict(math.nan, math.nan) == "not measurable"


def test_verdict_words():
    assert _tables.verdict(0.01, 0.05) == "vendor leads"
    assert _tables.verdict(-0.01, 0.05) == "caught up"
    assert _tables.verdict(0.0, 0.05) == "caught up"
    assert _tables.verdict(-0.05, -0.01) == "challenger ahead"
    assert _tables.verdict(-0.05, 0.0) == "caught up"


def test_negative_lift_is_kept_as_it_came_out():
    rng = np.random.default_rng(4)
    labels = (rng.random(600) < 0.3).astype(int)
    vendor = rng.random(600)
    line = labels * 0.8 + rng.random(600)
    _, _, gap, low, high = _tables.lift(labels, vendor, line)
    assert gap < 0 and _tables.verdict(low, high) == "challenger ahead"


def test_groups_add_up_to_the_holdout(report_2000):
    lift = pd.read_csv(report_2000 / "lift_by_group.csv")
    one = lift[(lift["regime"] == "data_owner") & (lift["line"] == c.NAMED_LINE)]
    total = one[one["segment"] == "all"].iloc[0]
    for segment in c.SEGMENTS:
        rows = one[one["segment"] == segment]
        assert rows["n"].sum() == total["n"], segment
        assert rows["bads"].sum() == total["bads"], segment


def test_every_group_has_all_seven_lines(report_2000):
    lift = pd.read_csv(report_2000 / "lift_by_group.csv")
    sizes = lift.groupby(["regime", "segment", "group"]).size()
    assert (sizes == 7).all()
    assert set(lift["line"]) == set(c.LINES) and len(c.LINES) == 7
    assert set(lift[lift["named_challenger"]]["line"]) == {c.NAMED_LINE}


def test_sparse_flag_below_fifty_bad(report_2000):
    lift = pd.read_csv(report_2000 / "lift_by_group.csv")
    assert ((lift["bads"] < 50) == lift["sparse"]).all()
    assert lift["sparse"].any() and (~lift["sparse"]).any()


def test_verdict_follows_the_interval(report_2000):
    lift = pd.read_csv(report_2000 / "lift_by_group.csv").dropna(subset=["auc_lift_low"])
    expected = np.where(
        lift["auc_lift_low"] > 0, "vendor leads", np.where(lift["auc_lift_high"] < 0, "challenger ahead", "caught up")
    )
    assert (lift["verdict"].to_numpy() == expected).all()


def test_thin_cut_is_six_months_or_less(report_2000, experiment_2000):
    assert c.THIN_MAX_MONTHS == 6
    lift = pd.read_csv(report_2000 / "lift_by_group.csv")
    held = experiment_2000.heldout
    ids = held[(held["regime"] == "data_owner") & (held["checkpoint"] == 24)]["application_id"]
    features = experiment_2000.features.set_index("application_id").loc[ids]
    thin = int((features["history_months"] <= 6).sum())
    row = lift[(lift["regime"] == "data_owner") & (lift["segment"] == "history") & (lift["line"] == c.NAMED_LINE)]
    assert int(row[row["group"] == "thin"]["n"].iloc[0]) == thin
    assert int(row[row["group"] == "thick"]["n"].iloc[0]) == len(ids) - thin


def test_age_bands_cover_ages_eighteen_up():
    ages = pd.DataFrame({"age_years": [18, 24, 25, 34, 35, 44, 45, 54, 55, 70], "history_months": [1] * 10})
    out = _tables.add_groups(ages)
    assert list(out["age_band"]) == [
        "18-24", "18-24", "25-34", "25-34", "35-44", "35-44", "45-54", "45-54", "55+", "55+",
    ]
