"""Assertions shared by the unit suite and the advisory eval suite."""

import hashlib
import math

import numpy as np
import pandas as pd

from support.runs import PanelRun

DISCONNECTED = {"disconnected_restored_30d", "unpaid_past_30d"}
STATES = {"on_time", "late_before_disconnection", "disconnected_restored_30d", "unpaid_past_30d"}


def spearman(x, y) -> float:
    rx = pd.Series(np.asarray(x, dtype=float)).rank(method="average")
    ry = pd.Series(np.asarray(y, dtype=float)).rank(method="average")
    return float(rx.corr(ry))


def rank_residual(y, xs) -> np.ndarray:
    ranked_y = pd.Series(np.asarray(y, dtype=float)).rank(method="average").to_numpy()
    design = np.column_stack(
        [np.ones(len(ranked_y))]
        + [pd.Series(np.asarray(x, dtype=float)).rank(method="average").to_numpy() for x in xs]
    )
    coef, *_ = np.linalg.lstsq(design, ranked_y, rcond=None)
    return np.round(ranked_y - design @ coef, 6)


def assert_finite_and(value: float, sign: str) -> None:
    assert math.isfinite(value), value
    assert (value < 0) if sign == "<" else (value > 0), value


def assert_residual_correlates(y, xs, label, sign: str) -> None:
    residual = rank_residual(y, xs)
    assert len(set((residual + 0.0).tolist())) >= 2
    assert_finite_and(spearman(residual, label), sign)


def override_values(prefix: str, ground_truth: pd.DataFrame) -> list[float]:
    rows = ground_truth.sort_values(["person_id", "month"])
    return [
        (int.from_bytes(hashlib.sha256(f"{prefix}|{p}|{m}".encode("utf-8")).digest()[:4], "big") / 2**32) * 6 - 3
        for p, m in zip(rows["person_id"].tolist(), rows["month"].tolist())
    ]


def assert_prepaid_share(run: PanelRun) -> None:
    assert abs(run["sim"]["prepaid"].mean() - 0.96) <= 0.02


def assert_sims_per_person(run: PanelRun) -> None:
    sim = run["sim"]
    assert 1.3 <= len(sim) / len(run["person"]) <= 2.5
    assert sim["person_id"].value_counts().max() >= 2


def assert_electricity_state_shares(run: PanelRun) -> None:
    states = run["month_behaviour"]["electricity_state"]
    assert abs(states.isin(DISCONNECTED).mean() - 0.05) <= 0.03
    assert (states == "on_time").mean() > 0.5
    assert set(states.unique()) == STATES


def assert_shared_account_counts(run: PanelRun) -> None:
    for table in ("electricity_account", "ewallet_account"):
        shared = run[table]["shared"]
        assert shared.sum() >= 20, table
        assert (~shared).sum() >= 20, table


def assert_driver_signs(run: PanelRun) -> None:
    rows = run.origination_rows
    assert_finite_and(spearman(rows["ability"], rows["true_default"]), "<")
    assert_finite_and(spearman(rows["willingness"], rows["true_default"]), "<")


def assert_default_class_counts(run: PanelRun) -> None:
    labels = run.origination_rows["true_default"]
    assert (labels == 1).sum() >= 30
    assert (labels == 0).sum() >= 30


def assert_ability_rank_residual(run: PanelRun) -> None:
    rows = run.origination_rows
    assert_residual_correlates(rows["ability"], [rows["willingness"]], rows["true_default"], "<")


def assert_willingness_rank_residual(run: PanelRun) -> None:
    rows = run.origination_rows
    assert_residual_correlates(rows["willingness"], [rows["ability"]], rows["true_default"], "<")


def assert_vendor_signal_rank_residual(run: PanelRun) -> None:
    rows = run.origination_rows
    assert_residual_correlates(
        rows["vendor_signal"], [rows["ability"], rows["willingness"]], rows["true_default"], ">"
    )


def assert_calendar_split(run: PanelRun) -> None:
    receivers = run["person"].merge(run["household"][["household_id", "remittance_receiver"]], on="household_id")
    receiver_by_person = receivers.set_index("person_id")["remittance_receiver"]

    def calendar_means(table: str, column: str, receiver: bool) -> tuple[float, float]:
        frame = run[table]
        frame = frame[frame["person_id"].map(receiver_by_person) == receiver]
        calendar = (frame["month"] - 1) % 12 + 1
        december = float(frame.loc[calendar == 12, column].mean())
        april = float(frame.loc[calendar == 4, column].mean())
        assert math.isfinite(december) and math.isfinite(april), (table, column, receiver)
        return december, april

    ability_dec, ability_apr = calendar_means("ground_truth", "ability", True)
    will_dec, will_apr = calendar_means("ground_truth", "willingness", True)
    inflow_dec, inflow_apr = calendar_means("month_behaviour", "wallet_inflow", True)
    other_dec, other_apr = calendar_means("month_behaviour", "wallet_inflow", False)

    ability_gap = ability_dec - ability_apr
    assert ability_gap > 0
    assert ability_gap > will_dec - will_apr
    assert inflow_dec - inflow_apr > other_dec - other_apr
    assert inflow_dec > inflow_apr
