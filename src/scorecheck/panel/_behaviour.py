import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np

from scorecheck import schema
from scorecheck._streams import Streams
from scorecheck.panel._grid import PersonMonth, PersonMonthGrid
from scorecheck.panel._params import GeneratorParams
from scorecheck.panel._population import Population
from scorecheck.panel._truth import Traits

WILLINGNESS_LOADING = 0.5
ABILITY_LOADING = 0.25
# A fixed scale rather than the sample sd, so one person's state never depends on another's.
STATE_SCORE_SD = math.sqrt(1.0 + WILLINGNESS_LOADING**2 + ABILITY_LOADING**2)


@dataclass(frozen=True)
class Behaviour:
    electricity_state: PersonMonth
    topup_amount: PersonMonth
    wallet_inflow: PersonMonth
    wallet_outflow: PersonMonth

    def columns(self) -> dict[str, PersonMonth]:
        return dict(vars(self))


def _state_cutpoints(params: GeneratorParams) -> np.ndarray:
    t = params.tuning
    disconnected = params.disconnection_share
    on_time = 1.0 - t.late_before_disconnection_share - disconnected
    restored = disconnected * (1.0 - t.unpaid_fraction_of_disconnection)
    cumulative = np.cumsum([on_time, t.late_before_disconnection_share, restored])
    return np.array([NormalDist(0.0, STATE_SCORE_SD).inv_cdf(c) for c in cumulative])


def draw(streams: Streams, pop: Population, grid: PersonMonthGrid, traits: Traits, params: GeneratorParams) -> Behaviour:
    ability, willingness = traits.ability, traits.willingness

    score = (
        -WILLINGNESS_LOADING * willingness
        - ABILITY_LOADING * ability
        + streams("behaviour.electricity").standard_normal(grid.shape)
    )
    state = np.array(schema.ELECTRICITY_STATES)[np.digitize(score, _state_cutpoints(params))]

    sims = pop.sim_person_row
    prepaid = pop.sim["prepaid"].to_numpy()
    per_sim = (
        streams("behaviour.topup").lognormal(math.log(150.0), 0.5, (len(sims), grid.n_months))
        * np.exp(0.1 * ability[sims])
        * prepaid[:, None]
    )
    first_sim = np.flatnonzero(np.r_[True, sims[1:] != sims[:-1]])
    topup = np.add.reduceat(per_sim, first_sim, axis=0)

    receiver = grid.per_household(pop.remittance_receiver)
    base = streams("behaviour.wallet_base").lognormal(math.log(3000.0), 0.6, grid.n_persons)
    base = base * np.where(pop.remittance_receiver[grid.household_row], 1.5, 1.0)
    calendar = params.remittance_multiplier[grid.calendar_month - 1][None, :]
    inflow = (
        grid.per_person(base)
        * np.exp(0.2 * ability)
        * np.where(receiver, calendar, 1.0)
        * streams("behaviour.wallet_noise").lognormal(0.0, 0.25, grid.shape)
    )
    spend_ratio = np.clip(
        0.85 - 0.1 * willingness + streams("behaviour.spend").normal(0.0, 0.1, grid.shape), 0.3, 1.2
    )
    return Behaviour(
        electricity_state=state,
        topup_amount=topup,
        wallet_inflow=inflow,
        wallet_outflow=inflow * spend_ratio,
    )
