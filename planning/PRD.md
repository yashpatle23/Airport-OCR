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

1. Convert a single aerodrome chart PDF into validated, normalized JSON + GeoJSON.
2. Extract five feature groups: **airport identity, runways, taxiways, runway
   holding positions, coordinates/elevation**.
3. Make the structured output **searchable** (by feature type, airport,
   designator, bounding box).
4. Make **trust explicit**: every field carries provenance and a completeness
   status; conflicts are preserved, never silently resolved.
5. Ship a reproducible demo (Colab notebook + local CLI + offline web UI) plus an
   optional **AI paraphrase** of the structured package.

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
| **Evaluator / senior reviewer** | See a working end-to-end demo | Colab notebook, `DEMO.md`, offline web UI, styled HTML report |
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

### FR-4 Native PDF text extraction
- Convert a PyMuPDF `page.get_text("words")` dump into observations: airport
  header, ARP, elevation, the runway table, and the full taxiway inventory
  (with widths) from the runway-pavement legend.

### FR-5 Runway holding positions (review-only)
- Produce **candidate** holding positions from black-linework vector clustering,
  each marked `NEEDS_REVIEW`. Accepted holding set stays
  `BLOCKED_SOURCE_BYTES_REQUIRED` until reviewed.

### FR-6 Exports & search
- Normalized JSON + RFC 7946 GeoJSON `FeatureCollection`.
- Search by `feature_type`, `airport`, `designator`, `bbox`.

### FR-7 Interfaces
- **CLI**: `intake`, `process`, `search`, `serve`, `extract-pdf-words`.
- **Web app**: stdlib HTTP API + offline browser UI (no external assets/network).
- **Report**: `render_html(package, ai_text)` → self-contained styled HTML card.
- **AI summary (optional)**: paraphrase-only of the *already-structured* package.

## 6. Non-functional requirements

- **Zero runtime third-party dependencies** for the core package (Python 3.9+).
  PyMuPDF is used only to produce the upstream word/vector dump, off the runtime path.
- **Deterministic** normalization/validation (same input → same output).
- **Offline & safe by default**: web UI ships no external assets, scripts, or
  network calls; all chart/AI text is HTML-escaped (treated as untrusted).
- **Reproducible**: Colab notebook pinned to the working branch; tests via pytest.
- **Auditable**: every output field is traceable to source + carries a status.

## 7. Success metrics / acceptance

- End-to-end Colab run completes `PDF → … → Search` on VOBL and writes JSON,
  GeoJSON, and `vobl_report.html`.
- Validation returns `PASS_WITH_EXPECTED_BLOCKERS` with **0 real failures**.
- All five feature groups represented (with honest statuses where blocked).
- Elevation conflict preserved (not auto-resolved).
- Full test suite green (`pytest`).

## 8. Case study

Kempegowda International Airport, Bengaluru — **VOBL**, Aerodrome Chart
`AD 2 VOBL 1-101` (AMDT 06/2025). Two runway pairs (09L/27R, 09R/27L,
4000×45 m), 43 taxiways (B3 = 15 m, rest 23 m), ARP
13°11′56″N 077°42′20″E → `[77.7055555556, 13.1988888889]`.
