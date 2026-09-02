# Airport-OCR

Turn aerodrome-chart PDFs into validated, normalized, searchable research data — safely.

## Run the local application

The primary delivery is a portable FastAPI microservice with a same-origin
browser UI. It accepts one PDF up to **5 MiB** and runs the complete request-
scoped pipeline without blocking the ASGI event loop: controlled intake,
all-page evidence extraction, identification, normalization/validation, search,
document-derived research, deterministic summary/report, and artifact/ZIP
generation. Uploads and results are not persisted by the application.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --constraint constraints-app.txt -e .
airport-ocr-api --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```

Or use the local-only container profile:

```bash
cp .env.example .env             # optional: edit bounded resource settings
docker compose config            # validate the resolved configuration
docker compose up --build -d
docker compose ps
docker compose logs -f airport-ocr
# open http://127.0.0.1:8000
# stop and remove the local service with: docker compose down
```

Compose publishes only to loopback, runs one non-root Uvicorn worker, uses a
read-only root filesystem, and caps the container at 512 MiB, 1 CPU, and 128
processes. The `/tmp` multipart spool is a 64 MiB memory-backed filesystem and
shares the container memory budget. Encoded API responses default to a 64 MiB
cap (`AIRPORT_OCR_MAX_PIPELINE_RESPONSE_BYTES=67108864`, configurable from 1 to
128 MiB); this limits generated JSON, not native PDF expansion or browser ZIP
amplification. These are local-development defaults, not a public deployment
profile.

The application executes:

```text
PDF → Intake → Extract → Identify → Validate → Structure → Search → Research/Report → Artifacts/ZIP
```

The earlier [upload-first Colab notebook](https://colab.research.google.com/github/yashpatle23/Airport-OCR/blob/4f180eca52dcbe1d35314b68e8c31ee14bf35056/notebooks/Airport_OCR_Full_Pipeline.ipynb)
remains an optional immutable demo, not the primary development environment.

> **Non-operational / research-only.** Nothing emitted by this project is
> authoritative aeronautical data, and it must never be used for navigation or
> operational decisions. Uploading a PDF does not grant source rights. Every
> result remains provisional until rights and qualified aviation review are
> recorded.

## Project documentation

For a consolidated account of what was designed, implemented, tested, and
shipped, see the [project implementation summary](docs/PROJECT_IMPLEMENTATION_SUMMARY.md).
The [local application architecture](docs/architecture/LOCAL_FASTAPI_APPLICATION.md),
[API standards](docs/API_STANDARDS.md), and
[Python memory/concurrency study](docs/PYTHON_MEMORY_AND_CONCURRENCY.md) document
the primary runtime in detail. Requirements, decisions, and phase records remain
in [`planning/`](planning/) and [`docs/`](docs/).

## Problem scope

Aerodrome charts are visually structured PDFs containing text, tables, vector
linework, and symbols. Airport-OCR extracts only five groups:

1. airport identity;
2. runways;
3. taxiways;
4. runway holding positions;
5. airport coordinates/elevation.

The project is provenance-first: source strings are retained, missing optional
values become explicit blockers, and conflicting claims are never silently
resolved.

## What works now

- **Local FastAPI full pipeline** — reliable picker/drag-and-drop upload,
  versioned OpenAPI, Pydantic contracts, structured problem details, strict
  PDF-only and 5 MiB enforcement, async chunk reads, bounded
  `asyncio.to_thread` processing, and a complete UI for stage outline, summary,
  document-derived research/diagnostics, GeoJSON search/map, raw evidence/results,
  individual artifacts, self-contained HTML report, and one complete ZIP.
- **Portable infrastructure** — local Uvicorn command plus non-root,
  local-interface Docker/Compose deployment with health checks, a read-only root
  filesystem, dropped capabilities, and CPU/memory/process limits.
- **Optional Colab demo** — browser upload, SHA-qualified run ID, all-page
  processing, dynamic search/map labels, and one complete result ZIP.
- **Controlled intake** — SHA-256, magic-byte detection, extension mismatch, and
  optional content-addressed quarantine. Intake records malware/rights state; it
  never claims to scan or grant rights.
- **Page-aware native-text extraction** — positioned PyMuPDF words retain page
  identity. Header coordinates are associated with a unique non-runway header
  region rather than selected globally. Independent adapters detect AAI-style
  chart IDs/titles, ARP, `AD ELEV` variants, arbitrary runway rows, explicit
  physical dimensions, strict width-first taxiway lists, and explicit `TWY X`
  references.
- **Airport-independent domain assembly** — dynamic reciprocal runway pairing
  supports `07/25`, `12/30`, `09L/27R`, and other valid 01–36 L/R/C pairs.
- **Deterministic coordinate normalization** — exact DMS parsing with `Decimal`;
  RFC 7946/CRS84 longitude-latitude output with original strings preserved.
- **Invariant validation** — validates ICAO, reciprocal pairs, units/ranges,
  elevation claim state, and collection completeness—not VOBL-specific values.
- **Taxiway honesty** — a structured width legend produces reviewed-pending
  features; hot-spot/map text references become candidates with unknown width,
  never a false complete inventory.
- **Holding-position boundary** — page-qualified black-linework clusters remain
  `NEEDS_REVIEW`; accepted positions stay blocked-not-absent.
- **Exports/search/report** — normalized JSON, GeoJSON, attribute/bbox search,
  self-contained safe HTML, and optional Gemini paraphrase.
- **Legacy observation web app** — the stdlib JSON-input API/UI remains available
  through `airport-ocr serve`; it is self-contained but is no longer the primary
  PDF workflow.

## Honest support boundary

"Upload any airport map" means the local application will intake and diagnose it
safely; it does **not** mean every world-wide layout can be fully extracted today.

- **Supported:** native-text AAI/ICAO-style aerodrome charts matching the current
  deterministic adapters.
- **Partial:** unknown optional layouts (e.g. no supported taxiway legend) retain
  `PARTIAL`, `CANDIDATES_PENDING_REVIEW`, or
  `BLOCKED_LAYOUT_OR_REVIEW_REQUIRED`.
- **Stopped safely:** scanned/textless PDFs return
  `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED`; OCR is a future adapter.
- Declared TORA/TODA/ASDA/LDA values are **never** substituted for physical
  runway dimensions.
- Threshold connectors are labelled derived connectors, not surveyed runway
  surfaces.

## Case studies

### VOBL — Bengaluru regression/sample profile

`AD 2 VOBL 1-101`: 09L/27R and 09R/27L; 43 width-legend taxiways; ARP
`[77.7055555556, 13.1988888889]`. The explicit sample profile preserves the
separate 3003/3001 FT elevation claims unresolved.

### VOMM — Chennai multi-layout check

The attached `AD 2 VOMM 1-101` layout exercises a different title/elevation
format, runways 07/25 and 12/30, one THR-elevation column (no TDZ column),
separate declared-distance data, explicit hot-spot `TWY` references, and
cartographic holding symbols. The committed rights-safe synthetic check produces:

- ARP `[80.1736036111, 12.9950988889]` from
  `12°59′42.356″N 080°10′24.973″E`;
- 54 FT single-source elevation;
- 07/25 (3658×45 m) and 12/30 (2890×45 m);
- threshold elevations 43/54/44/48 FT;
- missing TDZ/taxiway widths as expected blockers, not fabricated values.

This is a structural regression from a committed, rights-safe synthetic
positioned-word fixture shaped from the supplied chart image; it is not an
operational dataset or a substitute for running the original permitted PDF.
Extraction remains visibly `PARTIAL` because TDZ values, complete taxiway
inventory/widths, and accepted holding geometry are unavailable.

## Installation and startup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --constraint constraints-app.txt -e .
airport-ocr-api --host 127.0.0.1 --port 8000
```

For development reload only:

```bash
airport-ocr-api --host 127.0.0.1 --port 8000 --reload
```

The service targets Python 3.11 and the package remains source-compatible with
Python 3.9+. FastAPI, Pydantic, Uvicorn, python-multipart, and PyMuPDF are the
local application dependencies. The deterministic domain modules do not import
FastAPI/Pydantic and only the PDF service adapter imports PyMuPDF.

Environment limits are documented in `.env.example`. The 5 MiB upload maximum
is a fixed product/security rule and cannot be increased through environment
configuration.

## CLI usage

```bash
# Inspect an untrusted source
airport-ocr intake chart.pdf --manifest out/intake.json

# Produce a PyMuPDF words dump outside the zero-dependency core, then extract
airport-ocr extract-pdf-words chart-words.json \
  --metadata out/intake.json --output out/observations.json

# Normalize, validate, export, search
airport-ocr process out/observations.json --output-dir out
airport-ocr search out/features.geojson --feature-type runway_threshold
airport-ocr search out/features.geojson --designator 07
airport-ocr search out/features.geojson --bbox 80.15,12.98,80.20,13.02

# Offline app
airport-ocr serve out/observations.json --port 8000
```

`extract-pdf-words` defaults to `profile=auto`. `--profile vobl-sample` is only
for the VOBL regression chart, must be selected explicitly, and refuses non-VOBL
input. Missing metadata never activates compatibility facts. Optional external
elevation claims are explicit CLI/user inputs; generic mode never injects one.

Produce a page-aware words dump with PyMuPDF:

```python
import json, pymupdf

doc = pymupdf.open("airport-chart.pdf")
pages = [
    {"page": i, "size": [p.rect.width, p.rect.height], "words": p.get_text("words")}
    for i, p in enumerate(doc)
]
json.dump(pages, open("chart-words.json", "w"))
```

## Use the full browser pipeline

1. Open `http://127.0.0.1:8000` and choose or drag exactly one PDF.
2. Confirm permission and select **Run full pipeline**.
3. Review the run overview and eight-stage pipeline outline.
4. Inspect the deterministic document summary, document-derived research,
   validation/blockers, extraction diagnostics, and provisional GeoJSON map.
5. Search generated features by exact feature type or designator.
6. Inspect raw intake, positioned words, observations, normalized data, GeoJSON,
   validation, candidates, package, research, manifest, or complete response.
7. Download any SHA-qualified artifact on demand or generate the complete
   `<run-id>-airport-ocr-results.zip` in browser memory. The ZIP temporarily
   retains all serialized artifacts, so generate it only when needed.

The full local artifact set contains intake, positioned words, observations,
holding candidates, normalized JSON, GeoJSON, validation, package, Markdown
summary, self-contained HTML report, and manifest. Optional AI paraphrasing is
explicitly `SKIPPED_OFFLINE_POLICY`; no API key or outbound model call is needed.
If the browser has an older cached UI after updating the branch, restart the
service and hard-refresh the page.

## Local FastAPI contract

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | full same-origin PDF-to-research-artifacts UI |
| GET | `/api/v1/health` | liveness, version, safety flag, and upload limit |
| POST | `/api/v1/pipeline-runs` | complete request-scoped pipeline used by the UI |
| POST | `/api/v1/extractions` | compact compatibility extraction response |
| GET | `/api/openapi.json` | machine-readable API contract (CDN-backed interactive docs disabled) |

Both POST endpoints require a `.pdf` filename, `Content-Type: application/pdf`,
`%PDF-` signature, permission attestation, `profile=auto`, and at most 5 MiB of
uploaded file bytes. Expected errors use `application/problem+json`.

`POST /api/v1/pipeline-runs` adds run/intake metadata, a stage outline,
positioned-word evidence, observations, normalized JSON, GeoJSON, validation,
holding candidates, package, document-derived research/search examples,
deterministic Markdown, escaped HTML report, artifact descriptors, and manifest.
It makes no external research or AI claim: “research” means structured findings,
evidence, diagnostics, support boundaries, and limitations derived from the PDF.
API-owned nested envelopes are validated by Pydantic; domain documents retain
their independent dictionary contracts. The encoded body is capped at 64 MiB by
default, and the browser builds the final ZIP without server persistence or a CDN
dependency.

The legacy `/api/v1/extractions` and `airport-ocr serve` interfaces remain for
compatibility. New local PDF workflows should use the pipeline UI or
`/api/v1/pipeline-runs`.

## Exit codes

`airport-ocr process` exits `0` on `PASS_WITH_EXPECTED_BLOCKERS`, `1` on real
validation failures, and `3` under `--fail-on-blockers` while expected blockers
remain.

## Project layout

```text
src/airport_ocr/api/       FastAPI app, versioned controllers, DTOs, errors, launcher
src/airport_ocr/services/  synchronous PyMuPDF application service
src/airport_ocr/static/    same-origin central PDF upload and JSON UI
src/airport_ocr/*.py       framework-independent extraction/domain/CLI modules
Dockerfile, compose.yaml   local container runtime and resource/security controls
notebooks/                 optional generated Colab demonstrations
scripts/                   deterministic notebook builder + local VOBL demo
examples/                  VOBL regression + rights-safe synthetic VOMM fixtures
docs/                      local architecture/API/runtime study + research/history
planning/                  PRD, Architecture, Rules, Phases, Design, Memory
```

The notebook is an optional legacy demonstration. If it must be regenerated, do
not hand-edit its JSON:

```bash
python scripts/build_full_pipeline_notebook.py
```

## Testing

```bash
pytest -q
```

## Status / next boundary

The deterministic native-text multi-layout increment is implemented. Complete
OCR/CV, complete taxiway map-label extraction, accepted holding geometry, source
rights, and an accountable SME review workflow remain future/gated work. See
[`planning/`](planning/), the
[multi-airport design](docs/architecture/MULTI_AIRPORT_DESIGN.md), and the
[multi-airport research](docs/research/MULTI_AIRPORT_EXTRACTION_RESEARCH.md).

## License

Code is MIT licensed. It does **not** grant rights to source charts or AIP/eAIP
material; see [`LICENSE`](LICENSE) and `docs/phase-0`.
