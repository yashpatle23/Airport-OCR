"""Self-contained web application for the Airport-OCR proof of concept.

Serves a JSON API and an offline browser UI over the normalized VOBL dataset,
built entirely on the Python standard library (http.server). No third-party
runtime dependencies and no outbound network calls.

Endpoints:
- GET  /                 browser UI (static HTML/JS/CSS, no external assets)
- GET  /api/health       liveness and dataset identity
- GET  /api/airport      normalized airport/runway/collections document
- GET  /api/features     GeoJSON FeatureCollection
- GET  /api/validation   validation report
- GET  /api/search       filtered GeoJSON (feature_type, airport, designator, bbox)
- POST /api/process      normalize a posted observation document (stateless)

Everything remains non-operational and research-only.
"""

from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .pipeline import PipelineError, normalize
from .search import SearchError, search_features
from .webui import INDEX_HTML

_MAX_POST_BYTES = 5 * 1024 * 1024  # generous cap for a single observation doc


class AppState:
    """Holds the normalized dataset served by GET endpoints."""

    def __init__(self, document: Dict[str, Any]):
        self.reload(document)

    def reload(self, document: Dict[str, Any]) -> None:
        normalized, geojson, report = normalize(document)
        self.document = document
        self.normalized = normalized
        self.geojson = geojson
        self.report = report

    @classmethod
    def from_path(cls, path: str | Path) -> "AppState":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls(json.load(handle))


def _parse_bbox(raw: Optional[str]):
    if not raw:
        return None
    parts = [p for p in raw.split(",") if p != ""]
    try:
        values = [float(p) for p in parts]
    except ValueError as exc:
        raise SearchError("bbox must be comma-separated numbers") from exc
    if len(values) != 4:
        raise SearchError("bbox must be minLon,minLat,maxLon,maxLat")
    return values


class Handler(BaseHTTPRequestHandler):
    server_version = "airport-ocr/0.1"
    # Access to shared state is provided via the server instance.

    @property
    def state(self) -> AppState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Quiet by default; the server owns logging policy.
        if getattr(self.server, "verbose", False):  # pragma: no cover
            super().log_message(format, *args)

    # --- helpers ---------------------------------------------------------
    def _send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Operational-Use", "false")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_html(self, html: str, status: int = HTTPStatus.OK) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Operational-Use", "false")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._send_json({"error": message, "operational_use": False}, status=status)

    # --- routing ---------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)

        if route == "/" or route == "/index.html":
            self._send_html(INDEX_HTML)
            return
        if route == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "operational_use": False,
                    "dataset_id": self.state.normalized.get("dataset_id"),
                    "validation_status": self.state.report.get("status"),
                }
            )
            return
        if route == "/api/airport":
            self._send_json(self.state.normalized)
            return
        if route == "/api/features":
            self._send_json(self.state.geojson)
            return
        if route == "/api/validation":
            self._send_json(self.state.report)
            return
        if route == "/api/search":
            self._handle_search(query)
            return
        self._error(HTTPStatus.NOT_FOUND, f"Unknown route: {route}")

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/process":
            self._error(HTTPStatus.NOT_FOUND, f"Unknown route: {parsed.path}")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "Invalid Content-Length")
            return
        if length <= 0:
            self._error(HTTPStatus.BAD_REQUEST, "Empty request body")
            return
        if length > _MAX_POST_BYTES:
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Body too large")
            return
        raw = self.rfile.read(length)
        try:
            document = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._error(HTTPStatus.BAD_REQUEST, "Body must be valid JSON")
            return
        if not isinstance(document, dict):
            self._error(HTTPStatus.BAD_REQUEST, "Body must be a JSON object")
            return
        try:
            normalized, geojson, report = normalize(document)
        except (PipelineError, KeyError) as exc:
            self._error(HTTPStatus.UNPROCESSABLE_ENTITY, f"Cannot process document: {exc}")
            return
        status = HTTPStatus.OK if report["failure_count"] == 0 else HTTPStatus.UNPROCESSABLE_ENTITY
        self._send_json(
            {"normalized": normalized, "geojson": geojson, "validation": report},
            status=status,
        )

    def _handle_search(self, query: Dict[str, list]) -> None:
        def first(name: str) -> Optional[str]:
            values = query.get(name)
            return values[0] if values else None

        try:
            bbox = _parse_bbox(first("bbox"))
            result = search_features(
                self.state.geojson,
                feature_type=first("feature_type"),
                airport_icao=first("airport"),
                designator=first("designator"),
                bbox=bbox,
            )
        except SearchError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        self._send_json(result)


def create_server(
    document: Dict[str, Any],
    host: str = "127.0.0.1",
    port: int = 8000,
) -> ThreadingHTTPServer:
    """Create (but do not start) a configured server bound to host:port."""
    server = ThreadingHTTPServer((host, port), Handler)
    server.state = AppState(document)  # type: ignore[attr-defined]
    server.verbose = False  # type: ignore[attr-defined]
    return server


def serve(
    document: Dict[str, Any],
    host: str = "127.0.0.1",
    port: int = 8000,
    verbose: bool = True,
) -> None:  # pragma: no cover - blocking loop exercised via integration run
    server = create_server(document, host, port)
    server.verbose = verbose  # type: ignore[attr-defined]
    bound_host, bound_port = server.server_address[0], server.server_address[1]
    print(f"airport-ocr web app on http://{bound_host}:{bound_port}  (non-operational)")
    print("Press Ctrl+C to stop.")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        thread.join()
    except KeyboardInterrupt:
        print("\nshutting down...")
        server.shutdown()
        server.server_close()
