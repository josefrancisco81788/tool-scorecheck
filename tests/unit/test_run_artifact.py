import hashlib
import json

from scorecheck import config, panel, rundir

PANEL_FILES = {
    "household.parquet", "person.parquet", "sim.parquet", "electricity_account.parquet",
    "ewallet_account.parquet", "month_behaviour.parquet", "ground_truth.parquet", "run_config.json",
}


def test_run_id():
    assert rundir.run_id(7, 300) == "78dc4a1737d02cc1"
    expected = hashlib.sha256(f"{config.SEED}|300|24".encode("utf-8")).hexdigest()[:16]
    assert rundir.run_id(config.SEED, 300) == expected


def test_generate_writes_only_panel(tmp_path):
    run_dir = panel.generate(config.SEED, 300, tmp_path)
    assert run_dir == tmp_path / rundir.run_id(config.SEED, 300)
    assert [p.name for p in tmp_path.iterdir()] == [run_dir.name]
    assert {p.name for p in run_dir.iterdir()} == PANEL_FILES
    assert all(p.is_file() for p in run_dir.iterdir())


def test_generate_twice_into_same_directory(tmp_path):
    first = panel.generate(config.SEED, 300, tmp_path)
    second = panel.generate(config.SEED, 300, tmp_path)
    assert first == second
    assert {p.name for p in second.iterdir()} == PANEL_FILES


def test_run_config(run_300):
    data = json.loads((run_300.run_dir / "run_config.json").read_text(encoding="utf-8"))
    assert set(data) == {"seed", "n_households", "scale", "n_months"}
    assert data["seed"] == config.SEED
    assert data["n_households"] == 300
    assert data["n_months"] == 24
    assert isinstance(data["scale"], str)
