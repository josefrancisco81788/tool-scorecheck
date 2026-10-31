"""Advisory bounds on a two-class vendor ledger. Proves no locked check."""

from scorecheck.vendor import ReasonCode, score
from support.vendor import copied_run, read_features, two_class

TOKENS = {"credit_stress", "capacity", "thin_file", "alt_activity", "private_factor"}


def test_vendor_bounds(run_300, tmp_path):
    from scorecheck.vendor import publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    publish(run_dir)
    for application_id in read_features(run_dir)["application_id"].tolist():
        probability, reason_1, reason_2, reason_3 = score(run_dir, int(application_id))
        assert 0.0 <= float(probability) <= 1.0
        codes = (reason_1, reason_2, reason_3)
        assert len(set(codes)) == 3
        assert all(isinstance(code, ReasonCode) for code in codes)
        assert {code.value for code in codes} <= TOKENS
