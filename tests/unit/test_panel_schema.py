import pandas as pd

DETAIL_COLUMNS = {
    "household": {"household_id", "region", "urban_rural", "income_band", "remittance_receiver"},
    "person": {"person_id", "household_id", "age_years", "role", "origination_month"},
    "sim": {"sim_id", "person_id", "prepaid", "operator_slot"},
    "electricity_account": {"account_id", "household_id", "shared"},
    "ewallet_account": {"account_id", "household_id", "shared"},
    "month_behaviour": {"person_id", "month", "electricity_state", "topup_amount", "wallet_inflow", "wallet_outflow"},
}
STATES = {"on_time", "late_before_disconnection", "disconnected_restored_30d", "unpaid_past_30d"}


def test_detail_columns(run_300):
    for table, columns in DETAIL_COLUMNS.items():
        assert set(run_300[table].columns) == columns, table


def test_unique_keys(run_300):
    household = run_300["household"]
    assert len(household) == 300
    for table, key in (
        ("household", "household_id"), ("person", "person_id"), ("sim", "sim_id"),
        ("electricity_account", "account_id"), ("ewallet_account", "account_id"),
    ):
        assert run_300[table][key].duplicated().sum() == 0, table
    assert set(household["household_id"]) <= set(run_300["person"]["household_id"])


def test_foreign_keys(run_300):
    households = set(run_300["household"]["household_id"])
    persons = set(run_300["person"]["person_id"])
    for table in ("person", "electricity_account", "ewallet_account"):
        assert (~run_300[table]["household_id"].isin(households)).sum() == 0, table
    for table in ("sim", "month_behaviour", "ground_truth"):
        assert (~run_300[table]["person_id"].isin(persons)).sum() == 0, table


def test_origination_month_range(run_300):
    months = run_300["person"]["origination_month"]
    assert pd.api.types.is_integer_dtype(months)
    assert months.between(2, 18).all()


def test_month_behaviour_grain(run_300):
    mb = run_300["month_behaviour"]
    assert mb.duplicated(["person_id", "month"]).sum() == 0
    assert pd.api.types.is_integer_dtype(mb["month"])
    assert mb["month"].between(1, 24).all()
    assert len(mb) == 24 * len(run_300["person"])


def test_electricity_states(run_300):
    assert (~run_300["month_behaviour"]["electricity_state"].isin(STATES)).sum() == 0
