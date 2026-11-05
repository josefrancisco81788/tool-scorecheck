"""Experiment constants and the approval rule."""

import numpy as np

CHECKPOINTS: tuple[int, ...] = (4, 8, 12, 16, 20, 24)
REGIMES: tuple[str, ...] = ("vendor_only", "data_owner")
BAD_WINDOW_MONTHS = 6
APPROVAL_MAX_PROBABILITY = 0.0185
TEST_CELL_SHARE = 0.05
HOLDOUT_MODULUS = 5

HYPOTHESIS = (
    "The vendor leads early, and the gap narrows only in the regime where the data owner keeps the outcomes.\n"
    "This sentence is a hypothesis. It is not a target. The curves are the ones this seed produced.\n"
)


DECLINE_SHARE = 0.20


def approve(probability, cutoff: float = APPROVAL_MAX_PROBABILITY):
    """True where the vendor probability is strictly below the cutoff."""
    result = np.asarray(probability, dtype=np.float64) < cutoff
    return bool(result) if result.ndim == 0 else result
