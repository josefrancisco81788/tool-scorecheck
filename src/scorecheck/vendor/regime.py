"""Batch ledger reader and regime vendor refits for the Feature 004 experiment.

Everything returned here is a probability plus three reason codes per application, the same
surface as ``vendor.score``. The booster, its training matrix, and ``private_factor`` stay inside
this package.
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from scorecheck import vendor
from scorecheck.logical_hash import logical_hash
from scorecheck.vendor import _private

LEDGER_COLUMNS = ("application_id", "probability", "reason_1", "reason_2", "reason_3")
_TIE_ORDER = ("credit_stress", "capacity", "thin_file", "alt_activity", "private_factor")


def read_published(run_dir: Path | str) -> pd.DataFrame:
    """The whole Feature 002 ledger in one read, after one check of its feature hash."""
    run_dir = Path(run_dir)
    directory = _private.ledger_dir(run_dir)
    ledger_file = directory / "ledger.parquet"
    bind_file = directory / "bind.json"
    if not ledger_file.is_file() or not bind_file.is_file():
        raise vendor.LedgerMissing(directory)
    bound = json.loads(bind_file.read_text(encoding="utf-8"))["features_hash"]
    if bound != _private.features_hash(run_dir):
        raise vendor.StaleLedger(run_dir)
    ledger = pd.read_parquet(ledger_file, columns=list(LEDGER_COLUMNS))
    return ledger.sort_values("application_id", kind="mergesort").reset_index(drop=True)


class Refitter:
    """Refit the vendor on chosen applications and labels, and score the whole book.

    The training columns, booster arguments, and seed are Feature 002's. Only the rows and the
    label change.
    """

    def __init__(self, run_dir: Path | str) -> None:
        self._table = _private.assemble(Path(run_dir), vendor.COLUMN_GROUPS)
        self.application_id = self._table.application_id.copy()
        self.features_hash = self._table.features_hash
        self._position = pd.Series(np.arange(len(self.application_id)), index=self.application_id)

    def fit(self, fit_ids, labels) -> pd.DataFrame | None:
        """Return a ledger frame for every application, or None when the labels cannot train.

        ``labels`` is aligned with ``fit_ids``. An empty or one-class fit returns None so the
        caller keeps the previous model's scores.
        """
        fit_ids = np.asarray(fit_ids, dtype=np.int64)
        labels = np.asarray(labels, dtype=np.int64)
        if len(fit_ids) != len(labels):
            raise ValueError("fit_ids and labels differ in length")
        if len(fit_ids) == 0 or np.unique(labels).size < 2:
            return None
        rows = self._position.loc[fit_ids].to_numpy()
        matrix = self._table.matrix.iloc[rows].reset_index(drop=True)
        booster = _private.train(matrix, labels, self._table.seed)
        data = self._table.matrix.to_numpy(dtype=np.float64)
        probability = np.clip(booster.predict(data), 0.0, 1.0).astype(np.float64)
        contrib = np.asarray(booster.predict(data, pred_contrib=True), dtype=np.float64)[:, :-1]
        reasons = rank_reasons_matrix(contrib, list(self._table.matrix.columns))
        return _ledger_frame(self.application_id, probability, reasons)


def rank_reasons_matrix(contrib: np.ndarray, names: list[str]) -> np.ndarray:
    """``vendor.rank_reasons`` for every row at once. Returns an (n, 3) array of token strings."""
    weights = np.zeros((contrib.shape[0], len(_TIE_ORDER)), dtype=np.float64)
    for j, name in enumerate(names):
        weights[:, _TIE_ORDER.index(vendor.COLUMN_GROUPS[name])] += np.abs(contrib[:, j])
    order = np.argsort(-weights, axis=1, kind="stable")[:, :3]
    return np.asarray(_TIE_ORDER, dtype=object)[order]


def _ledger_frame(application_id, probability, reasons) -> pd.DataFrame:
    return pd.DataFrame({
        "application_id": np.asarray(application_id, dtype=np.int64),
        "probability": np.asarray(probability, dtype=np.float64),
        "reason_1": reasons[:, 0].astype(str),
        "reason_2": reasons[:, 1].astype(str),
        "reason_3": reasons[:, 2].astype(str),
    })


def fit_ids_hash(application_ids) -> str:
    frame = pd.DataFrame({"application_id": np.asarray(application_ids, dtype=np.int64)})
    return logical_hash(frame)


def write(regime_dir: Path | str, ledger: pd.DataFrame, features_hash: str, fit_hash: str) -> None:
    """Write a regime ledger and its bind into ``regime_dir``. Replaces only those two files."""
    regime_dir = Path(regime_dir)
    regime_dir.mkdir(parents=True, exist_ok=True)
    frame = ledger.loc[:, list(LEDGER_COLUMNS)].sort_values("application_id", kind="mergesort")
    tmp = regime_dir / f".ledger.parquet.tmp-{os.getpid()}"
    frame.reset_index(drop=True).to_parquet(tmp, index=False)
    os.replace(tmp, regime_dir / "ledger.parquet")
    bind = {"features_hash": features_hash, "fit_ids_hash": fit_hash}
    (regime_dir / "bind.json").write_text(json.dumps(bind), encoding="utf-8")


def read(run_dir: Path | str, regime_dir: Path | str, application_id: int) -> vendor.VendorDecision:
    """One application's regime score and three reason codes."""
    regime_dir = Path(regime_dir)
    ledger_file = regime_dir / "ledger.parquet"
    bind_file = regime_dir / "bind.json"
    if not ledger_file.is_file() or not bind_file.is_file():
        raise vendor.LedgerMissing(regime_dir)
    bound = json.loads(bind_file.read_text(encoding="utf-8"))["features_hash"]
    if bound != _private.features_hash(Path(run_dir)):
        raise vendor.StaleLedger(run_dir)
    ledger = pd.read_parquet(ledger_file)
    hit = ledger.loc[ledger["application_id"] == application_id]
    if hit.empty:
        raise vendor.UnknownApplicant(application_id)
    row = hit.iloc[0]
    return vendor.VendorDecision(
        float(row["probability"]),
        vendor.ReasonCode(str(row["reason_1"])),
        vendor.ReasonCode(str(row["reason_2"])),
        vendor.ReasonCode(str(row["reason_3"])),
    )
