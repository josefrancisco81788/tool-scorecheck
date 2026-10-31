"""Application-time features built from a panel run."""

from pathlib import Path

import pandas as pd

from scorecheck import panel, rundir
from scorecheck._streams import Streams
from scorecheck.features import _application

__all__ = ["from_panel", "challenger_matrix"]

# The only columns a challenger fit receives, in this order. Demographics and external scores stay
# on application_features and are absent here.
MATRIX_COLUMNS: tuple[str, ...] = (
    "utilization",
    "open_credit_count",
    "delinquency_count_30",
    "delinquency_count_60",
    "delinquency_count_90",
    "on_time_rate",
    "income",
    "dependents",
    "credit_amount",
    "installment_to_income",
    "payment_to_obligation_ratio",
    "history_months",
    "sim_count",
    "prepaid_flag",
    "electricity_late_rate",
    "electricity_disconnect_count",
    "remittance_inflow_mean",
    "ewallet_net_flow_mean",
    "shared_account_flag",
)

MONOTONE_COLUMNS: frozenset[str] = frozenset({
    "utilization",
    "delinquency_count_30",
    "delinquency_count_60",
    "delinquency_count_90",
    "installment_to_income",
})


def from_panel(run_dir: Path | str) -> pd.DataFrame:
    """Build application_features for a run, write it beside the panel, and return the written frame."""
    view = panel.read_at_origination(run_dir)
    frame = _application.build(view, Streams(view.seed, "application"))
    return rundir.write_application_features(Path(run_dir), frame)


def challenger_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the challenger columns, one row per application, sorted by application_id.

    Does not write a file and does not read ground truth. The training label is ``default_label``
    on this same row order, taken by the caller, not a column of this frame.
    """
    ordered = frame.sort_values("application_id", kind="mergesort")
    return ordered.loc[:, list(MATRIX_COLUMNS)].reset_index(drop=True)
