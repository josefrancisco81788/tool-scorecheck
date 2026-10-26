"""Logical hash of a table, computed from values rather than Parquet bytes.

The cast lists are a frozen copy of the "Logical hash" section of checks/approved/feature-001.md.
A schema change does not edit them.
"""

import hashlib

import numpy as np
import pandas as pd

_INT_COLUMNS = frozenset({
    "month", "origination_month", "age_years", "operator_slot", "dependents", "open_credit_count",
    "delinquency_count_30", "delinquency_count_60", "delinquency_count_90", "history_months",
    "sim_count", "electricity_disconnect_count", "default_label", "label_observed", "true_default",
    "prepaid_flag", "shared_account_flag", "prepaid", "shared", "remittance_receiver",
    "region_month_shock", "post_origination_shock",
})
_STR_COLUMNS = frozenset({
    "region", "urban_rural", "income_band", "role", "electricity_state", "gender", "education",
    "marital_status",
})

NULL = "<NA>"


class LogicalHashError(ValueError):
    """No digest is produced for this table."""


def logical_hash(table: pd.DataFrame) -> str:
    return hashlib.sha256(logical_bytes(table)).hexdigest()


def logical_bytes(table: pd.DataFrame) -> bytes:
    names = sorted(str(c) for c in table.columns)
    cast = pd.DataFrame({name: _cast(name, table[name]) for name in names})
    ordered = cast.sort_values(names, na_position="last", kind="mergesort") if len(cast) else cast
    columns = [_render(name, ordered[name]) for name in names]
    lines = [",".join(_quote(n) for n in names)]
    lines.extend(",".join(fields) for fields in zip(*columns))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _cast(name: str, column: pd.Series) -> pd.Series:
    if name.endswith("_id"):
        if str(column.dtype) not in ("int64", "Int64") or column.isna().any():
            raise LogicalHashError(f"{name} is not a non-null int64 column")
        return column.astype(np.int64).reset_index(drop=True)
    if name in _INT_COLUMNS:
        return _to_int(name, column)
    if name in _STR_COLUMNS:
        values = column.astype(object)
        return pd.Series(
            [None if _is_null(v) else str(v) for v in values], dtype=object
        )
    return pd.to_numeric(column.astype(object), errors="raise").astype(np.float64).reset_index(drop=True)


def _to_int(name: str, column: pd.Series) -> pd.Series:
    if column.isna().any():
        raise LogicalHashError(f"{name} has a null in an int64 column")
    if column.dtype == bool or str(column.dtype) == "boolean":
        return column.astype(np.int64).reset_index(drop=True)
    numeric = pd.to_numeric(column.astype(object), errors="coerce").astype(np.float64)
    if numeric.isna().any() or not np.all(np.isfinite(numeric)) or not np.all(numeric == np.round(numeric)):
        raise LogicalHashError(f"{name} has a non-whole value in an int64 column")
    return numeric.astype(np.int64).reset_index(drop=True)


def _is_null(value: object) -> bool:
    return value is None or value is pd.NA or (isinstance(value, float) and np.isnan(value))


def _render(name: str, column: pd.Series) -> list[str]:
    if column.dtype == np.int64:
        return [str(v) for v in column.tolist()]
    if column.dtype == np.float64:
        return [_float_text(v) for v in column.tolist()]
    return [NULL if v is None else _quote(v) for v in column.tolist()]


def _float_text(value: float) -> str:
    if np.isnan(value):
        return NULL
    text = format(value, ".6f")
    return "0.000000" if text == "-0.000000" else text


def _quote(field: str) -> str:
    if "," in field or '"' in field or "\n" in field:
        return '"' + field.replace('"', '""') + '"'
    return field
