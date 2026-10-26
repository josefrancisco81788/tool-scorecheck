"""Structural guards that are not locked checks."""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scorecheck
from scorecheck import logical_hash, rundir, schema
from scorecheck._streams import Streams

SRC = Path(scorecheck.__file__).parent


@pytest.mark.parametrize("spec", schema.ALL_TABLES, ids=lambda s: s.name)
def test_schema_kinds_match_hash_casts(spec):
    for name, kind in spec.columns:
        if kind is schema.Kind.ID:
            assert name.endswith("_id")
        elif kind in (schema.Kind.INT, schema.Kind.BOOL):
            assert name in logical_hash._INT_COLUMNS, name
        elif kind is schema.Kind.STR:
            assert name in logical_hash._STR_COLUMNS, name
        else:
            assert name not in logical_hash._INT_COLUMNS | logical_hash._STR_COLUMNS, name
            assert not name.endswith("_id"), name


def test_generators_only_built_in_streams():
    pattern = re.compile(r"default_rng|RandomState|np\.random\.seed|SeedSequence")
    offenders = [
        p.relative_to(SRC).as_posix()
        for p in SRC.rglob("*.py")
        if p.name != "_streams.py" and pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_stream_is_reproducible_and_independent_of_order():
    a = Streams(5, "panel")
    first = a("x").random(4)
    second = a("y").random(4)
    b = Streams(5, "panel")
    assert np.array_equal(b("y").random(4), second)
    assert np.array_equal(b("x").random(4), first)
    assert not np.array_equal(Streams(6, "panel")("x").random(4), first)


def test_stream_name_reuse_raises():
    streams = Streams(1, "panel")
    streams("x")
    with pytest.raises(ValueError):
        streams("x")


def test_conform_rejects_wrong_columns():
    with pytest.raises(schema.SchemaError):
        schema.conform(pd.DataFrame({"household_id": [1]}), schema.HOUSEHOLD)


def test_conform_casts_whole_floats_and_rejects_fractions():
    frame = pd.DataFrame({
        "account_id": [1.0, 2.0], "household_id": np.array([1, 1], dtype=np.int64), "shared": [1, 0],
    })
    out = schema.conform(frame, schema.EWALLET_ACCOUNT)
    assert out["account_id"].dtype == np.int64 and out["shared"].dtype == bool
    with pytest.raises(schema.SchemaError):
        schema.conform(frame.assign(account_id=[1.5, 2.0]), schema.EWALLET_ACCOUNT)


def _tables():
    one = np.array([1], dtype=np.int64)
    return {
        schema.HOUSEHOLD: pd.DataFrame({"household_id": one, "region": ["NCR"], "urban_rural": ["urban"],
                                        "income_band": ["low"], "remittance_receiver": [True]}),
        schema.PERSON: pd.DataFrame({"person_id": one, "household_id": one, "age_years": one * 30,
                                     "role": ["head"], "origination_month": one * 2}),
        schema.SIM: pd.DataFrame({"sim_id": one, "person_id": one, "prepaid": [True], "operator_slot": one}),
        schema.ELECTRICITY_ACCOUNT: pd.DataFrame({"account_id": one, "household_id": one, "shared": [False]}),
        schema.EWALLET_ACCOUNT: pd.DataFrame({"account_id": one, "household_id": one, "shared": [False]}),
        schema.MONTH_BEHAVIOUR: pd.DataFrame({"person_id": one, "month": one, "electricity_state": ["on_time"],
                                              "topup_amount": [1.0], "wallet_inflow": [1.0],
                                              "wallet_outflow": [1.0]}),
        schema.GROUND_TRUTH: pd.DataFrame({"person_id": one, "month": one, "ability": [0.0], "willingness": [0.0],
                                           "region_month_shock": [False], "post_origination_shock": [False],
                                           "vendor_signal": [0.0], "true_default": one * 0}),
    }


def test_write_run_replaces_existing_directory(tmp_path):
    run = rundir.RunConfig(seed=1, n_households=1)
    first = rundir.write_run(tmp_path, run, _tables())
    (first / "stale.txt").write_text("x", encoding="utf-8")
    second = rundir.write_run(tmp_path, run, _tables())
    assert second == first
    assert sorted(p.name for p in second.iterdir()) == sorted(rundir.PANEL_FILES)
    assert [p.name for p in tmp_path.iterdir()] == [run.run_id]
    assert rundir.read_run_config(second) == run
