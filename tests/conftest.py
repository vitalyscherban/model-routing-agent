import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from router.tasks import build_tasks


@pytest.fixture(scope="session")
def tasks():
    return build_tasks()
