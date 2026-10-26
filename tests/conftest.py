import pytest

from scorecheck import config, panel
from support.runs import PanelRun


@pytest.fixture(scope="session")
def run_300(tmp_path_factory) -> PanelRun:
    return PanelRun(panel.generate(config.SEED, 300, tmp_path_factory.mktemp("run300")))


@pytest.fixture(scope="session")
def run_2000(tmp_path_factory) -> PanelRun:
    return PanelRun(panel.generate(config.SEED, 2000, tmp_path_factory.mktemp("run2000")))
