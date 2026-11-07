"""Read the Feature 004 held-out scores and outcomes, build the tables, write ``report/``.

Inputs are only: ``heldout_scores.parquet`` and ``outcomes.parquet`` under the experiment directory,
and the processed ``application_features``, ``person`` and ``household`` tables. The vendor is never
reached; its held-out scores come from the experiment file.
"""

import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from scorecheck import rundir
from scorecheck._streams import Streams
from scorecheck.report import _constants as c
from scorecheck.report import _summary, _tables

_FEATURE_COLUMNS = [
    "application_id", "person_id", "age_years", "credit_amount", "history_months", "gender", "region",
]


def run(run_dir: Path | str) -> Path:
    """Write ``data/experiment/<run id>/report/``. Prints nothing."""
    run_dir = Path(run_dir)
    exp_dir = rundir.experiment_dir(run_dir)
    seed = rundir.read_run_config(run_dir).seed
    frames, outcomes = _read(run_dir, exp_dir)
    draw = Streams(seed, "report")("phased_switch").random(len(next(iter(frames.values()))))
    tables = {
        "lift_by_group.csv": _tables.lift_by_group(frames),
        "phased_switch.csv": _tables.phased_switch(frames, draw),
        "swap_sets.csv": _tables.swap_sets(frames, outcomes),
        "equal_approval.csv": _tables.equal_approval(frames),
        "full_lines.csv": _tables.full_lines(frames),
    }
    summary = _summary.build(tables, frames[c.HEADLINE_REGIME])
    return _place(exp_dir, tables, summary)


def _read(run_dir: Path, exp_dir: Path) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    features = pd.read_parquet(run_dir / "application_features.parquet", columns=_FEATURE_COLUMNS)
    person = pd.read_parquet(run_dir / "person.parquet", columns=["person_id", "household_id"])
    household = pd.read_parquet(run_dir / "household.parquet", columns=["household_id", "income_band", "urban_rural"])
    attributes = features.merge(person, on="person_id", validate="one_to_one").merge(
        household, on="household_id", validate="many_to_one"
    )
    held = pd.read_parquet(exp_dir / "heldout_scores.parquet")
    outcomes = pd.read_parquet(exp_dir / "outcomes.parquet")
    frames: dict[str, pd.DataFrame] = {}
    cells: dict[str, pd.DataFrame] = {}
    for regime in c.REGIMES:
        rows = held[(held["regime"] == regime) & (held["checkpoint"] == c.CHECKPOINT)]
        merged = rows.merge(attributes, on="application_id", validate="one_to_one")
        frame = merged.sort_values("application_id", kind="mergesort").reset_index(drop=True)
        frames[regime] = _tables.add_groups(frame)
        cells[regime] = outcomes[(outcomes["regime"] == regime) & (outcomes["checkpoint"] == c.CHECKPOINT)]
    return frames, cells


def _write(stage: Path, tables: dict[str, pd.DataFrame], summary: str) -> None:
    for name, frame in tables.items():
        frame.round(c.ROUND).to_csv(stage / name, index=False, lineterminator="\n")
    (stage / "summary.md").write_text(summary, encoding="utf-8", newline="")


def _place(exp_dir: Path, tables: dict[str, pd.DataFrame], summary: str) -> Path:
    """Stage every file, then rename onto ``report/``. A previous report moves aside first."""
    final = exp_dir / "report"
    stage = exp_dir / f".report.staging-{os.getpid()}"
    backup = exp_dir / f".report.previous-{os.getpid()}"
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    stage.mkdir(parents=True)
    try:
        _write(stage, tables, summary)
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
    return final
