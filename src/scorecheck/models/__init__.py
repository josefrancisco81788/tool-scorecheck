"""In-house challengers in shadow mode.

Scores are written beside the vendor ledger, under ``data/models/<run id>/``. Nothing here
approves or declines an application. Books of at most 300 applications copy
``vendor_probability`` through ``vendor.score``. Larger books, including the default command,
store 0.5 in that column so publish does not hash the feature file once per row.
"""

import json
import math
import os
import shutil
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

from scorecheck import rundir, schema, vendor
from scorecheck._streams import Streams
from scorecheck.features import MATRIX_COLUMNS, MONOTONE_COLUMNS, challenger_matrix
from scorecheck.logical_hash import logical_hash

__all__ = [
    "publish",
    "line",
    "ChallengerLines",
    "ScoresMissing",
    "StaleScores",
    "UnknownApplicant",
]

PER_ROW_LIMIT = 300
LARGE_BOOK_VENDOR_PROBABILITY = 0.5
PDO = 20
BASE_POINTS = 600
BASE_ODDS = 50
_FACTOR = PDO / math.log(2)
_OFFSET = BASE_POINTS - _FACTOR * math.log(BASE_ODDS)
_CONSTRAINTS = tuple(1 if name in MONOTONE_COLUMNS else 0 for name in MATRIX_COLUMNS)

_PROBABILITY_COLUMNS = (
    "vendor_probability",
    "lightgbm",
    "lightgbm_monotone",
    "xgboost",
    "xgboost_monotone",
    "hist_gradient_boosting",
    "hist_gradient_boosting_monotone",
    "scorecard_probability",
)
_SCORE_COLUMNS = ("application_id",) + _PROBABILITY_COLUMNS + ("scorecard_points",)


class ChallengerLines(NamedTuple):
    vendor_probability: float
    lightgbm: float
    lightgbm_monotone: float
    xgboost: float
    xgboost_monotone: float
    hist_gradient_boosting: float
    hist_gradient_boosting_monotone: float
    scorecard_probability: float
    scorecard_points: float | None


class ScoresMissing(Exception):
    """The scores directory is absent or does not hold both scores files."""


class StaleScores(Exception):
    """application_features no longer matches the hash stored beside the scores."""


class UnknownApplicant(Exception):
    """This application_id is not in the scores file."""


def scores_dir(run_dir: Path) -> Path:
    run_dir = Path(run_dir)
    return run_dir.parent.with_name("models") / run_dir.name


def binned_weight_of_evidence(values, labels, monotone: bool) -> np.ndarray:
    """One weight-of-evidence float per input row. Not part of the public surface."""
    values = np.asarray(values, dtype=np.float64)
    labels = np.asarray(labels)
    if np.unique(values).size <= 1:
        codes = np.zeros(len(values), dtype=np.int64)
    else:
        codes = np.asarray(pd.qcut(values, q=10, duplicates="drop").codes, dtype=np.int64)
    goods = labels == 0
    bads = labels == 1
    n_bins = int(codes.max()) + 1 if len(codes) else 0
    good_counts = np.bincount(codes, weights=goods.astype(np.float64), minlength=n_bins).astype(np.float64)
    bad_counts = np.bincount(codes, weights=bads.astype(np.float64), minlength=n_bins).astype(np.float64)
    if monotone:
        good_counts, bad_counts, codes = _merge_monotone(good_counts, bad_counts, codes)
    weights = _weight_of_evidence(good_counts, bad_counts)
    return weights[codes]


def points_to_double_the_odds(probability: float) -> float:
    """Points at the stored probability. Not part of the public surface."""
    clipped = min(max(float(probability), 1e-6), 1.0 - 1e-6)
    odds = (1.0 - clipped) / clipped
    return float(_OFFSET + _FACTOR * math.log(odds))


def publish(run_dir: Path | str) -> None:
    """Fit the four challenger lines and write scores.parquet plus bind.json."""
    run_dir = Path(run_dir)
    features = pd.read_parquet(run_dir / schema.APPLICATION_FEATURES.file_name)
    features_hash = logical_hash(features)
    ordered = features.sort_values("application_id", kind="mergesort").reset_index(drop=True)
    application_id = ordered["application_id"].to_numpy(dtype=np.int64)
    label = ordered["default_label"].to_numpy()
    vendor_probability = _vendor_probability(run_dir, application_id)
    if int(np.unique(label).size) == 1:
        frame = _one_class_frame(application_id, label)
    else:
        matrix = challenger_matrix(ordered)
        seed = rundir.read_run_config(run_dir).seed
        fitted = _fit_challengers(matrix, label, seed)
        fitted["vendor_probability"] = vendor_probability
        frame = _scores_frame(application_id, fitted)
    _place(run_dir, features_hash, frame)


def line(run_dir: Path | str, application_id: int) -> ChallengerLines:
    """Read one application's challenger scores from disk."""
    run_dir = Path(run_dir)
    directory = scores_dir(run_dir)
    scores_file = directory / "scores.parquet"
    bind_file = directory / "bind.json"
    if not scores_file.is_file() or not bind_file.is_file():
        raise ScoresMissing(directory)
    bound = json.loads(bind_file.read_text(encoding="utf-8"))["features_hash"]
    current = logical_hash(pd.read_parquet(run_dir / schema.APPLICATION_FEATURES.file_name))
    if bound != current:
        raise StaleScores(run_dir)
    scores = pd.read_parquet(scores_file)
    hit = scores.loc[scores["application_id"] == application_id]
    if hit.empty:
        raise UnknownApplicant(application_id)
    row = hit.iloc[0]
    points = row["scorecard_points"]
    return ChallengerLines(
        *(float(row[name]) for name in _PROBABILITY_COLUMNS),
        None if pd.isna(points) else float(points),
    )


def _vendor_probability(run_dir: Path, application_id: np.ndarray) -> np.ndarray:
    if len(application_id) > PER_ROW_LIMIT:
        return np.full(len(application_id), LARGE_BOOK_VENDOR_PROBABILITY, dtype=np.float64)
    values = [
        float(vendor.score(run_dir, int(app_id)).probability)
        for app_id in application_id
    ]
    return np.asarray(values, dtype=np.float64)


def _one_class_frame(application_id: np.ndarray, label: np.ndarray) -> pd.DataFrame:
    rate = float(np.asarray(label, dtype=np.float64).mean())
    columns = {
        name: np.full(len(application_id), rate, dtype=np.float64)
        for name in _PROBABILITY_COLUMNS
    }
    columns["scorecard_points"] = np.full(len(application_id), np.nan, dtype=np.float64)
    return _scores_frame(application_id, columns)


def _fit_challengers(matrix: pd.DataFrame, label: np.ndarray, seed: int) -> dict[str, np.ndarray]:
    import lightgbm
    import sklearn.ensemble
    import sklearn.linear_model
    import xgboost

    streams = Streams(int(seed), "models")
    lightgbm_seed = int(streams("lightgbm").integers(0, 2**31))
    xgboost_seed = int(streams("xgboost").integers(0, 2**31))
    histogram_seed = int(streams("hist_gradient_boosting").integers(0, 2**31))
    scorecard_seed = int(streams("scorecard").integers(0, 2**31))
    data = np.ascontiguousarray(matrix.to_numpy(dtype=np.float64))
    label = np.asarray(label)
    return {
        "lightgbm": _lightgbm_probability(lightgbm, data, label, lightgbm_seed, monotone=False),
        "lightgbm_monotone": _lightgbm_probability(lightgbm, data, label, lightgbm_seed, monotone=True),
        "xgboost": _xgboost_probability(xgboost, data, label, xgboost_seed, monotone=False),
        "xgboost_monotone": _xgboost_probability(xgboost, data, label, xgboost_seed, monotone=True),
        "hist_gradient_boosting": _histogram_probability(
            sklearn.ensemble, data, label, histogram_seed, monotone=False
        ),
        "hist_gradient_boosting_monotone": _histogram_probability(
            sklearn.ensemble, data, label, histogram_seed, monotone=True
        ),
        **_scorecard(sklearn.linear_model, matrix, label, scorecard_seed),
    }


def _lightgbm_probability(lightgbm, data, label, seed: int, monotone: bool) -> np.ndarray:
    params = {
        "objective": "binary",
        "deterministic": True,
        "force_row_wise": True,
        "device_type": "cpu",
        "num_threads": 1,
        "feature_fraction": 1.0,
        "bagging_fraction": 1.0,
        "bagging_freq": 0,
        "num_leaves": 15,
        "learning_rate": 0.1,
        "verbose": -1,
        "seed": seed,
        "bagging_seed": seed,
        "feature_fraction_seed": seed,
        "data_random_seed": seed,
    }
    if monotone:
        params["monotone_constraints"] = [int(value) for value in _CONSTRAINTS]
        params["monotone_constraints_method"] = "advanced"
    dataset = lightgbm.Dataset(data, label=np.asarray(label, dtype=np.float64))
    booster = lightgbm.train(params, dataset, num_boost_round=40)
    predicted = booster.predict(data)
    return np.clip(np.asarray(predicted, dtype=np.float64), 0.0, 1.0)


def _xgboost_probability(xgboost, data, label, seed: int, monotone: bool) -> np.ndarray:
    model = xgboost.XGBClassifier(
        n_estimators=40,
        learning_rate=0.1,
        max_leaves=15,
        grow_policy="lossguide",
        tree_method="hist",
        subsample=1,
        colsample_bytree=1,
        n_jobs=1,
        random_state=seed,
        objective="binary:logistic",
        verbosity=0,
        monotone_constraints=None if not monotone else tuple(int(value) for value in _CONSTRAINTS),
    )
    model.fit(data, label)
    return _positive_class(model, data)


def _histogram_probability(ensemble, data, label, seed: int, monotone: bool) -> np.ndarray:
    model = ensemble.HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.1,
        max_iter=40,
        max_leaf_nodes=15,
        min_samples_leaf=20,
        l2_regularization=0.0,
        max_features=1.0,
        max_bins=255,
        categorical_features=None,
        early_stopping=False,
        random_state=seed,
        verbose=0,
        monotonic_cst=None if not monotone else tuple(int(value) for value in _CONSTRAINTS),
    )
    model.fit(data, label)
    return _positive_class(model, data)


def _scorecard(linear_model, matrix: pd.DataFrame, label: np.ndarray, seed: int) -> dict[str, np.ndarray]:
    columns = []
    for name in MATRIX_COLUMNS:
        columns.append(
            binned_weight_of_evidence(
                matrix[name].to_numpy(dtype=np.float64),
                label,
                name in MONOTONE_COLUMNS,
            )
        )
    woe = np.column_stack(columns)
    model = linear_model.LogisticRegression(C=1.0, solver="lbfgs", max_iter=500, random_state=seed)
    model.fit(woe, label)
    probability = _positive_class(model, woe)
    points = np.asarray([points_to_double_the_odds(value) for value in probability], dtype=np.float64)
    return {"scorecard_probability": probability, "scorecard_points": points}


def _positive_class(model, data) -> np.ndarray:
    proba = np.asarray(model.predict_proba(data), dtype=np.float64)
    column = [int(value) for value in model.classes_].index(1)
    return np.clip(proba[:, column], 0.0, 1.0)


def _scores_frame(application_id: np.ndarray, columns: dict[str, np.ndarray]) -> pd.DataFrame:
    data = {"application_id": np.asarray(application_id, dtype=np.int64)}
    for name in _PROBABILITY_COLUMNS:
        data[name] = np.asarray(columns[name], dtype=np.float64)
    data["scorecard_points"] = np.asarray(columns["scorecard_points"], dtype=np.float64)
    frame = pd.DataFrame(data, columns=list(_SCORE_COLUMNS))
    return frame.sort_values("application_id", kind="mergesort").reset_index(drop=True)


def _place(run_dir: Path, features_hash: str, frame: pd.DataFrame) -> None:
    """Stage both scores files, then rename the directory onto the scores path."""
    final = scores_dir(run_dir)
    parent = final.parent
    stage = parent / f".{final.name}.staging-{os.getpid()}"
    backup = parent / f".{final.name}.previous-{os.getpid()}"
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir()
    try:
        frame.to_parquet(stage / "scores.parquet", index=False)
        (stage / "bind.json").write_text(
            json.dumps({"features_hash": features_hash}), encoding="utf-8"
        )
        if final.exists():
            os.replace(final, backup)
        try:
            os.replace(stage, final)
        except BaseException:
            if backup.exists():
                os.replace(backup, final)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)


def _weight_of_evidence(good_counts: np.ndarray, bad_counts: np.ndarray) -> np.ndarray:
    dist_good = (good_counts + 0.5) / np.sum(good_counts + 0.5)
    dist_bad = (bad_counts + 0.5) / np.sum(bad_counts + 0.5)
    return np.log(dist_good / dist_bad)


def _merge_monotone(
    good_counts: np.ndarray, bad_counts: np.ndarray, codes: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    good_counts = good_counts.copy()
    bad_counts = bad_counts.copy()
    codes = codes.copy()
    while good_counts.size > 1:
        weights = _weight_of_evidence(good_counts, bad_counts)
        violating = np.flatnonzero(weights[1:] > weights[:-1])
        if violating.size == 0:
            break
        index = int(violating[0])
        good_counts[index] += good_counts[index + 1]
        bad_counts[index] += bad_counts[index + 1]
        good_counts = np.delete(good_counts, index + 1)
        bad_counts = np.delete(bad_counts, index + 1)
        codes = np.where(codes == index + 1, index, np.where(codes > index + 1, codes - 1, codes))
    return good_counts, bad_counts, codes
