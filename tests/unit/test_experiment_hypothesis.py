"""E8: the hypothesis is written as a hypothesis and no code reads it."""

from pathlib import Path

import scorecheck

SRC = Path(scorecheck.__file__).parent
TEXT = (
    "The vendor leads early, and the gap narrows only in the regime where the data owner keeps the outcomes.\n"
    "This sentence is a hypothesis. It is not a target. The curves are the ones this seed produced.\n"
)


def test_hypothesis_file(experiment_2000):
    raw = (experiment_2000.exp_dir / "hypothesis.txt").read_bytes()
    assert raw == TEXT.encode("utf-8")
    assert raw.endswith(b"\n")


def test_constant():
    from scorecheck import experiment

    assert experiment.HYPOTHESIS == TEXT


def test_no_source_reads_the_hypothesis_file():
    readers = ("read_text", "read_bytes", "open(", "read_csv", "read_parquet", "read(")
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if path.parent.name != "experiment":
            assert "hypothesis.txt" not in text, path.name
        for number, line in enumerate(text.splitlines(), start=1):
            if "hypothesis.txt" in line:
                assert not any(reader in line for reader in readers), (path.name, number)
