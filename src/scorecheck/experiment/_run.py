"""The experiment timeline: decisions, fits, and holdout curves for both regimes.

The vendor is reached only through ``scorecheck.vendor.regime`` (a batch read of the published
ledger and refits inside ``vendor/``). Challenger refits come from ``scorecheck.models.regime``.
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from scorecheck import rundir, schema
from scorecheck._streams import Streams
from scorecheck.experiment import _constants as constants
from scorecheck.experiment import _metrics
from scorecheck.models import regime as models_regime
from scorecheck.vendor import regime as vendor_regime

LINES = models_regime.LINE_COLUMNS
_CURVE_COLUMNS = (
    "regime", "checkpoint", "line", "holdout_n", "holdout_bads", "vendor_fit_n", "vendor_fit_bads",
    "vendor_fit_test_cell_n", "line_fit_n", "line_fit_bads", "line_fit_test_cell_n", "vendor_auc", "line_auc",
    "auc_gap", "auc_gap_low", "auc_gap_high", "vendor_log_loss", "line_log_loss", "log_loss_gap",
    "log_loss_gap_low", "log_loss_gap_high", "vendor_brier", "line_brier", "brier_gap", "brier_gap_low",
    "brier_gap_high",
)
_COUNT_COLUMNS = (
    "checkpoint", "holdout_n", "holdout_bads", "vendor_fit_n", "vendor_fit_bads", "vendor_fit_test_cell_n",
    "line_fit_n", "line_fit_bads", "line_fit_test_cell_n",
)
_CURVE_DTYPES = {
    name: ("object" if name in ("regime", "line") else "int64" if name in _COUNT_COLUMNS else "float64")
    for name in _CURVE_COLUMNS
}
_FIT_COLUMNS = ["regime", "checkpoint", "arm", "trained", "n", "bads", "test_cell_n", "fit_ids_hash"]
_REASON_FALLBACK = ("credit_stress", "capacity", "thin_file")


@dataclass(frozen=True)
class _Fit:
    """What produced a model: the size of its fit set and whether it trained."""

    checkpoint: int
    trained: bool
    n: int
    bads: int
    test_cell_n: int
    fit_hash: str


@dataclass(frozen=True)
class _VendorModel:
    ledger: pd.DataFrame
    fit: _Fit


@dataclass(frozen=True)
class _LineModel:
    scores: pd.DataFrame
    fit: _Fit


def run(run_dir: Path | str) -> Path:
    """Run both regimes and write ``data/experiment/<run id>/``. Prints nothing."""
    run_dir = Path(run_dir)
    published = vendor_regime.read_published(run_dir)
    features = pd.read_parquet(run_dir / schema.APPLICATION_FEATURES.file_name)
    features = features.sort_values("application_id", kind="mergesort").reset_index(drop=True)
    refitter = vendor_regime.Refitter(run_dir)
    application_id = features["application_id"].to_numpy(dtype=np.int64)
    if not (
        np.array_equal(application_id, refitter.application_id)
        and np.array_equal(application_id, published["application_id"].to_numpy())
    ):
        raise schema.SchemaError("vendor ledger and application_features list different applications")
    seed = rundir.read_run_config(run_dir).seed

    origination = _origination(run_dir, features)
    bad = _bad_label(run_dir, features, origination)
    holdout = application_id % constants.HOLDOUT_MODULUS == 0
    window = np.searchsorted(np.asarray(constants.CHECKPOINTS), origination, side="left")
    draw = Streams(seed, "experiment")("test_cell").random(len(application_id))
    default_label = features["default_label"].to_numpy(dtype=np.int64)

    start_vendor = _starting_vendor(refitter, application_id, holdout, default_label)
    start_lines = _starting_lines(features, seed, application_id, holdout, default_label)
    vendor_model, owner_lines = start_vendor, start_lines

    live = published["probability"].to_numpy(dtype=np.float64)
    approved = np.zeros(len(application_id), dtype=bool)
    test_cell = np.zeros(len(application_id), dtype=bool)
    cutoff = constants.APPROVAL_MAX_PROBABILITY
    applied_cutoff = np.full(len(application_id), np.nan)

    decisions: dict[int, dict[str, np.ndarray]] = {}
    vendor_by_checkpoint: dict[int, _VendorModel] = {}
    owner_by_checkpoint: dict[int, _LineModel] = {}
    checkpoint_fits: dict[int, tuple[_Fit, bool, bool]] = {}

    for index, checkpoint in enumerate(constants.CHECKPOINTS):
        # Applications that originated since the last checkpoint are decided by the live model,
        # before this checkpoint's refit.
        decided_now = window == index
        by_cutoff = constants.approve(live, cutoff)
        applied_cutoff[decided_now] = cutoff
        test_now = decided_now & ~holdout & ~by_cutoff & (draw < constants.TEST_CELL_SHARE)
        approved |= decided_now & (by_cutoff | test_now)
        test_cell |= test_now

        matured = origination + constants.BAD_WINDOW_MONTHS <= checkpoint
        observed = approved & ~holdout & matured
        fit_ids = application_id[observed]
        fit_labels = bad[observed].astype(np.int64)
        info = _fit_info(checkpoint, fit_ids, fit_labels, int(test_cell[observed].sum()))

        vendor_ledger = refitter.fit(fit_ids, fit_labels) if len(fit_ids) else None
        if vendor_ledger is not None:
            vendor_model = _VendorModel(vendor_ledger, _trained(info))
            live = vendor_ledger["probability"].to_numpy(dtype=np.float64)
            # Re-pin so about 20% of the next window is declined. Scores only, never outcomes.
            upcoming = window == index + 1
            if upcoming.any():
                cutoff = float(np.quantile(live[upcoming], 1.0 - constants.DECLINE_SHARE))
        line_scores = models_regime.refit(features, fit_ids, fit_labels, seed) if len(fit_ids) else None
        if line_scores is not None:
            owner_lines = _LineModel(line_scores, _trained(info))

        vendor_by_checkpoint[checkpoint] = vendor_model
        owner_by_checkpoint[checkpoint] = owner_lines
        checkpoint_fits[checkpoint] = (info, vendor_ledger is not None, line_scores is not None)
        decisions[checkpoint] = {
            "approved": approved.copy(),
            "test_cell": test_cell.copy(),
            "observed": observed,
            "on_book": origination <= checkpoint,
            "cutoff": applied_cutoff.copy(),
        }

    hold = np.flatnonzero(holdout)
    label = bad[hold].astype(np.int64)
    heldout_frames: list[pd.DataFrame] = []
    curve_rows: list[dict] = []
    for regime in constants.REGIMES:
        for checkpoint in constants.CHECKPOINTS:
            vendor = vendor_by_checkpoint[checkpoint]
            lines = start_lines if regime == "vendor_only" else owner_by_checkpoint[checkpoint]
            frame = _heldout_frame(regime, checkpoint, application_id[hold], label, vendor, lines, hold)
            heldout_frames.append(frame)
            curve_rows.extend(_curve_rows(regime, checkpoint, frame, vendor.fit, lines.fit))

    tables = {
        "outcomes": _outcomes(application_id, origination, holdout, bad, decisions),
        "fits": _fits_table(start_vendor, start_lines, checkpoint_fits),
        "heldout": pd.concat(heldout_frames, ignore_index=True),
        "curves": pd.DataFrame(curve_rows, columns=list(_CURVE_COLUMNS)).astype(_CURVE_DTYPES),
    }
    final = constants.CHECKPOINTS[-1]
    return _place(
        run_dir,
        refitter.features_hash,
        tables,
        vendor_by_checkpoint[final],
        {"vendor_only": start_lines, "data_owner": owner_by_checkpoint[final]},
    )


def _origination(run_dir: Path, features: pd.DataFrame) -> np.ndarray:
    person = pd.read_parquet(run_dir / "person.parquet", columns=["person_id", "origination_month"])
    month = person.set_index("person_id")["origination_month"]
    return features["person_id"].map(month).to_numpy(dtype=np.int64)


def _bad_label(run_dir: Path, features: pd.DataFrame, origination: np.ndarray) -> np.ndarray:
    """First month with true_default 1 is no later than origination month + the bad window."""
    truth = pd.read_parquet(run_dir / "ground_truth.parquet", columns=["person_id", "month", "true_default"])
    first = truth.loc[truth["true_default"] == 1].groupby("person_id")["month"].min()
    first_month = features["person_id"].map(first)
    reached = first_month.notna().to_numpy()
    month = first_month.fillna(0).to_numpy(dtype=np.int64)
    return reached & (month <= origination + constants.BAD_WINDOW_MONTHS)


def _fit_info(checkpoint: int, fit_ids: np.ndarray, labels: np.ndarray, test_cell_n: int) -> _Fit:
    return _Fit(
        checkpoint=checkpoint,
        trained=False,
        n=int(len(fit_ids)),
        bads=int(np.sum(labels)),
        test_cell_n=test_cell_n,
        fit_hash=vendor_regime.fit_ids_hash(fit_ids),
    )


def _trained(info: _Fit) -> _Fit:
    return _Fit(info.checkpoint, True, info.n, info.bads, info.test_cell_n, info.fit_hash)


def _constant_rate(labels: np.ndarray) -> float:
    return float(labels.mean()) if len(labels) else 0.0


def _starting_vendor(refitter, application_id, holdout, default_label) -> _VendorModel:
    """The holdout-free starting vendor model: Feature 002's fit on the non-holdout origination labels."""
    ids, labels = application_id[~holdout], default_label[~holdout]
    info = _fit_info(0, ids, labels, 0)
    ledger = refitter.fit(ids, labels)
    if ledger is None:
        ledger = pd.DataFrame({
            "application_id": application_id,
            "probability": np.full(len(application_id), _constant_rate(labels), dtype=np.float64),
            "reason_1": _REASON_FALLBACK[0],
            "reason_2": _REASON_FALLBACK[1],
            "reason_3": _REASON_FALLBACK[2],
        })
        return _VendorModel(ledger, info)
    return _VendorModel(ledger, _trained(info))


def _starting_lines(features, seed, application_id, holdout, default_label) -> _LineModel:
    """The challengers' starting fit: Feature 003's lines on the non-holdout origination labels."""
    ids, labels = application_id[~holdout], default_label[~holdout]
    info = _fit_info(0, ids, labels, 0)
    scores = models_regime.refit(features, ids, labels, seed)
    if scores is None:
        scores = pd.DataFrame({"application_id": application_id})
        for name in LINES:
            scores[name] = np.full(len(application_id), _constant_rate(labels), dtype=np.float64)
        return _LineModel(scores, info)
    return _LineModel(scores, _trained(info))


def _heldout_frame(regime, checkpoint, ids, label, vendor: _VendorModel, lines: _LineModel, hold) -> pd.DataFrame:
    data = {
        "regime": regime,
        "checkpoint": np.int64(checkpoint),
        "application_id": ids,
        "bad_6m": label,
        "vendor_probability": vendor.ledger["probability"].to_numpy(dtype=np.float64)[hold],
    }
    for name in LINES:
        data[name] = lines.scores[name].to_numpy(dtype=np.float64)[hold]
    return pd.DataFrame(data)


def _curve_rows(regime, checkpoint, frame: pd.DataFrame, vendor_fit: _Fit, line_fit: _Fit) -> list[dict]:
    label = frame["bad_6m"].to_numpy()
    vendor_probability = frame["vendor_probability"].to_numpy()
    two_class = _metrics.is_two_class(label)
    nan3 = (np.nan, np.nan, np.nan)
    vendor_auc, vendor_loss, vendor_brier = _metrics.scores(label, vendor_probability) if two_class else nan3
    rows = []
    for name in LINES:
        line_probability = frame[name].to_numpy()
        line_auc, line_loss, line_brier = _metrics.scores(label, line_probability) if two_class else nan3
        gap = _metrics.gap(label, vendor_probability, line_probability)
        g = gap if gap is not None else _metrics.Gap(*([np.nan] * 9))
        rows.append({
            "regime": regime, "checkpoint": checkpoint, "line": name,
            "holdout_n": len(label), "holdout_bads": int(label.sum()),
            "vendor_fit_n": vendor_fit.n, "vendor_fit_bads": vendor_fit.bads,
            "vendor_fit_test_cell_n": vendor_fit.test_cell_n,
            "line_fit_n": line_fit.n, "line_fit_bads": line_fit.bads,
            "line_fit_test_cell_n": line_fit.test_cell_n,
            "vendor_auc": vendor_auc, "line_auc": line_auc,
            "auc_gap": g.auc, "auc_gap_low": g.auc_low, "auc_gap_high": g.auc_high,
            "vendor_log_loss": vendor_loss, "line_log_loss": line_loss,
            "log_loss_gap": g.log_loss, "log_loss_gap_low": g.log_loss_low, "log_loss_gap_high": g.log_loss_high,
            "vendor_brier": vendor_brier, "line_brier": line_brier,
            "brier_gap": g.brier, "brier_gap_low": g.brier_low, "brier_gap_high": g.brier_high,
        })
    return rows


def _outcomes(application_id, origination, holdout, bad, decisions) -> pd.DataFrame:
    frames = []
    for regime in constants.REGIMES:
        for checkpoint in constants.CHECKPOINTS:
            state = decisions[checkpoint]
            observed = state["observed"]
            matured = pd.arrays.IntegerArray(bad.astype(np.int64), mask=~observed)
            frames.append(pd.DataFrame({
                "application_id": application_id,
                "checkpoint": np.int64(checkpoint),
                "regime": regime,
                "origination_month": origination,
                "holdout": holdout,
                "on_book": state["on_book"],
                "approved": state["approved"],
                "test_cell": state["test_cell"],
                "label_observed": observed,
                "matured_label": matured,
                "cutoff": np.where(state["on_book"], state["cutoff"], np.nan),
            }))
    return pd.concat(frames, ignore_index=True)


def _fits_table(start_vendor: _VendorModel, start_lines: _LineModel, checkpoint_fits) -> pd.DataFrame:
    rows = []
    for regime in constants.REGIMES:
        rows.append(_fit_record(regime, "vendor", start_vendor.fit, start_vendor.fit.trained))
        for info, vendor_trained, _ in checkpoint_fits.values():
            rows.append(_fit_record(regime, "vendor", info, vendor_trained))
        rows.append(_fit_record(regime, "challenger", start_lines.fit, start_lines.fit.trained))
        if regime == "data_owner":
            for info, _, lines_trained in checkpoint_fits.values():
                rows.append(_fit_record(regime, "challenger", info, lines_trained))
    frame = pd.DataFrame(rows, columns=_FIT_COLUMNS)
    frame["_arm"] = frame["arm"].map({"vendor": 0, "challenger": 1})
    frame["_regime"] = frame["regime"].map({name: i for i, name in enumerate(constants.REGIMES)})
    ordered = frame.sort_values(["_regime", "_arm", "checkpoint"], kind="mergesort")
    return ordered.drop(columns=["_arm", "_regime"]).reset_index(drop=True)


def _fit_record(regime: str, arm: str, info: _Fit, trained: bool) -> dict:
    return {
        "regime": regime,
        "checkpoint": np.int64(info.checkpoint),
        "arm": arm,
        "trained": bool(trained),
        "n": np.int64(info.n),
        "bads": np.int64(info.bads),
        "test_cell_n": np.int64(info.test_cell_n),
        "fit_ids_hash": info.fit_hash,
    }


def _place(run_dir: Path, features_hash: str, tables: dict, vendor: _VendorModel, lines: dict) -> Path:
    """Stage every file, then rename the directory onto the experiment path.

    Windows cannot rename onto an existing directory, so a previous run moves to a backup sibling
    first and returns only if the new rename fails.
    """
    final = rundir.experiment_dir(run_dir)
    parent = final.parent
    stage = parent / f".{final.name}.staging-{os.getpid()}"
    backup = parent / f".{final.name}.previous-{os.getpid()}"
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    stage.mkdir(parents=True)
    try:
        tables["outcomes"].to_parquet(stage / "outcomes.parquet", index=False)
        tables["fits"].to_parquet(stage / "fits.parquet", index=False)
        tables["heldout"].to_parquet(stage / "heldout_scores.parquet", index=False)
        tables["curves"].to_parquet(stage / "curves.parquet", index=False)
        (stage / "hypothesis.txt").write_text(constants.HYPOTHESIS, encoding="utf-8", newline="")
        for regime in constants.REGIMES:
            vendor_regime.write(stage / regime, vendor.ledger, features_hash, vendor.fit.fit_hash)
            models_regime.write(stage / regime, lines[regime].scores, features_hash, lines[regime].fit.fit_hash)
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
