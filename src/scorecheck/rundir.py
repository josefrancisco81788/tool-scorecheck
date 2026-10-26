"""Sole owner of the on-disk run layout."""

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd

from scorecheck import config, schema
from scorecheck.schema import TableSpec

RUN_CONFIG_FILE = "run_config.json"
PANEL_FILES: tuple[str, ...] = tuple(s.file_name for s in schema.PANEL_TABLES) + (RUN_CONFIG_FILE,)


def run_id(seed: int, n_households: int) -> str:
    text = f"{seed}|{n_households}|{config.N_MONTHS}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class RunConfig:
    seed: int
    n_households: int

    @property
    def run_id(self) -> str:
        return run_id(self.seed, self.n_households)

    def to_json(self) -> str:
        return json.dumps(
            {
                "seed": self.seed,
                "n_households": self.n_households,
                "scale": config.scale_name(self.n_households),
                "n_months": config.N_MONTHS,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> "RunConfig":
        data = json.loads(text)
        if set(data) != {"seed", "n_households", "scale", "n_months"}:
            raise schema.SchemaError(f"run_config.json keys are {sorted(data)}")
        if data["n_months"] != config.N_MONTHS:
            raise schema.SchemaError(f"run_config.json n_months is {data['n_months']}")
        return cls(seed=int(data["seed"]), n_households=int(data["n_households"]))


def write_run(data_dir: Path, run: RunConfig, tables: Mapping[TableSpec, pd.DataFrame]) -> Path:
    """Write exactly PANEL_FILES into data_dir/<run id>/, replacing any earlier run with that id.

    Tables are staged in a dot-prefixed sibling and renamed into place. Windows cannot rename onto
    an existing directory, so a previous run directory is removed first.
    """
    if set(tables) != set(schema.PANEL_TABLES):
        raise ValueError("write_run needs exactly the seven panel tables")
    data_dir = Path(data_dir)
    stage = data_dir / f".{run.run_id}.staging-{os.getpid()}"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    for spec, frame in tables.items():
        schema.conform(frame, spec).to_parquet(stage / spec.file_name, index=False)
    (stage / RUN_CONFIG_FILE).write_text(run.to_json(), encoding="utf-8")
    final = data_dir / run.run_id
    if final.exists():
        shutil.rmtree(final)
    os.replace(stage, final)
    return final


def write_application_features(run_dir: Path, frame: pd.DataFrame) -> pd.DataFrame:
    spec = schema.APPLICATION_FEATURES
    conformed = schema.conform(frame, spec)
    tmp = Path(run_dir) / f".{spec.file_name}.tmp-{os.getpid()}"
    conformed.to_parquet(tmp, index=False)
    os.replace(tmp, Path(run_dir) / spec.file_name)
    return conformed


def read_table(run_dir: Path, spec: TableSpec, columns: Sequence[str] | None = None) -> pd.DataFrame:
    frame = pd.read_parquet(Path(run_dir) / spec.file_name, columns=None if columns is None else list(columns))
    return schema.conform(frame, spec, columns)


def read_run_config(run_dir: Path) -> RunConfig:
    return RunConfig.from_json((Path(run_dir) / RUN_CONFIG_FILE).read_text(encoding="utf-8"))
