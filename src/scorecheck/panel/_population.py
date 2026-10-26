from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

from scorecheck import config
from scorecheck._streams import Streams
from scorecheck.panel._params import GeneratorParams

NON_HEAD_ROLES = ("spouse", "adult_child", "other_adult")
NON_HEAD_ROLE_SHARES = (0.45, 0.40, 0.15)


@dataclass(frozen=True)
class Population:
    household: pd.DataFrame
    person: pd.DataFrame
    sim: pd.DataFrame
    electricity_account: pd.DataFrame
    ewallet_account: pd.DataFrame
    person_household_row: npt.NDArray[np.intp]
    sim_person_row: npt.NDArray[np.intp]
    region_code: npt.NDArray[np.intp]
    remittance_receiver: npt.NDArray[np.bool_]


def _ids(n: int) -> npt.NDArray[np.int64]:
    return np.arange(1, n + 1, dtype=np.int64)


def _position_within(counts: npt.NDArray[np.int64]) -> npt.NDArray[np.int64]:
    starts = np.repeat(np.cumsum(counts) - counts, counts)
    return np.arange(counts.sum()) - starts


def draw(streams: Streams, n_households: int, params: GeneratorParams) -> Population:
    t = params.tuning
    h = n_households

    region_code = streams("household.region").choice(len(config.REGIONS), h, p=t.region_shares)
    urban = streams("household.urban").random(h) < t.urban_share
    income_band = streams("household.income_band").choice(len(config.INCOME_BANDS), h, p=t.income_band_shares)
    receiver = streams("household.remittance_receiver").random(h) < t.remittance_receiver_share
    size = 1 + streams("household.size").binomial(*t.extra_persons, h)
    household = pd.DataFrame({
        "household_id": _ids(h),
        "region": np.array(config.REGIONS)[region_code],
        "urban_rural": np.where(urban, "urban", "rural"),
        "income_band": np.array(config.INCOME_BANDS)[income_band],
        "remittance_receiver": receiver,
    })

    person_household_row = np.repeat(np.arange(h), size)
    p = len(person_household_row)
    role = np.array(NON_HEAD_ROLES)[streams("person.role").choice(3, p, p=NON_HEAD_ROLE_SHARES)]
    role = np.where(_position_within(size) == 0, "head", role)
    lo, hi = t.origination_months
    person = pd.DataFrame({
        "person_id": _ids(p),
        "household_id": person_household_row.astype(np.int64) + 1,
        "age_years": streams("person.age").integers(18, 71, p, dtype=np.int64),
        "role": role,
        "origination_month": streams("person.origination_month").integers(lo, hi + 1, p, dtype=np.int64),
    })

    plus_one, plus_two = t.extra_sim_probs
    u = streams("sim.count").random(p)
    n_sims = 1 + (u < plus_one + plus_two).astype(np.int64) + (u < plus_two).astype(np.int64)
    sim_person_row = np.repeat(np.arange(p), n_sims)
    s = len(sim_person_row)
    sim = pd.DataFrame({
        "sim_id": _ids(s),
        "person_id": sim_person_row.astype(np.int64) + 1,
        "prepaid": streams("sim.prepaid").random(s) < params.prepaid_probability,
        "operator_slot": _position_within(n_sims) + 1,
    })

    multi, single = t.electricity_shared_probs
    electricity_account = pd.DataFrame({
        "account_id": _ids(h),
        "household_id": _ids(h),
        "shared": streams("electricity.shared").random(h) < np.where(size > 1, multi, single),
    })

    n_wallets = 1 + (streams("ewallet.count").random(h) < t.ewallet_second_account_share).astype(np.int64)
    wallet_household = np.repeat(_ids(h), n_wallets)
    ewallet_account = pd.DataFrame({
        "account_id": _ids(len(wallet_household)),
        "household_id": wallet_household,
        "shared": streams("ewallet.shared").random(len(wallet_household)) < t.ewallet_shared_share,
    })

    return Population(
        household=household,
        person=person,
        sim=sim,
        electricity_account=electricity_account,
        ewallet_account=ewallet_account,
        person_household_row=person_household_row,
        sim_person_row=sim_person_row,
        region_code=region_code,
        remittance_receiver=receiver,
    )
