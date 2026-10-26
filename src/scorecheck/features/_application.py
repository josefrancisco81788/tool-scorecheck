import numpy as np
import pandas as pd

from scorecheck import schema
from scorecheck._streams import Streams
from scorecheck.panel import OriginationView

BAND_BASE_INCOME = {"low": 9_000.0, "lower_middle": 18_000.0, "middle": 35_000.0, "upper_middle": 70_000.0}
LOAN_TERMS_MONTHS = np.array([6, 12, 18, 24])
GENDERS = ("female", "male")
EDUCATION = ("elementary", "high_school", "college", "postgraduate")
EDUCATION_SHARES = (0.20, 0.45, 0.30, 0.05)
MARITAL_STATUS = ("single", "married", "widowed", "separated")
MARITAL_SHARES = (0.40, 0.48, 0.06, 0.06)


def _poisson(rng: np.random.Generator, lam: np.ndarray) -> np.ndarray:
    """One uniform per person, inverted through the Poisson CDF.

    Generator.poisson consumes a lambda-dependent number of uniforms, so one person's rate would
    shift every later person's draw.
    """
    u = rng.random(len(lam))
    k = np.zeros(len(lam), dtype=np.int64)
    pmf = np.exp(-lam)
    cdf = pmf.copy()
    active = (u > cdf) & (pmf > 0)
    while active.any():
        k[active] += 1
        pmf[active] *= lam[active] / k[active]
        cdf[active] += pmf[active]
        active = (u > cdf) & (pmf > 0)
    return k


def _alternative_data(view: OriginationView) -> pd.DataFrame:
    person_ids = view.person["person_id"]
    before = view.behaviour_before.assign(
        late=lambda f: f["electricity_state"] != "on_time",
        disconnected=lambda f: f["electricity_state"].isin(schema.DISCONNECTED_STATES),
        net_flow=lambda f: f["wallet_inflow"] - f["wallet_outflow"],
    ).groupby("person_id")
    sims = view.sim.sort_values("sim_id")
    shared = (
        pd.concat([view.electricity_account, view.ewallet_account])
        .groupby("household_id")["shared"].any()
    )
    columns = {
        "sim_count": sims.groupby("person_id").size(),
        "prepaid_flag": sims.drop_duplicates("person_id").set_index("person_id")["prepaid"].astype(np.int64),
        "electricity_late_rate": before["late"].mean(),
        "electricity_disconnect_count": before["disconnected"].sum(),
        "remittance_inflow_mean": before["wallet_inflow"].mean(),
        "ewallet_net_flow_mean": before["net_flow"].mean(),
        "shared_account_flag": view.person.set_index("person_id")["household_id"].map(shared).astype(np.int64),
    }
    return pd.DataFrame({name: values.reindex(person_ids).to_numpy() for name, values in columns.items()})


def build(view: OriginationView, streams: Streams) -> pd.DataFrame:
    """One row per person in person_id order.

    Every draw is a vector of length P, so the number of draws depends only on the person set and
    never on behaviour values.
    """
    person = view.person
    n = len(person)
    household = view.household.set_index("household_id")
    person_household = household.loc[person["household_id"]]
    others_in_household = person.groupby("household_id")["person_id"].transform("size").to_numpy() - 1

    alt = _alternative_data(view)
    late_rate = alt["electricity_late_rate"].to_numpy()
    months_before = person["origination_month"].to_numpy() - 1
    disconnect_rate = alt["electricity_disconnect_count"].to_numpy() / months_before

    income = (
        person_household["income_band"].map(BAND_BASE_INCOME).to_numpy()
        * streams("income").lognormal(0.0, 0.35, n)
        + 0.3 * alt["remittance_inflow_mean"].to_numpy()
    )
    credit_amount = np.round(income * streams("credit").uniform(1.5, 6.0, n) / 100.0) * 100.0
    term = streams("term").choice(LOAN_TERMS_MONTHS, n)

    core = pd.DataFrame({
        "application_id": np.arange(1, n + 1, dtype=np.int64),
        "person_id": person["person_id"].to_numpy(),
        "age_years": person["age_years"].to_numpy(),
        "income": income,
        "dependents": others_in_household + streams("dependents").poisson(0.8, n),
        "credit_amount": credit_amount,
        "installment_to_income": credit_amount / term / income,
        "utilization": np.clip(streams("utilization").beta(2.0, 5.0, n) + 0.4 * late_rate, 0.0, 1.0),
        "open_credit_count": streams("open_credit").poisson(1.0, n),
        "delinquency_count_30": _poisson(streams("delinquency_30"), 0.1 + 2.0 * late_rate),
        "delinquency_count_60": _poisson(streams("delinquency_60"), 0.05 + 1.0 * late_rate),
        "delinquency_count_90": _poisson(streams("delinquency_90"), 0.02 + 3.0 * disconnect_rate),
        "history_months": months_before,
        "on_time_rate": np.clip(1.0 - late_rate + streams("on_time").normal(0.0, 0.05, n), 0.0, 1.0),
        "payment_to_obligation_ratio": streams("payment").lognormal(0.0, 0.2, n) * (1.0 - 0.5 * late_rate),
        "gender": np.array(GENDERS)[streams("gender").integers(0, len(GENDERS), n)],
        "education": np.array(EDUCATION)[streams("education").choice(len(EDUCATION), n, p=EDUCATION_SHARES)],
        "marital_status": np.array(MARITAL_STATUS)[
            streams("marital_status").choice(len(MARITAL_STATUS), n, p=MARITAL_SHARES)
        ],
        "region": person_household["region"].to_numpy(),
        "default_label": view.label.to_numpy(),
        "label_observed": np.ones(n, dtype=np.int64),
    })
    vendor = pd.DataFrame({name: np.full(n, np.nan) for name, _ in schema.VENDOR_COLUMNS})
    return pd.concat([core, vendor, alt], axis=1)
