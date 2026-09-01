# Airport-OCR project implementation summary

This document consolidates the work completed in Airport-OCR: what problem we
addressed, what we built, how the system now works, what was verified, and what
remains intentionally out of scope.

> **Safety classification:** non-operational, research-only. Airport-OCR does
> not produce authoritative aeronautical data and its output must not be used
> for navigation or operational decisions. Source rights and qualified aviation
> review remain required.

## Current 0.3.0 application delivery

Local development is now primary. The current increment adds a portable FastAPI
microservice, same-origin central PDF upload-to-JSON UI, fixed 5 MiB PDF policy,
Pydantic/OpenAPI contracts and problem details, tracked bounded async/thread
offload, PyMuPDF complexity controls, and local Uvicorn plus Docker/Compose
infrastructure. FastAPI was selected instead of Django because the service is
stateless and needs ASGI/multipart/contracts rather than ORM/admin/template
features.

The deterministic domain core remains framework-independent. Application edges
intentionally depend on FastAPI, Pydantic, PyMuPDF, python-multipart, and Uvicorn.
The earlier Colab workflow documented below remains an optional immutable demo,
not the primary development environment. See the
[local architecture](architecture/LOCAL_FASTAPI_APPLICATION.md),
[API standards](API_STANDARDS.md), and
[Python memory/concurrency study](PYTHON_MEMORY_AND_CONCURRENCY.md).

## 1. Project objective

Airport aerodrome charts are visually structured PDFs containing text, tables,
coordinates, vector linework, and symbols. The project turns supported
native-text charts into source-preserving, validated, searchable research
artifacts for five feature groups:

1. airport identity;
2. runways and runway directions;
3. taxiways;
4. runway holding positions;
5. airport coordinates and elevation.

The implemented flow is:

```text
PDF → controlled intake → extract → identify → normalize/validate → structure → search/report
```

The project prioritizes provenance and honest uncertainty over apparent
completeness. Missing or unsupported facts remain null, blocked, partial, or
review-required; they are never silently invented.

## 2. Starting point and problem found

The initial proof of concept worked mainly as a VOBL/Bengaluru demonstration.
Important airport facts were coupled to that sample: airport identity, runway
pairs, dimensions, an external elevation claim, taxiway legend shape, and parts
of the notebook/UI workflow.

A Chennai/VOMM chart exposed why those assumptions could not be generalized:

- VOMM uses runways `07/25` and `12/30`, not VOBL's parallel runway pairs;
- its title and elevation formatting differ;
- its visible runway rows contain threshold elevation but no TDZ column;
- physical dimensions and declared distances must not be confused;
- taxiways are referenced differently;
- holding positions are graphical symbols rather than reliable text records.

We therefore redesigned the extractor around evidence, layout capabilities, and
airport-independent domain rules instead of adding another set of hard-coded
airport values.

## 3. What we delivered

### 3.1 Governance, requirements, and architecture

We created and refreshed the planning set:

- `planning/PRD.md` — product requirements, scope, acceptance criteria, and
  non-goals;
- `planning/Architecture.md` — components, data flow, trust boundaries, and
  output contracts;
- `planning/Design.md` — interface and state presentation decisions;
- `planning/Rules.md` — binding anti-fabrication, safety, dependency, security,
  and workflow rules;
- `planning/Phases.md` — completed, partial, blocked, and future phases;
- `planning/Memory.md` — current state, decisions, regression facts, and
  delivery history.

We also added focused multi-airport research and design documents covering
chart standards, layout-aware extraction, GeoJSON axis order, evidence handling,
profile isolation, and safe unsupported states.

### 3.2 Controlled source intake and provenance

The intake layer now:

- verifies that a source file exists;
- detects supported media types from magic bytes;
- records extension/signature mismatches;
- computes SHA-256 and byte size;
- explicitly records whether original bytes are available;
- records, but does not fabricate, malware-scan and rights status;
- optionally creates a verified content-addressed quarantine copy.

Provenance validation is fail-closed: source-byte readiness passes only when
availability is literal boolean `true` and the SHA-256 has the correct form.
Truth-like strings or numbers cannot be promoted to trusted availability.

### 3.3 Page-aware native-text extraction

We generalized `src/airport_ocr/pdf_words.py` to consume one or more PyMuPDF
positioned-word pages while preserving page and block identity.

The extractor now supports:

- AAI-style chart identifiers such as `AD 2 VOMM 1-101`;
- airport title candidates without substituting a different airport;
- ARP latitude/longitude associated with a header region rather than the first
  coordinates found anywhere in the document;
- `AD ELEV`, `AD.ELEV.`, and `AD ELEVATION` variants;
- source date and amendment metadata when uniquely attributable;
- arbitrary valid runway-direction rows with displayed bearing, DMS threshold
  coordinates, threshold elevation, and optional TDZ elevation;
- page-qualified evidence on extracted threshold facts;
- explicit extraction diagnostics, adapters used, page count, and native-word
  count.

Textless/scanned PDFs stop with
`UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED`. Unknown required layouts stop with a
specific unsupported-layout error instead of emitting VOBL defaults.

### 3.4 Airport-independent runway assembly

Runway ends are paired using reciprocal-designator rules rather than a fixed
runway list. This supports examples such as:

- `09L ↔ 27R` and `09R ↔ 27L` at VOBL;
- `07 ↔ 25` and `12 ↔ 30` at VOMM;
- other valid `01–36` runway numbers with `L`, `R`, or `C` suffixes.

Physical runway dimensions are accepted only from explicit dimension text such
as `RWY 07/25 - 3658 M X 45 M`. TORA, TODA, ASDA, and LDA declared distances are
never substituted for physical length or width.

Threshold-to-threshold lines in GeoJSON are explicitly labelled as derived
connectors, not surveyed runway extents or polygons.

### 3.5 Taxiway extraction without false completeness

Two taxiway evidence paths were implemented:

1. a strict width-first legend parser for structured lists such as the VOBL
   legend;
2. explicit `TWY <designator>` or `TAXIWAY <designator>` text references, which
   become candidate inventory entries with unknown width.

The legend parser uses a constrained designator-list grammar. Ordinary words
such as `AND`, `FOR`, and `RWY` cannot become taxiways. Bare map letters are not
accepted because they are too ambiguous without spatial and symbol analysis.

Taxiway output therefore distinguishes extracted-width features from partial,
review-required text-reference candidates.

### 3.6 Runway holding-position candidates

Holding-position handling remains deliberately conservative:

- accepted holding positions stay blocked-not-absent;
- black vector linework can be clustered into page-qualified candidates;
- nearby known taxiway labels may be associated as evidence;
- every candidate remains `NEEDS_REVIEW`;
- candidate geometry is never automatically promoted to accepted aeronautical
  data.

The full notebook scans all pages rather than only page 0.

### 3.7 Deterministic normalization and validation

The normalization pipeline now applies airport-independent invariants for:

- ICAO identifier format;
- exact DMS parsing and coordinate-axis rules;
- legal latitude/longitude bounds, including the `90°`/`180°` terminal cases;
- reciprocal runway pairs and unique direction inventory;
- displayed runway bearings;
- numeric, finite, positive dimensions and elevations;
- elevation-claim conflict preservation;
- source-byte/SHA provenance;
- taxiway and holding collection completeness semantics.

Coordinates are normalized with `Decimal` and exported in RFC 7946/OGC:CRS84
longitude-latitude order while retaining the original DMS strings.

The system distinguishes:

- `PASS` — a deterministic invariant holds;
- `FAIL` — malformed or contradictory domain data;
- `EXPECTED_BLOCKER` — a known missing, unconfirmed, or unsupported capability;
- `INFO` — non-gating derived information.

Extraction status (`COMPLETE`, `PARTIAL`, or unsupported/error state) and issue
codes survive into normalized JSON, GeoJSON metadata, CLI summaries, packages,
Markdown, HTML, and the web UI.

### 3.8 CLI and local web applications

The primary browser application is now FastAPI. It provides:

- `GET /` — central drag/drop/select PDF upload and JSON views;
- `POST /api/v1/extractions` — versioned multipart extraction;
- `GET /api/v1/health` — liveness/version/fixed limit;
- `GET /api/openapi.json` — machine-readable contract; the default Swagger UI
  is disabled because its CDN assets violate the offline/same-origin policy;
- Pydantic request/response/settings validation and structured problem details;
- exact file-part checks for `.pdf`, `application/pdf`, `%PDF-`, permission, and
  maximum 5,242,880 bytes;
- awaited upload I/O and non-blocking bounded admission with tracked
  `asyncio.to_thread` native work;
- packaged, same-origin, no-CDN assets that render JSON with `textContent`.

The CLI continues to provide:

- `intake` — controlled source inspection and manifest generation;
- `extract-pdf-words` — generic positioned-word extraction with `auto` or
  explicit `vobl-sample` profile;
- `process` — normalization, validation, JSON, and GeoJSON output;
- `search` — feature, airport, designator, and bounding-box queries;
- `serve` — a local non-operational browser application.

Ordinary file, JSON, metadata, coordinate, and type errors return controlled
messages and exit codes rather than raw tracebacks.

The legacy `airport-ocr serve` observation-JSON stdlib app remains data-driven,
self-contained, and compatible. It is no longer the primary PDF workflow. Both
browser surfaces avoid CDNs, analytics, and outbound calls.

### 3.9 Reports and optional AI summary

The reporting layer produces:

- one structured airport package covering all five feature groups;
- a deterministic Markdown summary;
- a self-contained escaped HTML report;
- an optional Gemini paraphrase prompt and response path.

AI is downstream and paraphrase-only. It cannot extract, correct, select, or
invent aeronautical values. Structured output and the deterministic summary are
complete without AI, and all chart/AI text is treated as untrusted when rendered.

### 3.10 Optional historical Google Colab workflow

The generated Colab notebook is retained as an immutable demonstration. It is
not the primary development or application environment. It was rebuilt from the
deterministic generator `scripts/build_full_pipeline_notebook.py` and includes:

- **Upload PDF** as the default source mode;
- an explicit permission acknowledgement;
- exact-one-PDF and PDF-signature checks;
- an optional VOBL sample-download mode;
- controlled intake and SHA-256 provenance;
- a source-name plus SHA-derived run ID;
- all-page positioned-word extraction;
- native-text and required-layout capability gates;
- generic airport/runway/taxiway extraction;
- all-page holding-candidate detection;
- normalization, validation, dynamic map/search, package, and reports;
- deterministic summary with optional Gemini fallback;
- one ZIP containing the complete evidence and result set.

The notebook installation and Colab links are pinned to the reviewed immutable
implementation commit rather than a moving or nonexistent branch.

## 4. End-to-end workflow now available

A supported local run follows these steps:

1. **Select source:** use the central browser UI or multipart API to submit one
   permitted PDF up to 5 MiB and attest permission.
2. **Transport validation:** require PDF extension, MIME, signature, size, and
   Pydantic-validated options without persisting the file.
3. **Extract:** bounded PyMuPDF work reads positioned native text/vector evidence
   from all pages off the ASGI event-loop thread.
4. **Identify:** derive chart/airport facts and determine supported adapters.
5. **Assemble:** pair reciprocal runway directions and create conservative
   taxiway/holding collections.
6. **Normalize:** convert DMS to CRS84, preserve claims, and create normalized
   domain records.
7. **Validate:** report passes, real failures, and expected blockers separately.
8. **Structure:** produce JSON, GeoJSON, package, Markdown, HTML, and candidate
   artifacts.
9. **Display/download:** return the complete response envelope to selectable
   formatted JSON views; the optional Colab path can still create its historical ZIP.

## 5. Output artifacts

The upload-first run produces SHA-qualified artifacts including:

- intake manifest;
- page-aware PyMuPDF words dump;
- source-preserving observations;
- holding-position candidates;
- normalized airport JSON;
- GeoJSON feature collection;
- validation report;
- structured airport package;
- deterministic Markdown summary;
- optional AI paraphrase when configured;
- self-contained HTML report;
- artifact manifest and complete result ZIP.

## 6. Regression case studies

### VOBL/Bengaluru

The explicit `vobl-sample` compatibility profile preserves the known sample
regression:

- runways `09L/27R` and `09R/27L`;
- 4000 × 45 m sample dimensions;
- 43 structured taxiway legend entries;
- ARP `[77.7055555556, 13.1988888889]`;
- unresolved separate 3003/3001 FT elevation claims.

Compatibility values are activated only by explicit profile selection and can
never be applied to a non-VOBL chart.

### VOMM/Chennai

A committed rights-safe synthetic positioned-word fixture exercises the second
layout without redistributing the source chart. The regression verifies:

- `AD 2 VOMM 1-101` and Chennai International Airport;
- ARP `[80.1736036111, 12.9950988889]`;
- aerodrome elevation 54 FT;
- runways `07/25` at 3658 × 45 m and `12/30` at 2890 × 45 m;
- threshold elevations 43/54/44/48 FT;
- taxiway-reference candidates `B`, `C`, `E`, `F`, `G`, `I`, and `M`;
- absent TDZ values, unknown taxiway widths, and unaccepted holding geometry as
  visible blockers rather than fabricated facts.

The VOMM result correctly remains `PARTIAL` even though domain validation has no
real failures.

## 7. Prior 0.2.0 verification baseline

Before the 0.3.0 local-application increment, the multi-airport/Colab branch was
checked with:

- **94 automated tests passing**;
- Python `compileall` passing;
- `git diff --check` passing;
- deterministic regeneration of the 22-cell notebook;
- exact notebook/builder equality;
- VOBL regression verification;
- rights-safe synthetic VOMM extraction and normalization;
- scanned/textless PDF safe-stop behavior;
- VOBL-profile mismatch rejection;
- invalid DMS, terminal-axis, numeric-type, malformed metadata, and missing-file
  regressions;
- CLI extraction-status and issue-code propagation;
- escaped HTML/AI rendering checks;
- final behavior-level review with no confirmed high- or medium-severity issues;
- remote resolution of the immutable Git commit and notebook;
- exact Git installer resolution as `airport-ocr 0.2.0`.

## 7.1 Current 0.3.0 verification

The local-application increment was checked with:

- **94/94 existing domain/CLI regressions passing**;
- Python `compileall` for `src` and `scripts`;
- JavaScript syntax validation with Node;
- `git diff --check`;
- source HTML parsing and no external HTTP/CDN references in packaged API/UI
  source;
- Compose YAML structural parsing;
- a successful `airport_ocr-0.3.0-py3-none-any.whl` build whose 30 entries include
  the API, PDF service, and all three static assets;
- two behavior-level reviews; the confirmed unbounded extraction waiter and
  Swagger-CDN findings were remediated with non-blocking token admission/503 and
  disabled interactive docs plus CSP.

Verification limits are explicit: this sandbox has no FastAPI, Pydantic,
PyMuPDF, python-multipart, or Uvicorn installations and integration-only network
access, so it could not run an ASGI/multipart/native-PDF smoke. Its Docker CLI
also has no Compose provider, so the image/service could not be built and
started here. No new tests were added because the project workflow rule requires
an explicit test request; the 94 tests do not cover the new primary API. The
post-page-materialization PyMuPDF allocation boundary is accepted only for the
documented loopback/permitted-input local scope and requires process isolation
before hostile or remote use.

## 8. Important design decisions

1. **No cross-airport defaults:** generic extraction never injects Bengaluru or
   VOBL facts.
2. **Explicit compatibility only:** `vobl-sample` must be selected by the caller
   and rejects a non-VOBL chart.
3. **Evidence before inference:** page/block source context is retained wherever
   supported.
4. **Declared distance is not runway size:** TORA/TODA/ASDA/LDA never fill
   physical dimensions.
5. **Empty is not absent:** unextracted collections remain
   `NOT_EXTRACTED_NOT_ABSENT`.
6. **Candidates are not accepted data:** taxiway references and holding geometry
   require review.
7. **Partial is visible:** zero validation failures do not turn incomplete
   extraction green or complete.
8. **Conflicts remain unresolved:** the system does not auto-select among
   differing elevation claims.
9. **Layered dependencies:** the Python 3.9+ domain core remains stdlib and
   framework-independent; reviewed local-application edges own FastAPI, Pydantic,
   PyMuPDF, multipart, and Uvicorn.
10. **Local-first portability:** FastAPI/Uvicorn and Docker/Compose replace Colab
    as the primary development path; Colab remains optional.
11. **Async coordination is bounded:** overflow is rejected without a retained
    queue; admitted native work keeps its token through cancellation; threads are
    not isolation.
12. **No operational mode:** `OPERATIONAL_USE` remains false throughout.

## 9. Key implementation locations

| Area | Files |
|------|-------|
| Intake/provenance | `src/airport_ocr/intake.py` |
| Native-text extraction | `src/airport_ocr/pdf_words.py` |
| Coordinate/runway rules | `src/airport_ocr/coordinates.py` |
| Normalization/GeoJSON | `src/airport_ocr/pipeline.py` |
| Validation states | `src/airport_ocr/validation.py` |
| Holding candidates | `src/airport_ocr/holding.py` |
| Search | `src/airport_ocr/search.py` |
| CLI | `src/airport_ocr/cli.py` |
| FastAPI application/contracts | `src/airport_ocr/api/` |
| PDF application service | `src/airport_ocr/services/pdf_extraction.py` |
| Central upload/JSON UI | `src/airport_ocr/static/` |
| Local/container infrastructure | `Dockerfile`, `compose.yaml`, `.env.example` |
| Legacy observation web app | `src/airport_ocr/webapp.py`, `webui.py` |
| Package and reports | `src/airport_ocr/report.py` |
| Full Colab generator | `scripts/build_full_pipeline_notebook.py` |
| Generated full notebook | `notebooks/Airport_OCR_Full_Pipeline.ipynb` |
| Multi-layout fixture | `examples/vomm-synthetic-words.json` |
| Tests | `tests/` |
| Planning and decisions | `planning/` |
| Architecture and research | `docs/architecture/`, `docs/research/` |

## 10. Known limitations and future work

The following are intentionally not claimed as complete:

- OCR for scanned or image-only PDFs;
- universal support for every publisher and chart layout;
- complete taxiway inventory from bare map labels;
- automatic acceptance of runway holding positions;
- surveyed runway/taxiway surface polygons;
- confirmed publication/training rights for source AIP/eAIP material;
- an accountable aviation SME acceptance workflow;
- multi-airport persistence, release governance, and production hardening.

Planned future phases cover OCR/image adapters, additional positively detected
publisher/layout profiles, an audited SME review workflow, multi-airport
persistence, and operational hardening. These phases may increase supported
evidence, but they must not weaken the project's anti-fabrication rules.

## 11. Delivery references

The 0.3.0 local FastAPI increment is published for review:

- Implementation commit:
  [`3949a7e`](https://github.com/yashpatle23/Airport-OCR/commit/3949a7e)
- Delivery branch:
  [`feat/local-fastapi-app`](https://github.com/yashpatle23/Airport-OCR/tree/feat/local-fastapi-app)
- Pull request:
  [PR #4 — Add local FastAPI application and infrastructure](https://github.com/yashpatle23/Airport-OCR/pull/4)

The following references are the parent 0.2.0 multi-airport/Colab delivery:

- Reviewed implementation commit:
  [`4f180eca52dcbe1d35314b68e8c31ee14bf35056`](https://github.com/yashpatle23/Airport-OCR/commit/4f180eca52dcbe1d35314b68e8c31ee14bf35056)
- Delivery branch:
  [`feat/multi-airport-upload`](https://github.com/yashpatle23/Airport-OCR/tree/feat/multi-airport-upload)
- Pull request:
  [PR #3 — Generalize extraction and add upload-first Colab flow](https://github.com/yashpatle23/Airport-OCR/pull/3)
- Immutable upload-first notebook:
  [Open in Google Colab](https://colab.research.google.com/github/yashpatle23/Airport-OCR/blob/4f180eca52dcbe1d35314b68e8c31ee14bf35056/notebooks/Airport_OCR_Full_Pipeline.ipynb)

For detailed contracts and rationale, continue with the
[multi-airport design](architecture/MULTI_AIRPORT_DESIGN.md),
[multi-airport research](research/MULTI_AIRPORT_EXTRACTION_RESEARCH.md), and
[current implementation phases](../planning/Phases.md).
