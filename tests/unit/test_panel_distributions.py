from support import panel_assertions as pa


def test_prepaid_share(run_2000):
    pa.assert_prepaid_share(run_2000)


def test_sims_per_person(run_2000):
    pa.assert_sims_per_person(run_2000)


def test_electricity_state_shares(run_2000):
    pa.assert_electricity_state_shares(run_2000)


def test_shared_account_counts(run_2000):
    pa.assert_shared_account_counts(run_2000)
