import hashlib
import json

from scorecheck import config, rundir


def test_run_id():
    assert rundir.run_id(7, 300) == "78dc4a1737d02cc1"
    expected = hashlib.sha256(f"{config.SEED}|300|24".encode("utf-8")).hexdigest()[:16]
    assert rundir.run_id(config.SEED, 300) == expected
