"""Ledger fit and the directory swap. Callers outside this package use scorecheck.vendor."""

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from scorecheck import rundir, schema
from scorecheck._streams import Streams
from scorecheck.logical_hash import logical_hash
from scorecheck.schema import SchemaError

EXCLUDED = frozenset({
    "application_id", "person_id", "age_years", "gender", "education", "marital_status", "region",
    "external_score_1", "external_score_2", "external_score_3", "default_label", "label_observed",
})

_TRUTH_COLUMNS = ("person_id", "month", "vendor_signal")


@dataclass(frozen=True)
class TrainingTable:
    application_id: np.ndarray
    matrix: pd.DataFrame
    label: np.ndarray
    features_hash: str
    seed: int
    single_class: bool


def ledger_dir(run_dir: Path) -> Path:
    run_dir = Path(run_dir)
    return run_dir.parent.with_name("vendor") / run_dir.name


def read_features(run_dir: Path) -> pd.DataFrame:
    return pd.read_parquet(Path(run_dir) / schema.APPLICATION_FEATURES.file_name)


def features_hash(run_dir: Path) -> str:
    return logical_hash(read_features(run_dir))


def _origination(run_dir: Path) -> pd.DataFrame:
    person = pd.read_parquet(Path(run_dir) / "person.parquet", columns=["person_id", "origination_month"])
    truth = pd.read_parquet(Path(run_dir) / "ground_truth.parquet", columns=list(_TRUTH_COLUMNS))
    aligned = truth.merge(person, on="person_id", how="inner")
    kept = aligned.loc[aligned["month"] == aligned["origination_month"], list(_TRUTH_COLUMNS)]
    return kept.reset_index(drop=True)


def _fit_names(features: pd.DataFrame) -> list[str]:
    return [name for name in features.columns if name not in EXCLUDED] + ["private_factor"]


def assemble(run_dir: Path, groups: dict[str, str]) -> TrainingTable:
    """Build the training table or raise SchemaError before any ledger write."""
    run_dir = Path(run_dir)
    features = read_features(run_dir)
    origin = _origination(run_dir)
    applicants = set(features["person_id"])
    if origin["person_id"].duplicated().any() or not applicants.issubset(set(origin["person_id"])):
        raise SchemaError("application_features person has no single origination row")
    if set(groups) != set(_fit_names(features)):
        raise SchemaError("COLUMN_GROUPS keys are not the fit columns")

    ordered = features.sort_values("application_id", kind="mergesort").reset_index(drop=True)
    signal = origin.set_index("person_id")["vendor_signal"]
    private = ordered["person_id"].map(signal).astype(np.float64)
    columns = list(groups)
    matrix = pd.DataFrame({name: ordered[name].to_numpy(dtype=np.float64) for name in columns if name != "private_factor"})
    matrix["private_factor"] = private.to_numpy()
    matrix = matrix.loc[:, columns]
    label = ordered["default_label"].to_numpy()
    return TrainingTable(
        application_id=ordered["application_id"].to_numpy(dtype=np.int64),
        matrix=matrix,
        label=label,
        features_hash=logical_hash(features),
        seed=rundir.read_run_config(run_dir).seed,
        single_class=int(np.unique(label).size) == 1,
    )


def one_class_probability(table: TrainingTable) -> np.ndarray:
    rate = float(np.asarray(table.label, dtype=np.float64).mean())
    return np.full(len(table.application_id), rate, dtype=np.float64)


def fit(table: TrainingTable) -> tuple[np.ndarray, list[dict[str, float]]]:
    import lightgbm

    drawn = int(Streams(table.seed, "vendor")("lightgbm").integers(0, 2**31))
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
        "seed": drawn,
        "bagging_seed": drawn,
        "feature_fraction_seed": drawn,
        "data_random_seed": drawn,
    }
    names = list(table.matrix.columns)
    data = table.matrix.to_numpy(dtype=np.float64)
    dataset = lightgbm.Dataset(data, label=table.label.astype(np.float64), feature_name=names)
    booster = lightgbm.train(params, dataset, num_boost_round=40)
    probability = np.clip(booster.predict(data), 0.0, 1.0).astype(np.float64)
    contrib = np.asarray(booster.predict(data, pred_contrib=True), dtype=np.float64)[:, :-1]
    rows = [{name: float(contrib[i, j]) for j, name in enumerate(names)} for i in range(len(data))]
    return probability, rows


def place(
    run_dir: Path,
    features_hash: str,
    application_id: np.ndarray,
    probability: np.ndarray,
    reasons: list[tuple],
) -> None:
    """Stage ledger.parquet and bind.json, then rename the directory onto the ledger path.

    Windows cannot rename onto an existing directory, so a previous ledger moves to a backup
    sibling first and returns only if the new rename fails.
    """
    final = ledger_dir(run_dir)
    parent = final.parent
    stage = parent / f".{final.name}.staging-{os.getpid()}"
    backup = parent / f".{final.name}.previous-{os.getpid()}"
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir()
    try:
        _write_stage(stage, features_hash, application_id, probability, reasons)
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


def _write_stage(stage, features_hash, application_id, probability, reasons) -> None:
    reason_1, reason_2, reason_3 = zip(*reasons)
    frame = pd.DataFrame({
        "application_id": np.asarray(application_id, dtype=np.int64),
        "probability": np.asarray(probability, dtype=np.float64),
        "reason_1": [code.value for code in reason_1],
        "reason_2": [code.value for code in reason_2],
        "reason_3": [code.value for code in reason_3],
    })
    frame = frame.sort_values("application_id", kind="mergesort").reset_index(drop=True)
    frame.to_parquet(stage / "ledger.parquet", index=False)
    (stage / "bind.json").write_text(json.dumps({"features_hash": features_hash}), encoding="utf-8")
