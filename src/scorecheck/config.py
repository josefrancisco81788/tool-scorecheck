"""Run constants, sourced generator multipliers, and generator tuning.

The panel reads every value here at call time, so a test may monkeypatch a module attribute
before calling ``panel.generate``.
"""

from dataclasses import dataclass
from typing import Literal, Mapping, get_args

Source = Literal["BSP", "telco", "Meralco", "assumption"]


@dataclass(frozen=True)
class Sourced:
    """A generator multiplier with its provenance. Only the sourced multipliers use this type."""

    value: float
    source: Source

    def __post_init__(self) -> None:
        if self.source not in get_args(Source):
            raise ValueError(f"unknown source label {self.source!r}")


SEED: int = 20261024
N_MONTHS: int = 24
SCALE_DEFAULT: int = 50_000
SCALE_FULL: int = 200_000
SCALES: Mapping[str, int] = {"default": SCALE_DEFAULT, "full": SCALE_FULL}

BANNERS: Mapping[str, str] = {
    "default": (
        f"This run uses the default scale of {SCALE_DEFAULT:,} households. "
        f"The full run is {SCALE_FULL:,} households."
    ),
    "full": (
        f"This run uses the full scale of {SCALE_FULL:,} households. "
        f"The default run is {SCALE_DEFAULT:,} households."
    ),
}

PREPAID_PROBABILITY = Sourced(0.96, "telco")

# Keyed by calendar month. docs/research/b-synthetic-panel.md quotes only April, May, July, and
# December from the BSP cash remittance release; the other months are a flat assumption.
REMITTANCE_MULTIPLIERS: Mapping[int, Sourced] = {
    1: Sourced(1.00, "assumption"),
    2: Sourced(1.00, "assumption"),
    3: Sourced(1.00, "assumption"),
    4: Sourced(0.90, "BSP"),
    5: Sourced(0.90, "BSP"),
    6: Sourced(1.00, "assumption"),
    7: Sourced(1.07, "BSP"),
    8: Sourced(1.00, "assumption"),
    9: Sourced(1.00, "assumption"),
    10: Sourced(1.00, "assumption"),
    11: Sourced(1.00, "assumption"),
    12: Sourced(1.18, "BSP"),
}

DISCONNECTION_SHARE = Sourced(0.05, "assumption")


def generator_multipliers() -> dict[str, Sourced]:
    return {
        "prepaid_probability": PREPAID_PROBABILITY,
        **{f"remittance_{month:02d}": REMITTANCE_MULTIPLIERS[month] for month in range(1, 13)},
        "disconnection_share": DISCONNECTION_SHARE,
    }


ability_default_weight: float = 1.0
willingness_default_weight: float = 1.0


@dataclass(frozen=True)
class Tuning:
    """Unlabelled shape constants. Changing one changes the golden hashes."""

    origination_months: tuple[int, int] = (2, 18)
    extra_persons: tuple[int, float] = (3, 0.25)
    extra_sim_probs: tuple[float, float] = (0.45, 0.10)
    urban_share: float = 0.54
    remittance_receiver_share: float = 0.30
    income_band_shares: tuple[float, ...] = (0.40, 0.30, 0.20, 0.10)
    region_shares: tuple[float, ...] = (
        0.13, 0.02, 0.05, 0.03, 0.11, 0.15, 0.03, 0.06, 0.07,
        0.07, 0.04, 0.03, 0.04, 0.05, 0.04, 0.03, 0.05,
    )
    electricity_shared_probs: tuple[float, float] = (0.70, 0.15)
    ewallet_second_account_share: float = 0.40
    ewallet_shared_share: float = 0.35
    late_before_disconnection_share: float = 0.15
    unpaid_fraction_of_disconnection: float = 0.30
    region_shock_probability: float = 0.08
    post_origination_shock_probability: float = 0.03
    remittance_ability_loading: float = 2.0
    region_shock_ability_hit: float = 0.5
    default_intercept: float = -5.5
    vendor_signal_weight: float = 0.8
    post_shock_weight: float = 1.5


TUNING = Tuning()

REGIONS: tuple[str, ...] = (
    "NCR", "CAR", "Ilocos Region", "Cagayan Valley", "Central Luzon", "CALABARZON", "MIMAROPA",
    "Bicol Region", "Western Visayas", "Central Visayas", "Eastern Visayas", "Zamboanga Peninsula",
    "Northern Mindanao", "Davao Region", "SOCCSKSARGEN", "Caraga", "BARMM",
)
ROLES: tuple[str, ...] = ("head", "spouse", "adult_child", "other_adult")
INCOME_BANDS: tuple[str, ...] = ("low", "lower_middle", "middle", "upper_middle")


def scale_name(n_households: int) -> str:
    for name, count in SCALES.items():
        if count == n_households:
            return name
    return "custom"
