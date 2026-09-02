# PRD — Airport-OCR

> **Project Requirements Document.** What we are building, for whom, and what
> "done" means at each stage. This is a living document; see
> [`Phases.md`](Phases.md) for sequencing and [`Memory.md`](Memory.md) for
> current progress.

> ⚠️ **Non-operational, research-only.** Airport-OCR produces **provisional
> research data**. Nothing it emits is authoritative aeronautical data, and it
> must never be used for navigation or operational decisions. This constraint is
> a hard product requirement, not a disclaimer.

---

## 1. Problem statement

Aerodrome charts (e.g. an ICAO Aerodrome Chart, `AD 2 VOBL 1-101`) are published
as **unstructured PDFs**. The useful data — runways, taxiways, holding
positions, the aerodrome reference point (ARP), elevation — is locked inside
vector linework, embedded text, and cartographic symbols. Downstream systems
need this as **structured, machine-readable, searchable** data, with every value
traceable to its source and its trust level explicit.

The target flow:

```
PDF → Extract → Identify → Structure → Search
```

## 2. Goals

1. Accept an uploaded, permitted aerodrome-chart PDF and convert supported
   native-text layouts into validated, normalized JSON + GeoJSON.
2. Extract five feature groups: **airport identity, runways, taxiways, runway
   holding positions, coordinates/elevation**.
3. Make the structured output **searchable** (by feature type, airport,
   designator, bounding box).
4. Make **trust explicit**: every field carries provenance and a completeness
   status; conflicts are preserved, never silently resolved.
5. Safely diagnose scanned or unsupported layouts instead of emitting facts from
   another airport/profile; partial extraction must remain visibly partial.
6. Ship a portable **local FastAPI application** and local-only container as
   the primary development/delivery path, with the generated Colab notebook
   retained only as an optional immutable demo.

## 3. Non-goals (explicitly out of scope)

- No operational or authoritative aeronautical output. Ever.
- No navigation, flight-planning, or safety-of-life use.
- No model training; no bulk scraping of AIP/eAIP sources.
- No claim of surveyed runway-surface geometry (we emit labelled threshold
  connectors, not survey lines).
- No malware scanning or rights-granting — intake **records** status, it does not
  assert clearance.

## 4. Target users

| User | Need | How Airport-OCR serves it |
|------|------|---------------------------|
| **Aviation-data engineer** | Turn charts into structured data with an audit trail | CLI pipeline, JSON/GeoJSON exports, validation report |
| **GIS / data analyst** | Query aerodrome features spatially | GeoJSON `FeatureCollection` + search filters (bbox, designator) |
| **Reviewer / QA (aviation SME)** | Judge whether an extraction is trustworthy | Explicit completeness statuses, preserved conflicts, review-only candidates |
| **Evaluator / senior reviewer** | See a working end-to-end demo | Local FastAPI upload-to-JSON UI, optional Colab notebook, styled reports |
| **Compliance / governance** | Confirm rights and provenance controls | Phase-0 governance docs, intake manifests, source register |

## 5. Functional requirements

### FR-1 Controlled intake
- Compute SHA-256, sniff file signature (magic bytes), detect extension mismatch.
- Write a content-addressed quarantine copy.
- Record `malware_status` and `rights_status` **without** asserting either is clear.

### FR-2 Coordinate normalization
- Parse DMS with `Decimal` (no float drift); preserve the exact source string.
- Emit `OGC:CRS84` longitude/latitude order.

### FR-3 Domain validation
- ICAO identifier format; reciprocal runway pairing; dimension/unit checks.
- **Preserve elevation conflicts unselected** (e.g. VOBL `3003 ft` vs `3001 FT`).
- Distinguish `NOT_EXTRACTED_NOT_ABSENT` from "the airport has none".

### FR-4 Multi-layout native PDF text extraction
- Accept a page-aware PyMuPDF `page.get_text("words")` dump and preserve page/
  bbox evidence.
- Detect airport identity, ARP, elevation, arbitrary reciprocal runway pairs,
  explicit runway dimensions, and supported taxiway legends/references.
- Keep adapters independent (header, runway table, dimensions, taxiways); no
  airport name, runway designator, dimension, or external claim may be globally
  hard-coded.
- Stop with `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED` when no native text exists;
  unknown layouts produce explicit partial/blocker statuses, never VOBL defaults.

### FR-5 Runway holding positions (review-only)
- Produce **candidate** holding positions from page-qualified black-linework
  vector clustering, each marked `NEEDS_REVIEW`.
- Accepted holding positions remain `NOT_EXTRACTED_NOT_ABSENT` /
  `BLOCKED_LAYOUT_OR_REVIEW_REQUIRED` until qualified review; candidate geometry
  must never be promoted automatically.

### FR-6 Exports & search
- Normalized JSON + RFC 7946 GeoJSON `FeatureCollection`.
- Search by `feature_type`, `airport`, `designator`, `bbox`.

### FR-7 Interfaces
- **Local application (primary):** FastAPI/Pydantic microservice plus same-origin
  browser UI; reliably choose or drag/drop one PDF and run intake, all-page
  evidence extraction, identification, normalization/validation, search,
  document-derived research/diagnostics, deterministic summary/report, and
  artifact generation through one request-scoped pipeline.
- **UI outputs:** stage outline, overview, Markdown summary, research/support
  boundary, GeoJSON search and no-tile map, raw evidence/results, SHA-qualified
  individual files, manifest, and complete in-browser ZIP.
- **Upload policy:** require `.pdf`, `application/pdf`, `%PDF-`, explicit
  permission attestation, and a fixed maximum of 5 MiB (5,242,880 file bytes).
- **Async boundary:** use `async`/`await` for request I/O and bounded tracked
  `asyncio.to_thread` work for synchronous PyMuPDF/domain processing.
- **Infrastructure:** local Uvicorn launcher and local-interface Docker/Compose
  profile with non-root, read-only, health/resource controls.
- **CLI:** `intake`, `process`, `search`, `serve`, `extract-pdf-words`; legacy
  `serve` remains compatible but is not the primary PDF workflow.
- **Optional Colab:** immutable upload-first demonstration, not the development
  environment or current application runtime.
- **Report/AI:** self-contained report and optional paraphrase-only summary of
  already-structured data.

## 6. Non-functional requirements

- **Portable local-first runtime:** Python 3.9+ FastAPI application starts via a
  documented virtual-environment command or the local-only Compose profile.
- **Layered dependencies:** the deterministic domain core stays framework-
  independent/stdlib-only; reviewed application edges own FastAPI, Pydantic,
  PyMuPDF, multipart, and Uvicorn.
- **Deterministic** normalization/validation (same evidence → same domain output).
- **Offline & safe by default:** the service binds locally; UI assets are packaged
  same-origin with no external calls; dynamic data is rendered as text.
- **Bounded resources:** fixed file bytes plus configurable page, word, drawing,
  vector-segment, concurrency, and container limits.
- **Auditable API:** Pydantic DTOs, OpenAPI, versioned paths, structured problem
  details, and explicit non-operational/partial/review states.
- **Runtime proficiency:** architecture documentation explains async behavior and
  Python heap, stacks/frames, reference counting, cyclic GC, native allocations,
  deterministic cleanup, and measurement.

## 7. Success metrics / acceptance

- Local FastAPI is the documented primary workflow and runs from a clean virtual
  environment or the local-only Compose profile; Colab is optional/historical.
- The browser picker and fresh drag/drop path share one selected file, run the
  complete pipeline, preserve the file for retry after an error, and expose the
  full stage/summary/research/search/map/raw/artifact result without persistence.
- The complete ZIP contains intake, positioned words, observations, holding
  candidates, normalized JSON, GeoJSON, validation, package, Markdown summary,
  self-contained HTML report, and manifest under the SHA-qualified run ID.
- The API rejects non-PDF extension/MIME/signature, missing permission, files over
  5,242,880 bytes, and bounded document complexity with structured errors.
- Request I/O uses `async`/`await`; synchronous PyMuPDF work is offloaded behind
  tracked bounded per-process capacity and does not run on the event-loop thread.
- OpenAPI and Pydantic DTOs describe the versioned success/error envelopes.
- Local/container setup, API standards, async behavior, and Python heap/stack/GC
  are documented with explicit limits and non-operational boundaries.
- The VOBL regression profile still extracts 09L/27R, 09R/27L and 43 taxiways.
- A VOMM-like native-text dump extracts ICAO VOMM, ARP
  `[80.1736036111, 12.9950988889]`, 54 FT elevation, and reciprocal pairs
  `07/25` and `12/30` without injecting Bengaluru/VOBL facts.
- Validation returns **0 real failures** for supported required fields; missing
  optional dimensions/TDZ/taxiway widths remain expected blockers.
- Scanned/unsupported PDFs stop or emit a diagnostic rather than misleading
  normalized data.
- All five feature groups are represented with honest completeness/review states.
- Full existing test suite remains green (`pytest`).

## 8. Case studies

1. **VOBL — Bengaluru:** `AD 2 VOBL 1-101`; 09L/27R and 09R/27L,
   4000×45 m; 43 legend-derived taxiways; ARP
   `[77.7055555556, 13.1988888889]`; separate 3003/3001 FT claims remain an
   unresolved conflict in the explicit VOBL sample profile.
2. **VOMM — Chennai:** attached `AD 2 VOMM 1-101`; 07/25 and 12/30; ARP
   `12°59′42.356″N 080°10′24.973″E` →
   `[80.1736036111, 12.9950988889]`; 54 FT; taxiway references from hot-spot text
   are candidate-grade and holding markings remain review-only.
