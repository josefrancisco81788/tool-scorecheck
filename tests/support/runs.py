from functools import cached_property
from pathlib import Path

import pandas as pd

from scorecheck import features, panel

PANEL_TABLE_NAMES = (
    "household", "person", "sim", "electricity_account", "ewallet_account", "month_behaviour", "ground_truth",
)
ALL_TABLE_NAMES = PANEL_TABLE_NAMES + ("application_features",)


class PanelRun:
    """Read-only access to one run directory's tables, each read once."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = Path(run_dir)
        self._tables: dict[str, pd.DataFrame] = {}

    def __getitem__(self, name: str) -> pd.DataFrame:
        if name not in self._tables:
            self._tables[name] = pd.read_parquet(self.run_dir / f"{name}.parquet")
        return self._tables[name].copy()

    @cached_property
    def origination_rows(self) -> pd.DataFrame:
        gt = self["ground_truth"].merge(self["person"][["person_id", "origination_month"]], on="person_id")
        rows = gt[gt["month"] == gt["origination_month"]]
        return rows.sort_values("person_id").reset_index(drop=True)


def generate_run(seed: int, n_households: int, data_dir, **overrides) -> PanelRun:
    """A run as the checks define it: panel.generate, then features.from_panel on its directory."""
    run_dir = panel.generate(seed, n_households, data_dir, **overrides)
    features.from_panel(run_dir)
    return PanelRun(run_dir)
