from pathlib import Path

from scorecheck import config
from support.runs import generate_run
from support.vendor import ledger_dir

ROOT = Path(__file__).resolve().parents[2]
TOKENS = {"credit_stress", "capacity", "thin_file", "alt_activity", "private_factor"}


def test_public_surface():
    from scorecheck import vendor

    assert vendor.__all__ == [
        "publish", "score", "VendorDecision", "ReasonCode", "LedgerMissing", "StaleLedger", "UnknownApplicant",
    ]
    assert {member.value for member in vendor.ReasonCode} == TOKENS
    assert len(list(vendor.ReasonCode)) == 5
    assert not hasattr(vendor, "Booster")
    assert not hasattr(vendor, "booster")


def test_no_private_import_outside_vendor():
    needle = "scorecheck.vendor" + "._private"
    vendor_root = (ROOT / "src" / "scorecheck" / "vendor").resolve()
    offenders = []
    for base in ("src", "tests", "scripts"):
        for path in (ROOT / base).rglob("*.py"):
            resolved = path.resolve()
            if resolved.parent == vendor_root or vendor_root in resolved.parents:
                continue
            if needle in path.read_text(encoding="utf-8"):
                offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_generate_run_stops_at_from_panel(tmp_path, monkeypatch):
    from scorecheck import vendor

    def refuse(*args, **kwargs):
        raise AssertionError("generate_run called vendor.publish")

    monkeypatch.setattr(vendor, "publish", refuse)
    run = generate_run(config.SEED, 300, tmp_path / "processed")
    assert not ledger_dir(run.run_dir).exists()


def test_golden_script_stops_at_from_panel():
    text = (ROOT / "scripts" / "write_golden_panel.py").read_text(encoding="utf-8")
    assert "features.from_panel" in text
    assert "vendor.publish" not in text
    assert "scorecheck.vendor" not in text
