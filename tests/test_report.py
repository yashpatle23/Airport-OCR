import json
from pathlib import Path

import pytest

from airport_ocr.holding import holding_candidates
from airport_ocr.pdf_words import extract_from_words
from airport_ocr.pipeline import normalize
from airport_ocr.report import ai_summary_prompt, build_package, summarize

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "vobl-words-sample.json"


@pytest.fixture
def normalized_report():
    dump = json.loads(SAMPLE.read_text())
    observations = extract_from_words(dump)
    normalized, geojson, report = normalize(observations)
    return normalized, report


def test_build_package_covers_five_groups(normalized_report):
    normalized, report = normalized_report
    pkg = build_package(normalized, report)

    assert pkg["operational_use"] is False
    # 1. Airport, 5. coordinates/elevation
    assert pkg["airport"]["icao"] == "VOBL"
    assert pkg["airport"]["coordinates_elevation"]["arp"]["coordinates_lonlat"][0] == pytest.approx(77.70555, abs=1e-3)
    assert pkg["airport"]["coordinates_elevation"]["elevation"]["selected_value"] is None
    # 2. Runways
    assert {r["designator_pair"] for r in pkg["runways"]} == {"09L/27R", "09R/27L"}
    # 3. Taxiways
    assert pkg["taxiways"]["count"] == 43
    # 4. Holding positions (none provided -> empty accepted, no candidates)
    assert pkg["runway_holding_positions"]["candidate_count"] == 0


def test_build_package_attaches_holding_candidates(normalized_report):
    normalized, report = normalized_report
    segs = [(100, 100 + i * 2, 110, 100 + i * 2) for i in range(6)]
    labels = [{"designator": "A7", "x": 105, "y": 103}]
    cands = holding_candidates(segs, labels, min_segments=4)

    pkg = build_package(normalized, report, holding_candidates=cands)
    hp = pkg["runway_holding_positions"]
    assert hp["candidate_count"] == 1
    assert hp["review_required"] is True
    assert hp["candidate_completeness_status"] == "CANDIDATES_PENDING_REVIEW"


def test_summarize_mentions_all_groups(normalized_report):
    normalized, report = normalized_report
    pkg = build_package(normalized, report)
    md = summarize(pkg)

    assert "VOBL" in md
    assert "Runways" in md and "09L/27R" in md
    assert "Taxiways" in md and "43 taxiways" in md
    assert "Runway holding positions" in md
    assert "unresolved conflict" in md  # 3003 vs 3001
    assert "research only" in md.lower()
    assert "PDF -> Extract -> Identify -> Structure -> Search" in md


def test_ai_summary_prompt_is_safe(normalized_report):
    normalized, report = normalized_report
    pkg = build_package(normalized, report)
    prompt = ai_summary_prompt(pkg)
    assert set(prompt) == {"system", "user"}
    assert "Do not invent" in prompt["system"]
    assert "untrusted" in prompt["system"]
    assert "VOBL" in prompt["user"]
