"""The synthetic Philippine behavioural panel."""

from pathlib import Path
from typing import Sequence

import numpy as np

from scorecheck import rundir, schema
from scorecheck._streams import Streams
from scorecheck.panel import _behaviour, _population, _truth
from scorecheck.panel._grid import PersonMonth, PersonMonthGrid
from scorecheck.panel._params import GeneratorParams

__all__ = ["generate"]


def generate(
    seed: int,
    n_households: int,
    data_dir: Path | str,
    willingness_override: Sequence[float] | None = None,
    ability_override: Sequence[float] | None = None,
) -> Path:
    """Write data_dir/<run id>/ with the seven panel tables and run_config.json; return that directory.

    An override is a sequence aligned to ground_truth sorted by (person_id, month). When given it is
    the stored column, and true_default and behaviour read the stored column.
    """
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError(f"seed must be an int, got {type(seed).__name__}")
    if n_households < 1:
        raise ValueError("n_households must be at least 1")

    params = GeneratorParams.from_config()
    streams = Streams(int(seed), "panel")
    pop = _population.draw(streams, n_households, params)
    grid = PersonMonthGrid(
        person_id=pop.person["person_id"].to_numpy(),
        origination_month=pop.person["origination_month"].to_numpy(),
        household_row=pop.person_household_row,
        n_months=params.n_months,
    )
    exo = _truth.draw_exogenous(streams, pop, grid, params)
    traits = _truth.traits(
        streams, pop, grid, exo, params,
        ability=_parse_override(ability_override, grid, "ability_override"),
        willingness=_parse_override(willingness_override, grid, "willingness_override"),
    )
    true_default = _truth.realise_default(traits, exo, params)
    behaviour = _behaviour.draw(streams, pop, grid, traits, params)

    tables = {
        schema.HOUSEHOLD: pop.household,
        schema.PERSON: pop.person,
        schema.SIM: pop.sim,
        schema.ELECTRICITY_ACCOUNT: pop.electricity_account,
        schema.EWALLET_ACCOUNT: pop.ewallet_account,
        schema.MONTH_BEHAVIOUR: grid.flatten(**behaviour.columns()),
        schema.GROUND_TRUTH: grid.flatten(
            ability=traits.ability,
            willingness=traits.willingness,
            region_month_shock=exo.region_month_shock,
            post_origination_shock=exo.post_origination_shock,
            vendor_signal=exo.vendor_signal,
            true_default=true_default,
        ),
    }
    return rundir.write_run(Path(data_dir), rundir.RunConfig(int(seed), n_households), tables)


def _parse_override(values: Sequence[float] | None, grid: PersonMonthGrid, name: str) -> PersonMonth | None:
    if values is None:
        return None
    raw = values.to_numpy() if hasattr(values, "to_numpy") else values
    arr = np.asarray(raw, dtype=np.float64)
    expected = grid.n_persons * grid.n_months
    if arr.ndim != 1 or arr.size != expected:
        raise ValueError(f"{name} has shape {arr.shape}, expected ({expected},)")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} has non-finite values")
    return arr.reshape(grid.shape)
