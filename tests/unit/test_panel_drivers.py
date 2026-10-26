import numpy as np

from scorecheck import config, panel
from scorecheck.logical_hash import logical_hash
from support import panel_assertions as pa
from support.runs import PanelRun


def _run(tmp_path_factory, label: str, **overrides) -> PanelRun:
    return PanelRun(panel.generate(config.SEED, 2000, tmp_path_factory.mktemp(label), **overrides))


def _labels(run: PanelRun) -> np.ndarray:
    return run.origination_rows["true_default"].to_numpy()


def _sorted_column(run: PanelRun, column: str) -> np.ndarray:
    return run["ground_truth"].sort_values(["person_id", "month"])[column].to_numpy()


def test_driver_signs(run_2000):
    pa.assert_driver_signs(run_2000)


def test_default_class_counts(run_2000):
    pa.assert_default_class_counts(run_2000)


def test_ability_rank_residual(run_2000):
    pa.assert_ability_rank_residual(run_2000)


def test_willingness_rank_residual(run_2000):
    pa.assert_willingness_rank_residual(run_2000)


def test_vendor_signal_rank_residual(run_2000):
    pa.assert_vendor_signal_rank_residual(run_2000)


def test_calendar_split(run_2000):
    pa.assert_calendar_split(run_2000)


def test_driver_weights_nonzero():
    assert hasattr(config, "ability_default_weight")
    assert hasattr(config, "willingness_default_weight")
    assert config.ability_default_weight != 0
    assert config.willingness_default_weight != 0


def _assert_zero_weight_changes_default(weight, base, tmp_path_factory, monkeypatch) -> None:
    monkeypatch.setattr(config, weight, 0.0)
    zeroed = _run(tmp_path_factory, f"zero-{weight}")
    assert np.array_equal(zeroed.origination_rows["person_id"], base.origination_rows["person_id"])
    assert (_labels(zeroed) != _labels(base)).sum() >= 1


def test_zero_willingness_weight_changes_default(run_2000, tmp_path_factory, monkeypatch):
    _assert_zero_weight_changes_default("willingness_default_weight", run_2000, tmp_path_factory, monkeypatch)


def test_zero_ability_weight_changes_default(run_2000, tmp_path_factory, monkeypatch):
    _assert_zero_weight_changes_default("ability_default_weight", run_2000, tmp_path_factory, monkeypatch)


def _assert_override_contract(trait: str, prefix: str, base: PanelRun, tmp_path_factory) -> None:
    keyword = f"{trait}_override"
    n_rows = len(base["ground_truth"])

    hashed = pa.override_values(prefix, base["ground_truth"])
    hashed_run = _run(tmp_path_factory, f"{trait}-hashed", **{keyword: hashed})
    assert np.array_equal(_sorted_column(hashed_run, trait), np.asarray(hashed, dtype=np.float64))
    assert np.array_equal(hashed_run.origination_rows["person_id"], base.origination_rows["person_id"])
    assert (_labels(hashed_run) != _labels(base)).sum() >= 1

    low = _run(tmp_path_factory, f"{trait}-minus3", **{keyword: [-3.0] * n_rows})
    high = _run(tmp_path_factory, f"{trait}-plus3", **{keyword: [3.0] * n_rows})
    assert (_labels(low) == 1).sum() > (_labels(high) == 1).sum()

    round_trip = _run(tmp_path_factory, f"{trait}-round-trip", **{keyword: _sorted_column(base, trait)})
    assert logical_hash(round_trip["ground_truth"]) == logical_hash(base["ground_truth"])


def test_willingness_override_changes_default(run_2000, tmp_path_factory):
    _assert_override_contract("willingness", "w", run_2000, tmp_path_factory)


def test_ability_override_changes_default(run_2000, tmp_path_factory):
    _assert_override_contract("ability", "a", run_2000, tmp_path_factory)
