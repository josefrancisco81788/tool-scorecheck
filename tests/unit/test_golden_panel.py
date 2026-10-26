import json
from pathlib import Path

from scorecheck.logical_hash import logical_hash
from support.runs import ALL_TABLE_NAMES, generate_run

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "panel.json"


def test_golden_panel(tmp_path):
    assert FIXTURE.is_file(), f"golden fixture missing at {FIXTURE}; run scripts/write_golden_panel.py"
    golden = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert 200 <= golden["n_households"] <= 500
    assert set(golden["hashes"]) == set(ALL_TABLE_NAMES)

    run = generate_run(golden["seed"], golden["n_households"], tmp_path)
    actual = {table: logical_hash(run[table]) for table in ALL_TABLE_NAMES}
    assert actual == golden["hashes"]
