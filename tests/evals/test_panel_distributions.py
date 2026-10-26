"""Advisory eval of the panel's Philippine distributions and drivers. Proves no check on its own."""

import pytest

from support import panel_assertions as pa

EVAL_CASES = [
    pa.assert_prepaid_share,
    pa.assert_sims_per_person,
    pa.assert_electricity_state_shares,
    pa.assert_shared_account_counts,
    pa.assert_driver_signs,
    pa.assert_default_class_counts,
    pa.assert_ability_rank_residual,
    pa.assert_willingness_rank_residual,
    pa.assert_vendor_signal_rank_residual,
    pa.assert_calendar_split,
]


@pytest.mark.parametrize("case", EVAL_CASES, ids=lambda f: f.__name__.removeprefix("assert_"))
def test_panel_eval(case, run_2000):
    case(run_2000)
