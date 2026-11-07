"""Pure table builders for the champion and challenger decision report."""

import math

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from scorecheck.experiment import _metrics
from scorecheck.report import _constants as c


def wilson(bads: int, n: int) -> tuple[float, float]:
    """Wilson 95% interval for a proportion. NaN pair when n is 0."""
    if n == 0:
        return math.nan, math.nan
    p = bads / n
    z2 = c.Z_95 ** 2
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = c.Z_95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def expected_loss(frame: pd.DataFrame) -> np.ndarray:
    """Per applicant: bad outcome x loan amount x loss-given-default."""
    return (
        frame["bad_6m"].to_numpy(dtype=np.float64)
        * frame["credit_amount"].to_numpy(dtype=np.float64)
        * c.LOSS_GIVEN_DEFAULT
    )


def approve_share(score, application_id, rate: float) -> np.ndarray:
    """Approve exactly round(rate x n) applicants: the lowest scores, ties broken by application_id."""
    score = np.asarray(score, dtype=np.float64)
    order = np.lexsort((np.asarray(application_id), score))
    approved = np.zeros(len(score), dtype=bool)
    approved[order[: int(round(rate * len(score)))]] = True
    return approved


def add_groups(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["age_band"] = pd.cut(out["age_years"], bins=list(c.AGE_BINS), labels=list(c.AGE_LABELS)).astype(str)
    out["history"] = np.where(out["history_months"] <= c.THIN_MAX_MONTHS, "thin", "thick")
    return out


def verdict(low: float, high: float) -> str:
    if math.isnan(low) or math.isnan(high):
        return "not measurable"
    if low > 0:
        return "vendor leads"
    if high < 0:
        return "challenger ahead"
    return "caught up"


def lift(labels, vendor, line) -> tuple[float, float, float, float, float]:
    """Vendor AUC, challenger AUC, vendor minus challenger, and the paired DeLong 95% interval."""
    labels = np.asarray(labels).astype(np.int64)
    if not _metrics.is_two_class(labels):
        return (math.nan,) * 5
    vendor_auc = float(roc_auc_score(labels, vendor))
    line_auc = float(roc_auc_score(labels, line))
    half = c.Z_95 * math.sqrt(_metrics.delong_gap_variance(labels, vendor, line))
    gap = vendor_auc - line_auc
    return vendor_auc, line_auc, gap, gap - half, gap + half


def _group_items(frame: pd.DataFrame):
    yield "all", "all", frame
    for segment in c.SEGMENTS:
        for group, rows in frame.groupby(segment, sort=True):
            yield segment, str(group), rows


def lift_by_group(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    for regime, frame in frames.items():
        for segment, group, rows in _group_items(frame):
            bads = int(rows["bad_6m"].sum())
            for line in c.LINES:
                v_auc, l_auc, gap, low, high = lift(rows["bad_6m"], rows["vendor_probability"], rows[line])
                records.append({
                    "regime": regime, "segment": segment, "group": group, "line": line,
                    "named_challenger": line == c.NAMED_LINE, "n": len(rows), "bads": bads,
                    "sparse": bads < c.SPARSE_BADS, "vendor_auc": v_auc, "challenger_auc": l_auc,
                    "auc_lift": gap, "auc_lift_low": low, "auc_lift_high": high, "verdict": verdict(low, high),
                })
    return pd.DataFrame(records)


def _switch_flags(n: int, draw: np.ndarray, share: float) -> np.ndarray:
    """Nested deterministic subsets: the lowest round(share x n) draws go to the challenger."""
    flags = np.zeros(n, dtype=bool)
    flags[np.argsort(draw, kind="mergesort")[: int(round(share * n))]] = True
    return flags


def _reading(approval_delta: float, loss_delta: float) -> str:
    more = "approves more" if approval_delta > 1e-12 else "approves fewer" if approval_delta < -1e-12 else "same approval"
    cost = "loses more" if loss_delta > 1e-9 else "loses less" if loss_delta < -1e-9 else "same loss"
    return f"{more}, {cost}"


def phased_switch(frames: dict[str, pd.DataFrame], draw: np.ndarray) -> pd.DataFrame:
    records = []
    for regime, frame in frames.items():
        n = len(frame)
        loss = expected_loss(frame)
        amount = frame["credit_amount"].to_numpy(dtype=np.float64)
        bad = frame["bad_6m"].to_numpy()
        vendor = frame["vendor_probability"].to_numpy(dtype=np.float64)
        line = frame[c.NAMED_LINE].to_numpy(dtype=np.float64)
        for cutoff in c.SWITCH_CUTOFFS:
            vendor_ok = vendor < cutoff
            v_rate, v_loss = vendor_ok.mean(), loss[vendor_ok].sum()
            for share in c.SWITCH_SHARES:
                flags = _switch_flags(n, draw, share)
                approved = np.where(flags, line < cutoff, vendor_ok)
                rate, total = approved.mean(), loss[approved].sum()
                records.append({
                    "regime": regime, "line": c.NAMED_LINE, "cutoff": cutoff, "switch_share": share,
                    "applicants": n, "decided_by_challenger": int(flags.sum()), "approved": int(approved.sum()),
                    "approval_rate": rate, "vendor_approval_rate": v_rate, "approval_rate_delta": rate - v_rate,
                    "approved_bads": int(bad[approved].sum()),
                    "expected_loss": total, "vendor_expected_loss": v_loss, "expected_loss_delta": total - v_loss,
                    "expected_loss_pct_change": (total - v_loss) / v_loss if v_loss else math.nan,
                    "loss_per_applicant": total / n,
                    "loss_share_of_approved_value": total / amount[approved].sum(),
                    "reading": _reading(rate - v_rate, total - v_loss),
                })
    return pd.DataFrame(records)


def _swap_rows(regime: str, line: str, frame: pd.DataFrame) -> list[dict]:
    ids = frame["application_id"].to_numpy()
    by_vendor = approve_share(frame["vendor_probability"], ids, c.SWAP_APPROVAL_RATE)
    by_line = approve_share(frame[line], ids, c.SWAP_APPROVAL_RATE)
    loss = expected_loss(frame)
    bad = frame["bad_6m"].to_numpy()
    sets = (
        ("swap_in", by_line & ~by_vendor, "challenger approves, vendor declines"),
        ("swap_out", by_vendor & ~by_line, "vendor approves, challenger declines"),
        ("both_approve", by_line & by_vendor, "both approve"),
        ("both_decline", ~by_line & ~by_vendor, "both decline"),
    )
    rows = []
    for name, mask, meaning in sets:
        n, bads = int(mask.sum()), int(bad[mask].sum())
        low, high = wilson(bads, n)
        rows.append({
            "regime": regime, "line": line, "source": "holdout_outcomes", "group": name, "meaning": meaning,
            "approval_rate": c.SWAP_APPROVAL_RATE, "n": n, "bads": bads,
            "bad_rate": bads / n if n else math.nan, "bad_rate_low": low, "bad_rate_high": high,
            "expected_loss": float(loss[mask].sum()),
        })
    return rows


def _test_cell_row(regime: str, outcomes: pd.DataFrame) -> dict:
    cell = outcomes[outcomes["test_cell"]]
    observed = cell[cell["label_observed"]]
    n, bads = len(observed), int(observed["matured_label"].astype("int64").sum())
    low, high = wilson(bads, n)
    return {
        "regime": regime, "line": "", "source": "test_cell_outcomes", "group": "test_cell",
        "meaning": (
            f"vendor-declined applicants approved at random (Feature 004); {len(cell)} in the cell, {n} with a "
            "matured 6-month outcome. A cross-check on the declined population, not a score of the same people"
        ),
        "approval_rate": math.nan, "n": n, "bads": bads, "bad_rate": bads / n if n else math.nan,
        "bad_rate_low": low, "bad_rate_high": high, "expected_loss": math.nan,
    }


def swap_sets(frames: dict[str, pd.DataFrame], outcomes: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for regime, frame in frames.items():
        rows.extend(_swap_rows(regime, c.NAMED_LINE, frame))
        rows.append(_test_cell_row(regime, outcomes[regime]))
    return pd.DataFrame(rows)


def equal_approval(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    for regime, frame in frames.items():
        ids = frame["application_id"].to_numpy()
        loss = expected_loss(frame)
        bad = frame["bad_6m"].to_numpy()
        amount = frame["credit_amount"].to_numpy(dtype=np.float64)
        for rate in c.EQUAL_APPROVAL_RATES:
            results = {}
            for model, column in (("vendor", "vendor_probability"), *((line, line) for line in c.LINES)):
                approved = approve_share(frame[column], ids, rate)
                results[model] = (approved, int(bad[approved].sum()), float(loss[approved].sum()))
            _, v_bads, v_loss = results["vendor"]
            for model, (approved, bads, total) in results.items():
                n_approved = int(approved.sum())
                records.append({
                    "regime": regime, "approval_rate": rate, "model": model, "approved": n_approved,
                    "approved_bads": bads, "bad_rate": bads / n_approved, "expected_loss": total,
                    "loss_share_of_approved_value": total / amount[approved].sum(),
                    "defaults_avoided_vs_vendor": v_bads - bads,
                    "bad_rate_delta_vs_vendor": (bads - v_bads) / n_approved,
                    "expected_loss_delta_vs_vendor": total - v_loss,
                    "expected_loss_pct_change_vs_vendor": (total - v_loss) / v_loss if v_loss else math.nan,
                })
    return pd.DataFrame(records)


def full_lines(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    for regime, frame in frames.items():
        ids = frame["application_id"].to_numpy()
        loss = expected_loss(frame)
        bad = frame["bad_6m"].to_numpy()
        by_vendor = approve_share(frame["vendor_probability"], ids, c.SWAP_APPROVAL_RATE)
        for line in c.LINES:
            v_auc, l_auc, gap, low, high = lift(bad, frame["vendor_probability"], frame[line])
            by_line = approve_share(frame[line], ids, c.SWAP_APPROVAL_RATE)
            swap_in, swap_out = by_line & ~by_vendor, by_vendor & ~by_line
            records.append({
                "regime": regime, "line": line, "named_challenger": line == c.NAMED_LINE,
                "vendor_auc": v_auc, "challenger_auc": l_auc, "auc_lift": gap, "auc_lift_low": low,
                "auc_lift_high": high, "verdict": verdict(low, high), "approval_rate": c.SWAP_APPROVAL_RATE,
                "vendor_bad_rate": bad[by_vendor].mean(), "challenger_bad_rate": bad[by_line].mean(),
                "defaults_avoided_vs_vendor": int(bad[by_vendor].sum() - bad[by_line].sum()),
                "expected_loss_delta_vs_vendor": float(loss[by_line].sum() - loss[by_vendor].sum()),
                "swap_in_n": int(swap_in.sum()),
                "swap_in_bad_rate": bad[swap_in].mean() if swap_in.any() else math.nan,
                "swap_out_n": int(swap_out.sum()),
                "swap_out_bad_rate": bad[swap_out].mean() if swap_out.any() else math.nan,
            })
    return pd.DataFrame(records)
