from dataclasses import dataclass

import numpy as np

from scorecheck import config
from scorecheck.config import Tuning


@dataclass(frozen=True)
class GeneratorParams:
    """Everything the generator reads from config, captured once per ``generate`` call."""

    n_months: int
    prepaid_probability: float
    remittance_multiplier: np.ndarray
    disconnection_share: float
    ability_weight: float
    willingness_weight: float
    tuning: Tuning

    @classmethod
    def from_config(cls) -> "GeneratorParams":
        return cls(
            n_months=config.N_MONTHS,
            prepaid_probability=config.PREPAID_PROBABILITY.value,
            remittance_multiplier=np.array(
                [config.REMITTANCE_MULTIPLIERS[m].value for m in range(1, 13)], dtype=np.float64
            ),
            disconnection_share=config.DISCONNECTION_SHARE.value,
            ability_weight=float(config.ability_default_weight),
            willingness_weight=float(config.willingness_default_weight),
            tuning=config.TUNING,
        )
