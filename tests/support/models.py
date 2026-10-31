"""Shared setup for challenger score tests."""

from pathlib import Path

import pandas as pd

from scorecheck.logical_hash import logical_hash


def scores_dir(run_dir: Path) -> Path:
    run_dir = Path(run_dir)
    return run_dir.parent.with_name("models") / run_dir.name


def read_scores(run_dir: Path) -> pd.DataFrame:
    return pd.read_parquet(scores_dir(run_dir) / "scores.parquet")


def scores_hash(frame: pd.DataFrame) -> str:
    return logical_hash(frame)
