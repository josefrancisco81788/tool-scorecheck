"""Application-time features built from a panel run."""

from pathlib import Path

import pandas as pd

from scorecheck import panel, rundir
from scorecheck._streams import Streams
from scorecheck.features import _application

__all__ = ["from_panel"]


def from_panel(run_dir: Path | str) -> pd.DataFrame:
    """Build application_features for a run, write it beside the panel, and return the written frame."""
    view = panel.read_at_origination(run_dir)
    frame = _application.build(view, Streams(view.seed, "application"))
    return rundir.write_application_features(Path(run_dir), frame)
