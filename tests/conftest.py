import json
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "vobl-bootstrap-observations.json"


@pytest.fixture
def observation_document():
    with EXAMPLE.open("r", encoding="utf-8") as handle:
        return json.load(handle)
