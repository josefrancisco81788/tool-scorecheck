"""Shared setup for vendor ledger tests. Product code stays behind scorecheck.vendor."""

import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from scorecheck import logical_hash


class FitCapture:
    def __init__(self) -> None:
        self.train_calls = 0
        self.dataset_calls = 0
        self.params = None
        self.num_boost_round = None
        self.train_kwargs = None
        self.feature_name = None
        self.matrix = None
        self.label = None
        self.contrib = None


def spy_lightgbm(monkeypatch) -> FitCapture:
    import lightgbm

    capture = FitCapture()
    real_dataset = lightgbm.Dataset
    real_train = lightgbm.train
    real_predict = lightgbm.Booster.predict

    def dataset(data, label=None, feature_name="auto", **kwargs):
        capture.dataset_calls += 1
        capture.matrix = np.ascontiguousarray(data, dtype=np.float64).copy()
        capture.label = None if label is None else np.asarray(label).copy()
        capture.feature_name = None if feature_name == "auto" else list(feature_name)
        return real_dataset(data, label=label, feature_name=feature_name, **kwargs)

    def train(params, train_set, num_boost_round=100, **kwargs):
        capture.train_calls += 1
        capture.params = dict(params)
        capture.num_boost_round = num_boost_round
        capture.train_kwargs = dict(kwargs)
        return real_train(params, train_set, num_boost_round=num_boost_round, **kwargs)

    def predict(self, data, *args, **kwargs):
        pred_contrib = kwargs.get("pred_contrib", False)
        out = real_predict(self, data, *args, **kwargs)
        if pred_contrib:
            capture.contrib = np.asarray(out, dtype=np.float64).copy()
        return out

    monkeypatch.setattr(lightgbm, "Dataset", dataset)
    monkeypatch.setattr(lightgbm, "train", train)
    monkeypatch.setattr(lightgbm.Booster, "predict", predict)
    return capture


def copied_run(source: Path, tmp_path: Path) -> Path:
    """Place a run under tmp_path/processed so the ledger sibling stays inside the test tmp."""
    root = tmp_path / "processed"
    root.mkdir(parents=True, exist_ok=True)
    dest = root / source.name
    shutil.copytree(source, dest)
    return dest


def ledger_dir(run_dir: Path) -> Path:
    return run_dir.parent.with_name("vendor") / run_dir.name


def read_features(run_dir: Path) -> pd.DataFrame:
    return pd.read_parquet(run_dir / "application_features.parquet")


def write_features(run_dir: Path, frame: pd.DataFrame) -> None:
    frame.to_parquet(run_dir / "application_features.parquet", index=False)


def feature_hash(run_dir: Path) -> str:
    return logical_hash.logical_hash(read_features(run_dir))


def one_class(run_dir: Path, label: int) -> None:
    frame = read_features(run_dir)
    frame["default_label"] = np.int64(label)
    write_features(run_dir, frame)


def two_class(run_dir: Path) -> pd.DataFrame:
    """Lower half of application_id values are 0. Upper half are 1."""
    frame = read_features(run_dir).sort_values("application_id", kind="mergesort").reset_index(drop=True)
    labels = np.zeros(len(frame), dtype=np.int64)
    labels[len(frame) // 2 :] = 1
    frame["default_label"] = labels
    write_features(run_dir, frame)
    return frame


def ledger_hash(frame: pd.DataFrame) -> str:
    """Panel logical hash, plus the string cast for the three reason columns."""
    added = frozenset({"reason_1", "reason_2", "reason_3"})
    original = logical_hash._STR_COLUMNS
    logical_hash._STR_COLUMNS = original | added
    try:
        return logical_hash.logical_hash(frame)
    finally:
        logical_hash._STR_COLUMNS = original
