# Multi-airport extraction design

**Status:** implementation design · native-text PDFs · non-operational
**Problem flow:** `PDF → Extract → Identify → Structure → Search`

## 1. Design objective

Replace the VOBL-shaped algorithm with an airport-independent extraction core
that can process different AAI/ICAO aerodrome-chart layouts, including the
attached VOMM chart, while failing safely when a layout is not supported.
"Upload any PDF" means the system accepts and diagnoses the file; it does **not**
mean it may fabricate a complete result for every PDF.

## 2. Processing architecture

```text
Untrusted PDF
  │
  ├─ intake: signature + SHA-256 + rights/malware status
  │
  ├─ native-text capability gate
  │    └─ no positioned words → UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED (stop)
  │
  ├─ page-aware evidence model (word + bbox + block/line + page)
  │
  ├─ deterministic layout adapters
  │    ├─ chart identity: AD 2 <ICAO> <page>, date, airport title
  │    ├─ header: ARP DMS + AD ELEV / AD ELEVATION
  │    ├─ runway rows: designator, bearing, THR DMS, THR/TDZ elevation
  │    ├─ runway dimensions: explicit “RWY xx/yy N M X N M” text
  │    ├─ taxiway legend: width-first list (VOBL adapter)
  │    └─ taxiway references: “TWY A”, “TWY B” candidates (VOMM adapter)
  │
  ├─ domain assembly
  │    ├─ reciprocal runway pairing (dynamic; any 01–36 + L/R/C)
  │    ├─ source-preserving claims and nulls
  │    └─ extraction diagnostics + capability/completeness statuses
  │
  ├─ invariant validation (not airport-value assertions)
  │
  ├─ normalized JSON + RFC 7946 GeoJSON
  │
  ├─ vector holding-position candidate detector (all pages; NEEDS_REVIEW)
  │
  └─ dynamic search + report + ZIP artifact bundle
```

AI remains downstream of the structured package and is paraphrase-only.

## 3. Extractor API

```python
extract_from_words(
    dump,
    *,
    dataset_id=None,
    source_metadata=None,
    airport_name=None,
    external_elevation_claims=None,
    profile="auto",
)
```

- `dump`: one page, a list of pages, or legacy raw words.
- `source_metadata`: intake-derived filename, SHA-256, rights state and optional
  URL; extracted chart metadata wins only for fields actually present on-chart.
- `airport_name`: reviewed/user metadata fallback only; auto-detection is preferred.
- `external_elevation_claims`: explicit claims only. Generic mode never injects a
  VOBL/eAIP claim.
- `profile`: `auto` by default. The `vobl-sample` profile exists only for
  backwards-compatible regression/demo behavior, is activated only by explicit
  caller selection, and can never apply to VOMM. Missing metadata never selects it.

The output keeps observation schema `1.0.0` and adds:

```json
"extraction": {
  "status": "COMPLETE | PARTIAL | UNSUPPORTED",
  "profile": "auto",
  "adapters": ["aai_chart_header", "runway_row_blocks"],
  "issues": [{"code": "...", "detail": "..."}],
  "page_count": 1,
  "native_word_count": 1234
}
```

## 4. Required and optional fields

### Required to normalize
- unique ICAO identifier;
- ARP latitude + longitude;
- at least one complete reciprocal runway pair;
- valid threshold positions for both ends;
- at least one positive aerodrome-elevation claim.

An unsupported/missing required field raises an extraction diagnostic and does
not emit a misleading airport package.

### Optional but blocker-producing
- physical runway dimensions (must come from explicit physical-dimension text;
  never substitute TORA/TODA/ASDA/LDA);
- TDZ elevation;
- complete taxiway inventory and widths;
- accepted holding-position geometry.

Missing optional values remain `null` with an `EXPECTED_BLOCKER`.

## 5. Adapter behavior

### Chart header
- ICAO/chart ID: case-insensitive `AD 2 <four letters> <page>`.
- Elevation variants: `AD ELEV`, `AD.ELEV.`, `AD ELEVATION.` and attached
  values such as `54ft.`.
- ARP: complete latitude/longitude DMS pair associated with one non-runway
  header region (same elevation block, explicit `ARP` block, or unique same-page
  fallback); global first-coordinate selection is forbidden. DMS source strings
  and page/block evidence are retained.
- Name: title lines containing `AIRPORT`/`AERODROME`; a fallback is explicitly
  marked, never replaced with Bengaluru.

### Runways
- Runway rows are recognized by designator + bearing + latitude + longitude.
- Ends are paired with `reciprocal_designator`, so VOBL's 09L/27R and VOMM's
  07/25 both use the same code.
- Dimensions are associated by normalized unordered pair and explicit map text.
- Missing TDZ elevation is valid partial data (VOMM has THR elevation in the
  visible table but no TDZ column).

### Taxiways
- High-confidence VOBL width legends produce structured features with widths
  only when the body is an explicitly delimited designator list. Prose or
  ambiguous tokens reject that legend rather than becoming taxiways.
- `TWY <designator>` references produce **candidate inventory** entries without
  widths. They are useful for VOMM hot-spot text but are not a completeness claim.
- Bare single letters on a map are not accepted as taxiways: the false-positive
  rate is too high without spatial/symbol classification.

### Holding positions
- Text extraction always leaves the accepted collection blocked-not-absent.
- Vector clusters are a separate candidate collection, page-qualified,
  `NEEDS_REVIEW`, and never promoted automatically.

## 6. Validation state machine

| Condition | Result |
|-----------|--------|
| Required identity/ARP/runway/elevation unusable | extraction stops; no normalized package |
| Valid field present | `PASS` |
| Optional field missing/unsupported | `EXPECTED_BLOCKER`; extraction remains `PARTIAL` |
| Contradictory claims | unresolved conflict, `selected_value = null` |
| Heuristic label/geometry | `CANDIDATES_PENDING_REVIEW` |
| Empty unextracted collection | `NOT_EXTRACTED_NOT_ABSENT` |
| Domain invariant broken | `FAIL` |

Extraction diagnostics are preserved through normalized JSON, GeoJSON/package,
Markdown, HTML, CLI, and UI surfaces. `PARTIAL`, candidate, and expected-blocker
states use warning presentation even when validation has zero real failures.

## 7. Notebook run contract

The full Colab notebook defaults to an **Upload PDF** button. Optional sample
mode downloads VOBL explicitly. It preserves the original filename, verifies
PDF signature, creates `<safe-stem>-<sha8>` as `run_id`, scans all pages,
produces dynamic searches/map titles, and downloads one ZIP containing every
artifact and a manifest.

## 8. Compatibility and migration

- Existing VOBL examples/tests remain regression fixtures.
- `extract_from_words` keeps the legacy `eaip_elevation_conflict_ft` keyword;
  the compatibility value applies only to VOBL.
- Observation/package schema versions stay stable for this increment; additions
  are optional fields.
- The core package keeps zero runtime dependencies. PyMuPDF remains notebook/
  adapter-side only.

## 9. Explicit limitations

- Native-text only; scanned/image PDFs need a future OCR adapter.
- Layout adapters cover common AAI-style patterns, not every publisher worldwide.
- Taxiway map-label extraction is partial unless a structured legend/table exists.
- Holding-position output is candidate-grade until qualified human review.
- No operational or authoritative use.
