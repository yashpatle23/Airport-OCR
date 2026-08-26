# Airport-OCR

Turn aerodrome-chart observations into validated, normalized, searchable data — safely.

> **Non-operational.** This project produces research data only. Nothing here is
> authoritative aeronautical data and it must never be used for navigation or
> operational decisions. Extracted values remain **provisional** until the
> original source bytes, source rights, and qualified aviation review are
> recorded. See [`docs/`](docs/README.md).

## What this is

A dependency-light Python proof of concept for the target flow:

```
Source intake → observations → normalization → validation → JSON/GeoJSON → search
```

It implements the parts of the pipeline that are safe to run today and defines
clean, replaceable boundaries for the parts that are blocked (native PDF/vector
parsing, OCR, computer vision, and complete taxiway / runway-holding extraction).

The case study is the Kempegowda International Airport, Bengaluru (VOBL)
Aerodrome Chart `AD 2 VOBL 1-101`.

## What works now

- **Controlled intake** — SHA-256 digest, file-signature (magic-byte) sniffing,
  extension-mismatch detection, and a content-addressed quarantine copy. Intake
  records `malware_status`/`rights_status` but never pretends to scan or grant rights.
- **Deterministic coordinate normalization** — DMS parsing with `Decimal`,
  preserving the exact source string, emitting `OGC:CRS84` longitude/latitude.
- **Domain validation** — ICAO format, reciprocal runway pairs, dimensions,
  units, elevation-conflict preservation, and completeness semantics.
- **Exports** — normalized JSON and an RFC 7946 GeoJSON `FeatureCollection`.
- **Search** — filter the GeoJSON projection by feature type, airport, designator, and bbox.
- **Web application** — a stdlib HTTP API and an offline browser UI (structured
  view, elevation-conflict and blocked-collection banners, feature search, and a
  self-contained SVG map). No third-party runtime dependencies and no external
  assets or network calls.

## What is intentionally NOT done

- No OCR / PDF parsing / computer vision (blocked pending source bytes + rights).
- No complete taxiway or runway-holding-position inventory.
- No surveyed runway-surface geometry (runway lines are labelled threshold connectors).
- No model training. No operational/authoritative claims.

Empty `taxiways`/`runway_holding_positions` arrays mean **NOT_EXTRACTED_NOT_ABSENT**,
not "the airport has none". Conflicting claims (e.g. the VOBL `3003 ft` vs
`3001 FT` elevation) are preserved unselected.

## Install

```bash
python -m pip install -e ".[dev]"   # editable install with test deps
# or run without installing:
export PYTHONPATH=src
```

Requires Python 3.9+. Runtime has **no third-party dependencies**.

## Usage

```bash
# Inspect (and optionally quarantine) an untrusted source file
airport-ocr intake path/to/chart.pdf --quarantine-dir quarantine --manifest out/intake.json

# Normalize + validate the provisional VOBL observation fixture
airport-ocr process examples/vobl-bootstrap-observations.json --output-dir out

# Search the generated GeoJSON projection
airport-ocr search out/features.geojson --feature-type runway_threshold
airport-ocr search out/features.geojson --designator 09L
airport-ocr search out/features.geojson --bbox 77.70,13.19,77.71,13.20

# Run the web application (API + browser UI) and open http://127.0.0.1:8000
airport-ocr serve examples/vobl-bootstrap-observations.json --port 8000
```

### Web application

`airport-ocr serve <observations.json>` starts a local, non-operational web app.

UI (`GET /`): airport identity and ARP, the preserved `3003 ft` vs `3001 ft`
elevation conflict, blocked taxiway / runway-holding collections, a runway
table, a searchable feature list, an inline SVG map of the ARP and runway
thresholds, and the full validation report.

JSON API:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | liveness + dataset identity |
| GET | `/api/airport` | normalized airport/runway/collections document |
| GET | `/api/features` | GeoJSON `FeatureCollection` |
| GET | `/api/validation` | validation report |
| GET | `/api/search` | filtered GeoJSON (`feature_type`, `airport`, `designator`, `bbox`) |
| POST | `/api/process` | normalize a posted observation document (stateless) |

```bash
curl http://127.0.0.1:8000/api/health
curl "http://127.0.0.1:8000/api/search?feature_type=runway_threshold"
curl -X POST --data-binary @examples/vobl-bootstrap-observations.json \
  http://127.0.0.1:8000/api/process
```

`airport-ocr process` exits `0` on `PASS_WITH_EXPECTED_BLOCKERS`, `1` on real
validation failures, and (with `--fail-on-blockers`) `3` while expected blockers
remain — useful for strict CI gates.

You can also run it as a module: `python -m airport_ocr ...`.

## Project layout

```
src/airport_ocr/   intake, coordinates, validation, pipeline, search, webapp, webui, CLI
tests/             behavioral tests (pytest)
examples/          provisional VOBL observation fixture
docs/research/     enterprise architecture & solution research
docs/phase-0/      governance, rights, and source-intake controls (BLOCKED)
docs/phase-1/      discovery benchmark, results, and tool inventory (PARTIAL)
docs/architecture/ proof-of-concept design and trust boundaries
```

## Testing

```bash
pytest
```

## Status and blockers

- **Phase 0 (governance/source access):** BLOCKED — original PDF bytes/hash,
  source rights, and named accountable owners are required.
- **Phase 1 (discovery benchmark):** PARTIAL — deterministic normalization is
  complete; PDF/OCR/CV benchmarking and complete taxiway/holding extraction are blocked.

See [`docs/phase-0/PHASE_0_EXIT_REPORT.md`](docs/phase-0/PHASE_0_EXIT_REPORT.md)
and [`docs/phase-1/PHASE_1_EXIT_REPORT.md`](docs/phase-1/PHASE_1_EXIT_REPORT.md).

## License

Code is MIT licensed. It does **not** grant rights to any aeronautical source
charts or AIP/eAIP material — see [`LICENSE`](LICENSE) and `docs/phase-0`.
