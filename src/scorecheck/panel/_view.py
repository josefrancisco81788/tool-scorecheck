from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from scorecheck import rundir, schema
from scorecheck.panel._grid import is_pre_origination


@dataclass(frozen=True)
class OriginationView:
    """What a lender could know on each person's origination day, plus the label.

    ground_truth is read as person_id, month, and true_default only, and month_behaviour is cut to
    months before origination before it leaves this module.
    """

    seed: int
    household: pd.DataFrame
    person: pd.DataFrame
    sim: pd.DataFrame
    electricity_account: pd.DataFrame
    ewallet_account: pd.DataFrame
    behaviour_before: pd.DataFrame
    label: pd.Series


def read_at_origination(run_dir: Path | str) -> OriginationView:
    run_dir = Path(run_dir)
    person = rundir.read_table(run_dir, schema.PERSON).sort_values("person_id").reset_index(drop=True)
    origination = person.set_index("person_id")["origination_month"]

    behaviour = rundir.read_table(run_dir, schema.MONTH_BEHAVIOUR)
    keep = is_pre_origination(behaviour["month"], behaviour["person_id"].map(origination))
    behaviour_before = behaviour[keep].sort_values(["person_id", "month"]).reset_index(drop=True)

    truth = rundir.read_table(run_dir, schema.GROUND_TRUTH, ["person_id", "month", "true_default"])
    at_origination = truth[truth["month"] == truth["person_id"].map(origination)]
    label = at_origination.set_index("person_id")["true_default"]
    if label.index.duplicated().any() or set(label.index) != set(person["person_id"]):
        raise schema.SchemaError("ground_truth needs exactly one origination row per person")

    return OriginationView(
        seed=rundir.read_run_config(run_dir).seed,
        household=rundir.read_table(run_dir, schema.HOUSEHOLD),
        person=person,
        sim=rundir.read_table(run_dir, schema.SIM),
        electricity_account=rundir.read_table(run_dir, schema.ELECTRICITY_ACCOUNT),
        ewallet_account=rundir.read_table(run_dir, schema.EWALLET_ACCOUNT),
        behaviour_before=behaviour_before,
        label=label.reindex(person["person_id"]),
    )
