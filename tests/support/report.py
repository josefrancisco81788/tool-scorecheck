"""Small hand-checkable frames for the Feature 005 report tests."""

import numpy as np
import pandas as pd

from scorecheck.report import _constants as c


def frame(vendor, line, bad, credit=None) -> pd.DataFrame:
    """A held-out frame where every challenger line carries the same scores."""
    n = len(vendor)
    data = {
        "application_id": np.arange(1, n + 1, dtype=np.int64),
        "bad_6m": np.asarray(bad, dtype=np.int64),
        "credit_amount": np.asarray(credit if credit is not None else [1000.0] * n, dtype=np.float64),
        "vendor_probability": np.asarray(vendor, dtype=np.float64),
    }
    for name in c.LINES:
        data[name] = np.asarray(line, dtype=np.float64)
    return pd.DataFrame(data)


# Eight applicants. Indexes 1 and 4 are bad. Loan amounts 1000, 2000, ... 8000.
EIGHT = frame(
    vendor=[0.01, 0.05, 0.20, 0.02, 0.20, 0.01, 0.30, 0.02],
    line=[0.01, 0.20, 0.02, 0.02, 0.20, 0.30, 0.01, 0.02],
    bad=[0, 1, 0, 0, 1, 0, 0, 0],
    credit=[1000.0 * (i + 1) for i in range(8)],
)
