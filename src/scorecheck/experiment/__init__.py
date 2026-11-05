"""Outcomes-ownership experiment: who keeps the repayment outcomes, and what that does to the gap."""

from scorecheck.experiment._constants import (
    APPROVAL_MAX_PROBABILITY,
    BAD_WINDOW_MONTHS,
    CHECKPOINTS,
    HYPOTHESIS,
    REGIMES,
    TEST_CELL_SHARE,
    approve,
)
from scorecheck.experiment._metrics import Gap, gap
from scorecheck.experiment._run import run

__all__ = [
    "run",
    "approve",
    "gap",
    "Gap",
    "CHECKPOINTS",
    "REGIMES",
    "APPROVAL_MAX_PROBABILITY",
    "TEST_CELL_SHARE",
    "BAD_WINDOW_MONTHS",
    "HYPOTHESIS",
]
