# Airport-OCR

Turn aerodrome-chart observations into validated, normalized, searchable data — safely.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yashpatle23/Airport-OCR/blob/feat/airport-ocr-poc/notebooks/Airport_OCR_Colab.ipynb)

Run the whole pipeline in your browser — no local setup — with the [Colab notebook](notebooks/Airport_OCR_Colab.ipynb): upload the VOBL PDF (or a PyMuPDF words dump) and get intake → native-text extraction → normalize → validate → JSON/GeoJSON → map/search.

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
- **Native PDF text extraction** — turn a PyMuPDF `page.get_text("words")` dump
  into observations: airport identity, ARP, elevation, the runway table, and the
  full **taxiway inventory** (with widths) parsed from the runway-pavement legend.

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

# Extract observations from a native PDF word dump (PyMuPDF words)
airport-ocr extract-pdf-words examples/vobl-words-sample.json --output out/vobl.json
airport-ocr process out/vobl.json --output-dir out

# Run the web application (API + browser UI) and open http://127.0.0.1:8000
airport-ocr serve examples/vobl-from-pdf-observations.json --port 8000
```

### Native PDF text extraction

Produce the words dump on a machine that has PyMuPDF and the source PDF:

```python
import fitz, json           # PyMuPDF
doc = fitz.open("VOBL-ADC.pdf")
pages = [{"page": i, "size": [p.rect.width, p.rect.height], "words": p.get_text("words")}
         for i, p in enumerate(doc)]
json.dump(pages, open("vobl_words.json", "w"))
```

Then extract and validate locally (no PDF library needed downstream):

```bash
airport-ocr extract-pdf-words vobl_words.json --output out/vobl.json
airport-ocr process out/vobl.json --output-dir out
```

`extract-pdf-words` recovers the airport header, the four runway threshold rows,
and the **43 VOBL taxiways** (B3 = 15 m, the rest 23 m) from the legend. Runway
holding positions stay `BLOCKED_SOURCE_BYTES_REQUIRED` because distinct
identifiers/associations need the marking-geometry layer, not the word stream.

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
src/airport_ocr/   intake, coordinates, pdf_words, validation, pipeline, search, webapp, webui, CLI
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
