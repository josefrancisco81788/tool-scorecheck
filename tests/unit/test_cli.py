import subprocess
import sys
from pathlib import Path

import pytest

from scorecheck import cli, config, explain, rundir

STAGES = ["vendor", "models", "experiment", "report", "validate", "explain"]
BAD_SCALES = ["huge", "DEFAULT", "Full", "", "50000"]


def _listing(root: Path) -> list[tuple[str, int]]:
    return sorted((p.relative_to(root).as_posix(), p.stat().st_size if p.is_file() else -1) for p in root.rglob("*"))


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "scorecheck", *args], cwd=cwd, capture_output=True, text=True, timeout=120
    )


def test_scale_flag():
    assert cli.parse_args([]).n_households == config.SCALE_DEFAULT
    assert cli.parse_args([]).scale == "default"
    assert cli.parse_args(["--scale", "default"]).n_households == config.SCALE_DEFAULT
    assert cli.parse_args(["--scale", "full"]).n_households == config.SCALE_FULL


@pytest.mark.parametrize("value", BAD_SCALES)
def test_bad_scale_writes_nothing(value, tmp_path):
    absent = tmp_path / "absent"
    absent.mkdir()
    result = _run_cli(absent, "--scale", value)
    assert result.returncode != 0
    assert not (absent / "data" / "processed").exists()
    assert result.stdout == ""

    present = tmp_path / "present"
    nested = present / "data" / "processed" / "earlier-run" / "deeper"
    nested.mkdir(parents=True)
    (nested / "kept.parquet").write_bytes(b"x" * 17)
    (present / "data" / "processed" / "note.txt").write_text("keep", encoding="utf-8")
    before = _listing(present / "data" / "processed")
    result = _run_cli(present, "--scale", value)
    assert result.returncode != 0
    assert _listing(present / "data" / "processed") == before


def test_missing_scale_value_exits_nonzero(tmp_path):
    result = _run_cli(tmp_path, "--scale")
    assert result.returncode != 0
    assert not (tmp_path / "data").exists()


def test_draft_raises():
    with pytest.raises(RuntimeError):
        explain.draft()


def test_command_order(tmp_path, monkeypatch):
    from scorecheck import features, models, panel, vendor

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "SCALES", {"default": 200, "full": 400})
    order = []
    real_generate = panel.generate
    real_features = features.from_panel
    real_publish = vendor.publish
    real_models = models.publish

    def generate(*args, **kwargs):
        order.append("panel.generate")
        return real_generate(*args, **kwargs)

    def from_panel(*args, **kwargs):
        order.append("features.from_panel")
        return real_features(*args, **kwargs)

    def publish(*args, **kwargs):
        order.append("vendor.publish")
        return real_publish(*args, **kwargs)

    def models_publish(*args, **kwargs):
        order.append("models.publish")
        return real_models(*args, **kwargs)

    monkeypatch.setattr(panel, "generate", generate)
    monkeypatch.setattr(features, "from_panel", from_panel)
    monkeypatch.setattr(vendor, "publish", publish)
    monkeypatch.setattr(models, "publish", models_publish)
    assert cli.main([]) == 0
    assert order == ["panel.generate", "features.from_panel", "vendor.publish", "models.publish"]


def test_main_prints_banner_then_stages(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "SCALES", {"default": 200, "full": 400})

    def refuse(*args, **kwargs):
        raise AssertionError("the CLI called explain.draft")

    monkeypatch.setattr(explain, "draft", refuse)
    assert cli.main([]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [config.BANNERS["default"], *STAGES]
    run_dir = tmp_path / "data" / "processed" / rundir.run_id(config.SEED, 200)
    assert [p.name for p in (tmp_path / "data" / "processed").iterdir()] == [run_dir.name]
    assert (run_dir / "application_features.parquet").is_file()
