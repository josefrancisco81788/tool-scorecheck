"""R8: two runs with the same seed on the same machine give the same report tables."""

import os
import subprocess
import sys

from scorecheck.report import _constants as c

SCRIPT = """
import sys
from pathlib import Path
from scorecheck import config, experiment, features, panel, report, vendor

root = Path(sys.argv[1])
run_dir = panel.generate(config.SEED, 300, root / "processed")
features.from_panel(run_dir)
vendor.publish(run_dir)
experiment.run(run_dir)
print(report.run(run_dir))
"""


def _run(root, hash_seed: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT, str(root)],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PYTHONHASHSEED": hash_seed},
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_two_runs_give_equal_report_files(tmp_path):
    first = _run(tmp_path / "a", "1")
    second = _run(tmp_path / "b", "2")
    for name in c.FILES:
        a = open(f"{first}/{name}", "rb").read()
        b = open(f"{second}/{name}", "rb").read()
        assert a == b, name
        assert len(a) > 0, name
