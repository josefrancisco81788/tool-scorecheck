"""Black-box vendor score. Downstream code gets a probability and three reason codes."""

import json
from enum import Enum
from pathlib import Path
from typing import Mapping, NamedTuple

import pandas as pd

from scorecheck.schema import SchemaError
from scorecheck.vendor import _private

__all__ = [
    "publish",
    "score",
    "VendorDecision",
    "ReasonCode",
    "LedgerMissing",
    "StaleLedger",
    "UnknownApplicant",
]


class ReasonCode(str, Enum):
    credit_stress = "credit_stress"
    capacity = "capacity"
    thin_file = "thin_file"
    alt_activity = "alt_activity"
    private_factor = "private_factor"


class VendorDecision(NamedTuple):
    probability: float
    reason_1: ReasonCode
    reason_2: ReasonCode
    reason_3: ReasonCode


class LedgerMissing(Exception):
    pass


class StaleLedger(Exception):
    pass


class UnknownApplicant(Exception):
    pass


COLUMN_GROUPS = {
    "utilization": "credit_stress",
    "open_credit_count": "credit_stress",
    "delinquency_count_30": "credit_stress",
    "delinquency_count_60": "credit_stress",
    "delinquency_count_90": "credit_stress",
    "on_time_rate": "credit_stress",
    "income": "capacity",
    "dependents": "capacity",
    "credit_amount": "capacity",
    "installment_to_income": "capacity",
    "payment_to_obligation_ratio": "capacity",
    "history_months": "thin_file",
    "sim_count": "alt_activity",
    "prepaid_flag": "alt_activity",
    "electricity_late_rate": "alt_activity",
    "electricity_disconnect_count": "alt_activity",
    "remittance_inflow_mean": "alt_activity",
    "ewallet_net_flow_mean": "alt_activity",
    "shared_account_flag": "alt_activity",
    "private_factor": "private_factor",
}

_TIE_ORDER = ("credit_stress", "capacity", "thin_file", "alt_activity", "private_factor")
_ONE_CLASS = (ReasonCode.credit_stress, ReasonCode.capacity, ReasonCode.thin_file)


def rank_reasons(contributions: Mapping[str, float]) -> tuple[ReasonCode, ReasonCode, ReasonCode]:
    if set(contributions) != set(COLUMN_GROUPS):
        raise SchemaError("contribution names do not match COLUMN_GROUPS")
    weights = {token: 0.0 for token in _TIE_ORDER}
    for name, value in contributions.items():
        weights[COLUMN_GROUPS[name]] += abs(float(value))
    ranked = sorted(_TIE_ORDER, key=lambda token: (-weights[token], _TIE_ORDER.index(token)))
    return tuple(ReasonCode(token) for token in ranked[:3])


def publish(run_dir: Path | str) -> None:
    table = _private.assemble(Path(run_dir), COLUMN_GROUPS)
    if table.single_class:
        probability = _private.one_class_probability(table)
        reasons = [_ONE_CLASS for _ in table.application_id]
    else:
        probability, contributions = _private.fit(table)
        reasons = [rank_reasons(row) for row in contributions]
    _private.place(Path(run_dir), table.features_hash, table.application_id, probability, reasons)


def score(run_dir: Path | str, application_id: int) -> VendorDecision:
    run_dir = Path(run_dir)
    directory = _private.ledger_dir(run_dir)
    ledger_file = directory / "ledger.parquet"
    bind_file = directory / "bind.json"
    if not ledger_file.is_file() or not bind_file.is_file():
        raise LedgerMissing(directory)
    bound = json.loads(bind_file.read_text(encoding="utf-8"))["features_hash"]
    if bound != _private.features_hash(run_dir):
        raise StaleLedger(run_dir)
    ledger = pd.read_parquet(ledger_file)
    hit = ledger.loc[ledger["application_id"] == application_id]
    if hit.empty:
        raise UnknownApplicant(application_id)
    row = hit.iloc[0]
    return VendorDecision(
        float(row["probability"]),
        ReasonCode(str(row["reason_1"])),
        ReasonCode(str(row["reason_2"])),
        ReasonCode(str(row["reason_3"])),
    )
