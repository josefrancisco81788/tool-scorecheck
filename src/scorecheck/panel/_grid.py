from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

PersonMonth = npt.NDArray
"""Shape (P, M). Row i is the i-th person by ascending person_id; column t is month t + 1."""


def is_pre_origination(month, origination_month):
    """The one definition of the application-time cut."""
    return month < origination_month


@dataclass(frozen=True)
class PersonMonthGrid:
    person_id: npt.NDArray[np.int64]
    origination_month: npt.NDArray[np.int64]
    household_row: npt.NDArray[np.intp]
    n_months: int

    @property
    def n_persons(self) -> int:
        return len(self.person_id)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.n_persons, self.n_months)

    @property
    def months(self) -> npt.NDArray[np.int64]:
        return np.arange(1, self.n_months + 1, dtype=np.int64)

    @property
    def calendar_month(self) -> npt.NDArray[np.int64]:
        return (self.months - 1) % 12 + 1

    def after_origination(self) -> PersonMonth:
        return self.months[None, :] > self.origination_month[:, None]

    def per_person(self, values: npt.NDArray) -> PersonMonth:
        return np.broadcast_to(np.asarray(values)[:, None], self.shape)

    def per_household(self, values: npt.NDArray) -> PersonMonth:
        return self.per_person(np.asarray(values)[self.household_row])

    def flatten(self, **columns: PersonMonth) -> pd.DataFrame:
        data = {
            "person_id": np.repeat(self.person_id, self.n_months),
            "month": np.tile(self.months, self.n_persons),
        }
        for name, values in columns.items():
            if np.shape(values) != self.shape:
                raise ValueError(f"{name} has shape {np.shape(values)}, expected {self.shape}")
            data[name] = np.asarray(values).reshape(-1)
        return pd.DataFrame(data)
