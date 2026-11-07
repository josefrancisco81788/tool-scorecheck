import pytest

from scorecheck import config
from support.runs import PanelRun, generate_run


@pytest.fixture(scope="session")
def run_300(tmp_path_factory) -> PanelRun:
    return generate_run(config.SEED, 300, tmp_path_factory.mktemp("run300"))


@pytest.fixture(scope="session")
def run_2000(tmp_path_factory) -> PanelRun:
    return generate_run(config.SEED, 2000, tmp_path_factory.mktemp("run2000"))


@pytest.fixture(scope="session")
def experiment_2000(run_2000, tmp_path_factory):
    from support.experiment import prepare

    return prepare(run_2000.run_dir, tmp_path_factory.mktemp("exp2000"))


@pytest.fixture(scope="session")
def report_2000(experiment_2000):
    from scorecheck import report

    return report.run(experiment_2000.run_dir)
