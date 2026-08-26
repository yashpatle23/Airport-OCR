import json
import threading
import urllib.request
import urllib.error

import pytest

from airport_ocr.webapp import AppState, create_server


@pytest.fixture
def server(observation_document):
    srv = create_server(observation_document, host="127.0.0.1", port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    host, port = srv.server_address[0], srv.server_address[1]
    base = f"http://{host}:{port}"
    try:
        yield base
    finally:
        srv.shutdown()
        srv.server_close()


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=10) as resp:
        return resp.status, resp.headers, resp.read()


def _get_json(base, path):
    status, headers, body = _get(base, path)
    return status, headers, json.loads(body.decode("utf-8"))


def test_appstate_normalizes(observation_document):
    state = AppState(observation_document)
    assert state.report["status"] == "PASS_WITH_EXPECTED_BLOCKERS"
    assert len(state.geojson["features"]) == 7


def test_index_is_self_contained(server):
    status, headers, body = _get(server, "/")
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    html = body.decode("utf-8")
    # No external assets or network calls beyond this app's own API.
    assert "http://" not in html.replace("http://127.0.0.1", "")
    assert "https://" not in html
    assert "cdn" not in html.lower()


def test_health(server):
    status, headers, payload = _get_json(server, "/api/health")
    assert status == 200
    assert payload["operational_use"] is False
    assert payload["dataset_id"] == "vobl-adc-2025-11-27-bootstrap-v0.1.0"
    assert headers["X-Operational-Use"] == "false"


def test_airport_endpoint(server):
    _, _, payload = _get_json(server, "/api/airport")
    assert payload["airport"]["icao"] == "VOBL"
    assert payload["airport"]["elevation"]["selected_value"] is None
    assert payload["taxiways"]["empty_array_semantics"] == "NOT_EXTRACTED_NOT_ABSENT"


def test_features_endpoint(server):
    _, _, payload = _get_json(server, "/api/features")
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 7


def test_validation_endpoint(server):
    _, _, payload = _get_json(server, "/api/validation")
    assert payload["status"] == "PASS_WITH_EXPECTED_BLOCKERS"
    assert payload["failure_count"] == 0


def test_search_endpoint(server):
    _, _, payload = _get_json(server, "/api/search?feature_type=runway_threshold")
    assert payload["properties"]["match_count"] == 4


def test_search_bad_bbox_returns_400(server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _get(server, "/api/search?bbox=1,2,3")
    assert exc.value.code == 400


def test_unknown_route_404(server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _get(server, "/api/nope")
    assert exc.value.code == 404


def test_process_post(server, observation_document):
    data = json.dumps(observation_document).encode("utf-8")
    req = urllib.request.Request(
        server + "/api/process", data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["validation"]["status"] == "PASS_WITH_EXPECTED_BLOCKERS"
    assert payload["normalized"]["airport"]["icao"] == "VOBL"


def test_process_post_invalid_json_returns_400(server):
    req = urllib.request.Request(
        server + "/api/process", data=b"not json", headers={"Content-Type": "application/json"}, method="POST"
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req, timeout=10)
    assert exc.value.code == 400
