"""Shared setup for the Feature 004 experiment tests."""

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from support.vendor import copied_run

CHECKPOINTS = (4, 8, 12, 16, 20, 24)
REGIMES = ("vendor_only", "data_owner")
LINES = (
    "lightgbm", "lightgbm_monotone", "xgboost", "xgboost_monotone",
    "hist_gradient_boosting", "hist_gradient_boosting_monotone", "scorecard_probability",
)


def experiment_dir(run_dir: Path) -> Path:
    return run_dir.parent.with_name("experiment") / run_dir.name


def bad_6m(run_dir: Path) -> pd.Series:
    """Independent 6-month bad label, indexed by application_id."""
    features = pd.read_parquet(run_dir / "application_features.parquet", columns=["application_id", "person_id"])
    person = pd.read_parquet(run_dir / "person.parquet", columns=["person_id", "origination_month"])
    truth = pd.read_parquet(run_dir / "ground_truth.parquet", columns=["person_id", "month", "true_default"])
    first = truth.loc[truth["true_default"] == 1].groupby("person_id")["month"].min()
    merged = features.merge(person, on="person_id")
    first_month = merged["person_id"].map(first)
    bad = first_month.notna() & (first_month <= merged["origination_month"] + 6)
    return pd.Series(bad.to_numpy(), index=merged["application_id"].to_numpy()).sort_index()


@dataclass
class Experiment:
    run_dir: Path
    exp_dir: Path
    fit_calls: list = field(default_factory=list)
    vendor_results: list = field(default_factory=list)

    def read(self, name: str) -> pd.DataFrame:
        return pd.read_parquet(self.exp_dir / name)

    @cached_property
    def outcomes(self) -> pd.DataFrame:
        return self.read("outcomes.parquet")

    @cached_property
    def curves(self) -> pd.DataFrame:
        return self.read("curves.parquet")

    @cached_property
    def fits(self) -> pd.DataFrame:
        return self.read("fits.parquet")

    @cached_property
    def heldout(self) -> pd.DataFrame:
        return self.read("heldout_scores.parquet")

    @cached_property
    def features(self) -> pd.DataFrame:
        return pd.read_parquet(self.run_dir / "application_features.parquet")


def prepare(source_run_dir: Path, tmp_path: Path, publish_models: bool = False) -> Experiment:
    """Copy a run under tmp_path, publish the vendor ledger, run the experiment, record fit calls."""
    from scorecheck import experiment, models, vendor
    from scorecheck.models import regime as models_regime
    from scorecheck.vendor import regime as vendor_regime

    run_dir = copied_run(source_run_dir, tmp_path)
    vendor.publish(run_dir)
    if publish_models:
        models.publish(run_dir)
    calls: list = []
    results: list = []
    real_vendor_fit = vendor_regime.Refitter.fit
    real_refit = models_regime.refit

    def vendor_fit(self, fit_ids, labels):
        calls.append(("vendor", np.asarray(fit_ids).copy(), np.asarray(labels).copy()))
        result = real_vendor_fit(self, fit_ids, labels)
        results.append(result)
        return result

    def challenger_refit(features, fit_ids, labels, seed):
        calls.append(("challenger", np.asarray(fit_ids).copy(), np.asarray(labels).copy()))
        return real_refit(features, fit_ids, labels, seed)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(vendor_regime.Refitter, "fit", vendor_fit)
        patch.setattr(models_regime, "refit", challenger_refit)
        out = experiment.run(run_dir)
    assert out == experiment_dir(run_dir)
    return Experiment(run_dir=run_dir, exp_dir=out, fit_calls=calls, vendor_results=results)
