import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def engine():
    from run import build_engine
    return build_engine()


@pytest.fixture(scope="session")
def results(engine):
    return engine.run()
