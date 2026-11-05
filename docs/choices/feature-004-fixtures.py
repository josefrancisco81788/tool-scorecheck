"""Recompute the numeric fixtures quoted in checks/draft/feature-004.md.

This is not product code. From the repo root:

    python checks/draft/feature-004-fixtures.py

Measured on 31 Oct 2026 with scikit-learn 1.9.1. The gap literals are the
values that command printed. A change in sklearn that moves a value by more
than 1e-12 fails this script.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from scorecheck.logical_hash import logical_hash

LABELS = np.array([0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1], dtype=np.int64)
VENDOR = np.array(
    [0.20, 0.30, 0.25, 0.40, 0.35, 0.45, 0.55, 0.50, 0.60, 0.48, 0.70, 0.42],
    dtype=np.float64,
)
CHALLENGER = np.array(
    [0.10, 0.15, 0.12, 0.18, 0.20, 0.22, 0.80, 0.85, 0.78, 0.90, 0.88, 0.83],
    dtype=np.float64,
)

# sklearn 1.9.1 on 31 Oct 2026. Absolute tolerance in the draft is 1e-12.
EXPECTED = {
    "vendor_auc": 0.9722222222222223,
    "vendor_log_loss": 0.5139083833436667,
    "vendor_brier": 0.16556666666666667,
    "challenger_auc": 1.0,
    "challenger_log_loss": 0.17661799762264355,
    "challenger_brier": 0.027658333333333337,
    "auc_gap": -0.02777777777777768,
    "log_loss_gap": 0.3372903857210232,
    "brier_gap": 0.13790833333333333,
    "fit_ids_hash": "761a58240947f3caf8c0af75e1e8cadf0496ed1c17cee2fdf7df3cbe2088c462",
    "empty_fit_ids_hash": "1bcaeedcda3bf388ccc9cef0cb4b5e38e19d3fb03a007a5a90bc05f149691df9",
}

ATOL = 1e-12


def fit_ids_hash(application_ids: list[int]) -> str:
    frame = pd.DataFrame({"application_id": np.asarray(application_ids, dtype=np.int64)})
    return logical_hash(frame)


def main() -> None:
    vendor_auc = float(roc_auc_score(LABELS, VENDOR))
    challenger_auc = float(roc_auc_score(LABELS, CHALLENGER))
    vendor_log_loss = float(log_loss(LABELS, VENDOR))
    challenger_log_loss = float(log_loss(LABELS, CHALLENGER))
    vendor_brier = float(brier_score_loss(LABELS, VENDOR))
    challenger_brier = float(brier_score_loss(LABELS, CHALLENGER))
    got = {
        "vendor_auc": vendor_auc,
        "vendor_log_loss": vendor_log_loss,
        "vendor_brier": vendor_brier,
        "challenger_auc": challenger_auc,
        "challenger_log_loss": challenger_log_loss,
        "challenger_brier": challenger_brier,
        "auc_gap": vendor_auc - challenger_auc,
        "log_loss_gap": vendor_log_loss - challenger_log_loss,
        "brier_gap": vendor_brier - challenger_brier,
        "fit_ids_hash": fit_ids_hash([30, 10, 20]),
        "empty_fit_ids_hash": fit_ids_hash([]),
    }
    failed = False
    for name, expected in EXPECTED.items():
        actual = got[name]
        if isinstance(expected, float):
            ok = abs(actual - expected) <= ATOL
        else:
            ok = actual == expected
        mark = "ok" if ok else "FAIL"
        print(f"{mark} {name} {actual!r}")
        failed = failed or not ok
    if got["auc_gap"] >= 0:
        print("FAIL auc_gap is not negative, so this fixture no longer contradicts the hypothesis")
        failed = True
    if failed:
        sys.exit(1)
    print("feature-004 fixtures match sklearn and logical_hash")


if __name__ == "__main__":
    main()
