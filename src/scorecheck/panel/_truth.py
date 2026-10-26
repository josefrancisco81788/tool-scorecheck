from dataclasses import dataclass

import numpy as np

from scorecheck import config
from scorecheck._streams import Streams
from scorecheck.panel._grid import PersonMonth, PersonMonthGrid
from scorecheck.panel._params import GeneratorParams
from scorecheck.panel._population import Population


@dataclass(frozen=True)
class Exogenous:
    """Draws that no override or weight can change."""

    region_month_shock: PersonMonth
    post_origination_shock: PersonMonth
    vendor_signal: PersonMonth
    default_uniform: PersonMonth


@dataclass(frozen=True)
class Traits:
    """The stored ability and willingness columns."""

    ability: PersonMonth
    willingness: PersonMonth


def draw_exogenous(streams: Streams, pop: Population, grid: PersonMonthGrid, params: GeneratorParams) -> Exogenous:
    t = params.tuning
    region_shock = (
        streams("truth.region_shock").random((len(config.REGIONS), grid.n_months)) < t.region_shock_probability
    )
    post_shock = streams("truth.post_shock").random(grid.shape) < t.post_origination_shock_probability
    vendor_latent = streams("truth.vendor_latent").standard_normal(grid.n_persons)
    vendor_noise = streams("truth.vendor_noise").normal(0.0, 0.3, grid.shape)
    return Exogenous(
        region_month_shock=region_shock[pop.region_code[grid.household_row]],
        post_origination_shock=post_shock & grid.after_origination(),
        vendor_signal=grid.per_person(vendor_latent) + vendor_noise,
        default_uniform=streams("truth.default_uniform").random(grid.shape),
    )


def traits(
    streams: Streams,
    pop: Population,
    grid: PersonMonthGrid,
    exo: Exogenous,
    params: GeneratorParams,
    *,
    ability: PersonMonth | None,
    willingness: PersonMonth | None,
) -> Traits:
    """The formula is always drawn so an override never shifts another stream; an override then
    replaces it and the drawn arrays are dropped."""
    t = params.tuning
    remittance = np.log(params.remittance_multiplier[grid.calendar_month - 1])
    receiver = grid.per_household(pop.remittance_receiver)
    drawn_ability = (
        grid.per_person(streams("truth.ability_base").standard_normal(grid.n_persons))
        + t.remittance_ability_loading * receiver * remittance[None, :]
        - t.region_shock_ability_hit * exo.region_month_shock
        + streams("truth.ability_month").normal(0.0, 0.15, grid.shape)
    )
    drawn_willingness = (
        grid.per_person(streams("truth.willingness_base").standard_normal(grid.n_persons))
        + streams("truth.willingness_month").normal(0.0, 0.10, grid.shape)
    )
    return Traits(
        ability=drawn_ability if ability is None else ability,
        willingness=drawn_willingness if willingness is None else willingness,
    )


def realise_default(traits: Traits, exo: Exogenous, params: GeneratorParams) -> PersonMonth:
    """Absorbing default from month 1, read only from the stored traits and the exogenous draws."""
    t = params.tuning
    logit = (
        t.default_intercept
        - params.ability_weight * traits.ability
        - params.willingness_weight * traits.willingness
        + t.vendor_signal_weight * exo.vendor_signal
        + t.post_shock_weight * exo.post_origination_shock
    )
    event = exo.default_uniform < 1.0 / (1.0 + np.exp(-logit))
    return np.maximum.accumulate(event, axis=1).astype(np.int64)
