"""The only column list for the eight tables. Every writer and reader conforms through here."""

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

import numpy as np
import pandas as pd


class Kind(Enum):
    ID = "id"
    INT = "int"
    BOOL = "bool"
    STR = "str"
    FLOAT = "float"


class SchemaError(ValueError):
    pass


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[tuple[str, Kind], ...]
    key: tuple[str, ...]

    @property
    def file_name(self) -> str:
        return f"{self.name}.parquet"

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.columns)


ID, INT, BOOL, STR, FLOAT = Kind.ID, Kind.INT, Kind.BOOL, Kind.STR, Kind.FLOAT

HOUSEHOLD = TableSpec(
    "household",
    (("household_id", ID), ("region", STR), ("urban_rural", STR), ("income_band", STR),
     ("remittance_receiver", BOOL)),
    ("household_id",),
)
PERSON = TableSpec(
    "person",
    (("person_id", ID), ("household_id", ID), ("age_years", INT), ("role", STR),
     ("origination_month", INT)),
    ("person_id",),
)
SIM = TableSpec(
    "sim",
    (("sim_id", ID), ("person_id", ID), ("prepaid", BOOL), ("operator_slot", INT)),
    ("sim_id",),
)
ELECTRICITY_ACCOUNT = TableSpec(
    "electricity_account", (("account_id", ID), ("household_id", ID), ("shared", BOOL)), ("account_id",)
)
EWALLET_ACCOUNT = TableSpec(
    "ewallet_account", (("account_id", ID), ("household_id", ID), ("shared", BOOL)), ("account_id",)
)
MONTH_BEHAVIOUR = TableSpec(
    "month_behaviour",
    (("person_id", ID), ("month", INT), ("electricity_state", STR), ("topup_amount", FLOAT),
     ("wallet_inflow", FLOAT), ("wallet_outflow", FLOAT)),
    ("person_id", "month"),
)
GROUND_TRUTH = TableSpec(
    "ground_truth",
    (("person_id", ID), ("month", INT), ("ability", FLOAT), ("willingness", FLOAT),
     ("region_month_shock", BOOL), ("post_origination_shock", BOOL), ("vendor_signal", FLOAT),
     ("true_default", INT)),
    ("person_id", "month"),
)

ELECTRICITY_STATES: tuple[str, ...] = (
    "on_time", "late_before_disconnection", "disconnected_restored_30d", "unpaid_past_30d",
)
DISCONNECTED_STATES: frozenset[str] = frozenset({"disconnected_restored_30d", "unpaid_past_30d"})

CORE_COLUMNS: tuple[tuple[str, Kind], ...] = (
    ("application_id", ID), ("person_id", ID), ("age_years", INT), ("income", FLOAT),
    ("dependents", INT), ("credit_amount", FLOAT), ("installment_to_income", FLOAT),
    ("utilization", FLOAT), ("open_credit_count", INT), ("delinquency_count_30", INT),
    ("delinquency_count_60", INT), ("delinquency_count_90", INT), ("history_months", INT),
    ("on_time_rate", FLOAT), ("payment_to_obligation_ratio", FLOAT), ("gender", STR),
    ("education", STR), ("marital_status", STR), ("region", STR), ("default_label", INT),
    ("label_observed", INT),
)
VENDOR_COLUMNS: tuple[tuple[str, Kind], ...] = (
    ("external_score_1", FLOAT), ("external_score_2", FLOAT), ("external_score_3", FLOAT),
)
ALT_DATA_COLUMNS: tuple[tuple[str, Kind], ...] = (
    ("sim_count", INT), ("prepaid_flag", INT), ("electricity_late_rate", FLOAT),
    ("electricity_disconnect_count", INT), ("remittance_inflow_mean", FLOAT),
    ("ewallet_net_flow_mean", FLOAT), ("shared_account_flag", INT),
)
APPLICATION_FEATURES = TableSpec(
    "application_features", CORE_COLUMNS + VENDOR_COLUMNS + ALT_DATA_COLUMNS, ("application_id",)
)

PANEL_TABLES: tuple[TableSpec, ...] = (
    HOUSEHOLD, PERSON, SIM, ELECTRICITY_ACCOUNT, EWALLET_ACCOUNT, MONTH_BEHAVIOUR, GROUND_TRUTH,
)
ALL_TABLES: tuple[TableSpec, ...] = PANEL_TABLES + (APPLICATION_FEATURES,)


def conform(frame: pd.DataFrame, spec: TableSpec, columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Exact column set in spec order, each column cast by its kind. Used on every write and read."""
    wanted = spec.column_names if columns is None else tuple(columns)
    kinds = dict(spec.columns)
    unknown = set(wanted) - set(kinds)
    if unknown:
        raise SchemaError(f"{spec.name}: no such columns {sorted(unknown)}")
    got = set(frame.columns)
    if got != set(wanted):
        raise SchemaError(
            f"{spec.name}: missing {sorted(set(wanted) - got)}, extra {sorted(got - set(wanted))}"
        )
    return pd.DataFrame(
        {name: _cast(spec.name, name, kinds[name], frame[name]) for name in wanted}
    ).reset_index(drop=True)


def _cast(table: str, name: str, kind: Kind, column: pd.Series) -> pd.Series:
    where = f"{table}.{name}"
    if kind is FLOAT:
        return pd.to_numeric(column, errors="raise").astype(np.float64)
    if column.isna().any():
        raise SchemaError(f"{where} has nulls")
    if kind is STR:
        return column.astype(str)
    if column.dtype == bool:
        return column.astype(np.int64) if kind in (ID, INT) else column
    numeric = pd.to_numeric(column, errors="raise").astype(np.float64)
    if not np.all(numeric == np.round(numeric)):
        raise SchemaError(f"{where} has non-whole values")
    if kind is BOOL:
        if not numeric.isin([0.0, 1.0]).all():
            raise SchemaError(f"{where} is not boolean")
        return numeric.astype(bool)
    return numeric.astype(np.int64)
