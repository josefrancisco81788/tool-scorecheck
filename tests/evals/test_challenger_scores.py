"""Advisory bounds on a two-class challenger file. Proves no locked check."""

import numpy as np

from support.models import read_scores
from support.vendor import copied_run, two_class

FAMILIES = ("lightgbm", "xgboost", "hist_gradient_boosting", "scorecard_probability")
PROBABILITIES = FAMILIES + (
    "vendor_probability",
    "lightgbm_monotone",
    "xgboost_monotone",
    "hist_gradient_boosting_monotone",
)


def test_challenger_bounds(run_300, tmp_path):
    from scorecheck.models import publish
    from scorecheck.vendor import publish as vendor_publish

    run_dir = copied_run(run_300.run_dir, tmp_path)
    two_class(run_dir)
    vendor_publish(run_dir)
    publish(run_dir)
    frame = read_scores(run_dir)
    for name in FAMILIES:
        assert name in frame.columns
    for name in PROBABILITIES:
        values = frame[name].to_numpy(dtype=np.float64)
        assert np.isfinite(values).all()
        assert np.all((values >= 0.0) & (values <= 1.0))
