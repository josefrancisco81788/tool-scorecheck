"""Challenger refits for the Feature 004 experiment.

``refit`` fits the seven challenger lines on a chosen set of applications and labels, then scores
the whole book. It reuses the Feature 003 training arguments, seeds, and scorecard, so a refit on
every application with ``default_label`` reproduces the published shadow scores. Nothing here
approves or declines anyone, and nothing here reads the vendor.
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from scorecheck import models
from scorecheck.features import challenger_matrix

LINE_COLUMNS: tuple[str, ...] = (
    "lightgbm",
    "lightgbm_monotone",
    "xgboost",
    "xgboost_monotone",
    "hist_gradient_boosting",
    "hist_gradient_boosting_monotone",
    "scorecard_probability",
)


def woe_transform(train_values, labels, monotone: bool, score_values) -> np.ndarray:
    """Weight of evidence for ``score_values`` using the bins and weights learned on the training rows.

    On the training rows themselves this equals ``models.binned_weight_of_evidence`` exactly.
    """
    train_values = np.asarray(train_values, dtype=np.float64)
    score_values = np.asarray(score_values, dtype=np.float64)
    labels = np.asarray(labels)
    if np.unique(train_values).size <= 1:
        codes = np.zeros(len(train_values), dtype=np.int64)
        interior = np.empty(0, dtype=np.float64)
    else:
        cut, edges = pd.qcut(train_values, q=10, duplicates="drop", retbins=True)
        codes = np.asarray(cut.codes, dtype=np.int64)
        interior = np.asarray(edges, dtype=np.float64)[1:-1]
    goods = labels == 0
    bads = labels == 1
    n_bins = int(codes.max()) + 1 if len(codes) else 0
    good_counts = np.bincount(codes, weights=goods.astype(np.float64), minlength=n_bins).astype(np.float64)
    bad_counts = np.bincount(codes, weights=bads.astype(np.float64), minlength=n_bins).astype(np.float64)
    mapping = np.arange(n_bins, dtype=np.int64)
    if monotone:
        good_counts, bad_counts, mapping = models._merge_monotone(good_counts, bad_counts, mapping)
    weights = models._weight_of_evidence(good_counts, bad_counts)
    score_codes = np.searchsorted(interior, score_values, side="left")
    return weights[mapping[score_codes]]


def refit(features: pd.DataFrame, fit_ids, labels, seed: int) -> pd.DataFrame | None:
    """Fit the seven lines on ``fit_ids`` with ``labels`` and score every application.

    Returns ``application_id`` plus the seven line columns, sorted by ``application_id``. An empty
    fit or one with a single label class cannot train, so it returns None and the caller keeps
    the previous scores.
    """
    fit_ids = np.asarray(fit_ids, dtype=np.int64)
    labels = np.asarray(labels, dtype=np.int64)
    if len(fit_ids) != len(labels):
        raise ValueError("fit_ids and labels differ in length")
    if len(fit_ids) == 0 or np.unique(labels).size < 2:
        return None
    ordered = features.sort_values("application_id", kind="mergesort").reset_index(drop=True)
    application_id = ordered["application_id"].to_numpy(dtype=np.int64)
    matrix = challenger_matrix(ordered)
    position = pd.Series(np.arange(len(application_id)), index=application_id)
    rows = position.loc[fit_ids].to_numpy()
    fitted = models._fit_challengers(
        matrix.iloc[rows].reset_index(drop=True), labels, int(seed), score_matrix=matrix
    )
    data = {"application_id": application_id}
    for name in LINE_COLUMNS:
        data[name] = np.asarray(fitted[name], dtype=np.float64)
    return pd.DataFrame(data)


def write(regime_dir: Path | str, frame: pd.DataFrame, features_hash: str, fit_hash: str) -> None:
    """Write ``<regime_dir>/challengers/scores.parquet`` and ``bind.json``."""
    folder = Path(regime_dir) / "challengers"
    folder.mkdir(parents=True, exist_ok=True)
    columns = ["application_id", *LINE_COLUMNS]
    ordered = frame.loc[:, columns].sort_values("application_id", kind="mergesort").reset_index(drop=True)
    tmp = folder / f".scores.parquet.tmp-{os.getpid()}"
    ordered.to_parquet(tmp, index=False)
    os.replace(tmp, folder / "scores.parquet")
    bind = {"features_hash": features_hash, "fit_ids_hash": fit_hash}
    (folder / "bind.json").write_text(json.dumps(bind), encoding="utf-8")
