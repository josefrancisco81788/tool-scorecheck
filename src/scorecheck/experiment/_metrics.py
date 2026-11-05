"""Holdout metrics, the vendor-minus-challenger gap, and its 95% interval."""

import math
from typing import NamedTuple

import numpy as np
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

Z_95 = 1.96


class Gap(NamedTuple):
    auc: float
    log_loss: float
    brier: float
    auc_low: float
    auc_high: float
    log_loss_low: float
    log_loss_high: float
    brier_low: float
    brier_high: float


def is_two_class(labels) -> bool:
    return np.unique(np.asarray(labels)).size == 2


def scores(labels, probability) -> tuple[float, float, float]:
    """AUC, log loss, and Brier score. The caller checks the labels have both classes."""
    labels = np.asarray(labels).astype(np.int64)
    probability = np.asarray(probability, dtype=np.float64)
    return (
        float(roc_auc_score(labels, probability)),
        float(log_loss(labels, probability, labels=[0, 1])),
        float(brier_score_loss(labels, probability)),
    )


def gap(labels, vendor_probability, line_probability) -> Gap | None:
    """Vendor minus challenger on AUC, log loss, and Brier, each with a 95% interval.

    The AUC interval is the paired DeLong interval. The log-loss and Brier intervals are normal
    intervals on the per-applicant paired differences. Returns None when the labels hold one class.
    """
    labels = np.asarray(labels).astype(np.int64)
    if not is_two_class(labels):
        return None
    vendor = np.asarray(vendor_probability, dtype=np.float64)
    line = np.asarray(line_probability, dtype=np.float64)
    vendor_auc, vendor_loss, vendor_brier = scores(labels, vendor)
    line_auc, line_loss, line_brier = scores(labels, line)
    auc_gap = vendor_auc - line_auc
    loss_gap = vendor_loss - line_loss
    brier_gap = vendor_brier - line_brier
    auc_half = Z_95 * math.sqrt(delong_gap_variance(labels, vendor, line))
    loss_half = Z_95 * _standard_error(_row_log_loss(labels, vendor) - _row_log_loss(labels, line))
    brier_half = Z_95 * _standard_error((vendor - labels) ** 2 - (line - labels) ** 2)
    return Gap(
        auc_gap, loss_gap, brier_gap,
        auc_gap - auc_half, auc_gap + auc_half,
        loss_gap - loss_half, loss_gap + loss_half,
        brier_gap - brier_half, brier_gap + brier_half,
    )


def _row_log_loss(labels: np.ndarray, probability: np.ndarray) -> np.ndarray:
    eps = np.finfo(np.float64).eps
    clipped = np.clip(probability, eps, 1.0 - eps)
    return -(labels * np.log(clipped) + (1 - labels) * np.log(1.0 - clipped))


def _standard_error(differences: np.ndarray) -> float:
    if len(differences) < 2:
        return math.nan
    return float(differences.std(ddof=1) / math.sqrt(len(differences)))


def _midrank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ordered = values[order]
    start = np.concatenate(([True], ordered[1:] != ordered[:-1]))
    first = np.flatnonzero(start)
    last = np.concatenate((first[1:], [len(values)]))
    average = 0.5 * (first + last - 1) + 1.0
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.repeat(average, last - first)
    return ranks


def _placements(scores_: np.ndarray, positive: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """DeLong structural components: for each positive the share of negatives it beats, and for
    each negative the share of positives that beat it. Ties count one half."""
    m = int(positive.sum())
    n = len(scores_) - m
    on_positive = scores_[positive]
    on_negative = scores_[~positive]
    overall = _midrank(scores_)
    beats = (overall[positive] - _midrank(on_positive)) / n
    beaten_by = 1.0 - (overall[~positive] - _midrank(on_negative)) / m
    return beats, beaten_by


def delong_gap_variance(labels, a, b) -> float:
    """Variance of AUC(a) minus AUC(b) on the same applicants (Sun and Xu fast midrank method)."""
    labels = np.asarray(labels).astype(np.int64)
    positive = labels == 1
    m = int(positive.sum())
    n = len(labels) - m
    if m < 2 or n < 2:
        return math.nan
    a10, a01 = _placements(np.asarray(a, dtype=np.float64), positive)
    b10, b01 = _placements(np.asarray(b, dtype=np.float64), positive)
    return float(np.var(a10 - b10, ddof=1) / m + np.var(a01 - b01, ddof=1) / n)
