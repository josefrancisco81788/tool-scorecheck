import pytest

from scorecheck import config
from support.runs import PanelRun, generate_run


@pytest.fixture(scope="session")
def run_300(tmp_path_factory) -> PanelRun:
    return generate_run(config.SEED, 300, tmp_path_factory.mktemp("run300"))


@pytest.fixture(scope="session")
def run_2000(tmp_path_factory) -> PanelRun:
    return generate_run(config.SEED, 2000, tmp_path_factory.mktemp("run2000"))
