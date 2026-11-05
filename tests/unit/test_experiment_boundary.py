"""E10: vendor refits stay inside vendor/, challenger refits inside models/, Features 002 and 003 untouched."""

import hashlib
from pathlib import Path

import pytest

import scorecheck
from support.experiment import prepare
from support.vendor import copied_run

SRC = Path(scorecheck.__file__).parent
ROOT = SRC.parents[1]


def _snapshot(directory: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir())}


def test_no_private_import_outside_vendor():
    needle = "scorecheck.vendor" + "._private"
    for path in SRC.rglob("*.py"):
        if "vendor" in path.relative_to(SRC).parts[:1]:
            continue
        assert needle not in path.read_text(encoding="utf-8"), path
    for path in SRC.rglob("*.py"):
        if path.relative_to(SRC).parts[0] == "vendor":
            continue
        text = path.read_text(encoding="utf-8")
        assert "from scorecheck.vendor import _private" not in text, path
        assert "vendor._private" not in text, path


def test_models_package_does_not_name_the_vendor_ledger_file():
    for path in (SRC / "models").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "ledger.parquet" not in text, path
        assert "pred_contrib" not in text, path


def test_experiment_package_does_not_open_either_earlier_output():
    for path in (SRC / "experiment").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "ledger.parquet" not in text, path
        assert "scores.parquet" not in text.replace("heldout_scores.parquet", ""), path
        assert "scores_dir" not in text, path
        assert "models.line" not in text, path
        assert "vendor.score" not in text, path


def test_public_surfaces_unchanged():
    from scorecheck import models, vendor

    assert vendor.__all__ == [
        "publish", "score", "VendorDecision", "ReasonCode", "LedgerMissing", "StaleLedger", "UnknownApplicant",
    ]
    assert models.__all__ == [
        "publish", "line", "ChallengerLines", "ScoresMissing", "StaleScores", "UnknownApplicant",
    ]


def test_run_leaves_the_vendor_and_models_directories_alone(run_300, tmp_path, monkeypatch):
    from scorecheck import experiment, models, vendor
    from scorecheck.models import regime as models_regime  # noqa: F401  (import before spies)

    run_dir = copied_run(run_300.run_dir, tmp_path)
    vendor.publish(run_dir)
    models.publish(run_dir)
    vendor_dir = run_dir.parent.with_name("vendor") / run_dir.name
    models_dir = run_dir.parent.with_name("models") / run_dir.name
    before_vendor = _snapshot(vendor_dir)
    before_models = _snapshot(models_dir)
    before_panel = _snapshot(run_dir)

    def refuse(name):
        def inner(*args, **kwargs):
            raise AssertionError(f"experiment.run called {name}")

        return inner

    monkeypatch.setattr(vendor, "score", refuse("vendor.score"))
    monkeypatch.setattr(vendor, "publish", refuse("vendor.publish"))
    monkeypatch.setattr(models, "line", refuse("models.line"))
    monkeypatch.setattr(models, "publish", refuse("models.publish"))

    out = experiment.run(run_dir)
    assert out == run_dir.parent.with_name("experiment") / run_dir.name
    assert _snapshot(vendor_dir) == before_vendor
    assert _snapshot(models_dir) == before_models
    assert _snapshot(run_dir) == before_panel
    assert sorted(p.name for p in vendor_dir.iterdir()) == ["bind.json", "ledger.parquet"]
    assert sorted(p.name for p in models_dir.iterdir()) == ["bind.json", "scores.parquet"]


def test_run_does_not_need_the_shadow_scores(run_300, tmp_path):
    prepared = prepare(run_300.run_dir, tmp_path)
    assert not (prepared.run_dir.parent.with_name("models")).exists()


def test_output_layout(experiment_2000):
    root = experiment_2000.exp_dir
    assert sorted(p.name for p in root.iterdir()) == [
        "curves.parquet", "data_owner", "fits.parquet", "heldout_scores.parquet", "hypothesis.txt",
        "outcomes.parquet", "vendor_only",
    ]
    for regime in ("vendor_only", "data_owner"):
        assert sorted(p.name for p in (root / regime).iterdir()) == ["bind.json", "challengers", "ledger.parquet"]
        assert sorted(p.name for p in (root / regime / "challengers").iterdir()) == ["bind.json", "scores.parquet"]
    assert [p.name for p in root.parent.iterdir()] == [root.name]


def test_run_twice_replaces_the_directory(run_300, tmp_path):
    from scorecheck import experiment

    prepared = prepare(run_300.run_dir, tmp_path)
    (prepared.exp_dir / "stale.txt").write_text("x", encoding="utf-8")
    again = experiment.run(prepared.run_dir)
    assert again == prepared.exp_dir
    assert not (again / "stale.txt").exists()
    assert [p.name for p in again.parent.iterdir()] == [again.name]


def test_run_without_a_vendor_ledger_raises(run_300, tmp_path):
    from scorecheck import experiment, vendor

    run_dir = copied_run(run_300.run_dir, tmp_path)
    with pytest.raises(vendor.LedgerMissing):
        experiment.run(run_dir)
    assert not run_dir.parent.with_name("experiment").exists()
