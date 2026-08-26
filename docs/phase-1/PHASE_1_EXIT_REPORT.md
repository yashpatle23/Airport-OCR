# Phase 1 Exit Report

**Project:** VOBL aerodrome chart → structured searchable data  
**Assessment date:** 2026-08-19  
**Overall result:** **PARTIAL COMPLETE WITH EXTERNAL BLOCKERS**  
**Operational use:** not authorized

## 1. Executive decision

The Phase 1 discovery work that can be completed from the attached chart and current sandbox is complete and reproducible. The deterministic normalization baseline passes with expected blockers. The full PDF/vector/OCR/CV provider benchmark cannot be completed until the exact original source bytes, processing rights, and review ownership are available.

Decision:

- **GO:** internal research on schema, deterministic normalization, validation, and search projections.
- **GO WITH WARNINGS:** provisional JSON/GeoJSON prototype.
- **NO-GO:** operational use, gold-corpus claims, OCR/CV model selection, automated taxiway/holding publication, or model training.

## 2. Phase 1 objectives and results

| Objective | Result | Evidence |
|---|---|---|
| Inspect chart and define benchmark scope | Complete | `BENCHMARK_SCOPE_AND_INPUTS.md` |
| Inventory available tools | Complete | `TOOL_INVENTORY.md` |
| Bootstrap all five requested feature groups | Complete with blocked collection states | `data/vobl-bootstrap-observations.json` |
| Preserve source, rights, split, and adjudication metadata | Complete | `data/*manifest.json`, `data/adjudication-log.json` |
| Implement deterministic normalization | Complete | `scripts/normalize_and_validate.py` |
| Generate normalized search views | Complete | `results/vobl-normalized.json`, `results/vobl-features.geojson` |
| Run validation | Complete | `results/validation-report.json` |
| Record reproducibility/cost metadata | Complete | `results/benchmark-run.json` |
| Compare extraction approaches | Complete | `PHASE_1_DISCOVERY_BENCHMARK_REPORT.md` |
| Define metrics, costs, exports, and recommendation | Complete | `PHASE_1_DISCOVERY_BENCHMARK_REPORT.md` |
| Benchmark native PDF extraction and OCR providers | Blocked | Original source bytes and approved tool/provider access unavailable |
| Complete taxiway and runway-holding inventories | Blocked | Requires hashable source with evidence coordinates and qualified review |

## 3. Verified baseline result

Final status: `PASS_WITH_EXPECTED_BLOCKERS`

| Check state | Count |
|---|---:|
| PASS | 25 |
| INFO | 2 |
| EXPECTED_BLOCKER | 4 |
| FAIL | 0 |

Expected blockers:

1. original chart bytes and SHA-256 unavailable;
2. chart processing/training rights unconfirmed;
3. complete taxiway extraction requires source bytes;
4. complete runway-holding-position extraction requires source bytes.

The run used Python `3.9.25`, no external API, and no variable OCR/model cost. Runtime is approximately `1–2 ms` for normalization alone; this is not an extraction throughput measurement.

## 4. Provisional structured result

### Airport

- ICAO: `VOBL`
- Name: Kempegowda International Airport Bengaluru
- ARP source: `13°11′56″N 077°42′20″E`
- ARP CRS84: `[77.7055555556, 13.1988888889]`
- Aerodrome elevation: unresolved claims `3003 FT` and `3001 FT`; no selected value

### Runways

| Pair | Displayed dimensions | Thresholds | Status |
|---|---|---|---|
| `09L/27R` | `4000 M × 45 M` | `09L`, `27R` coordinates/elevations normalized | Provisional |
| `09R/27L` | `4000 M × 45 M` | `09R`, `27L` coordinates/elevations normalized | Provisional |

The attached chart's direction cells are provisionally transcribed as `092°4′` and `272°4′`; exact glyph/reference semantics must be verified from the original PDF.

Generated LineStrings are threshold connectors only and are explicitly not surveyed runway extents.

### Taxiways

- Features are visibly present.
- Complete identifiers, elements, geometry, and graph topology are not extracted.
- Empty feature array means `NOT_EXTRACTED_NOT_ABSENT`.
- Status: `BLOCKED_SOURCE_BYTES_REQUIRED`.

### Runway holding positions

- Holding markings are visibly present in the chart/map insets.
- Complete identities, taxiway/runway associations, and marking-line geometries are not extracted.
- Empty feature array means `NOT_EXTRACTED_NOT_ABSENT`.
- Status: `BLOCKED_SOURCE_BYTES_REQUIRED`.

## 5. Benchmark success-criteria assessment

| Criterion | Result |
|---|---|
| Airport/runway observations represented with explicit provisional state | PASS |
| All DMS conversions deterministic and source strings preserved | PASS |
| Output longitude/latitude axis order explicit | PASS |
| Reciprocal runway and dimension checks pass | PASS |
| Elevation conflict remains visible and unresolved | PASS |
| Taxiway/holding incompleteness cannot be mistaken for absence | PASS |
| Tool inventory and approach comparison documented | PASS |
| Normalized JSON and GeoJSON generated | PASS |
| Run hashes and costs recorded | PASS |
| Native PDF/vector metrics measured | BLOCKED |
| OCR engine/provider metrics measured | BLOCKED |
| Taxiway/holding precision and recall measured | BLOCKED |
| Generalization across airports/templates measured | BLOCKED |

## 6. Remaining blockers

### B1 — Original source file

Required:

- exact official `VOBL-ADC.pdf` for `AD 2 VOBL 1-101`, `27 NOV 2025`, `AMDT 06/2025`;
- workspace file bytes;
- SHA-256, byte size, MIME, malware result, page count, and header verification.

### B2 — Rights decision

A named Rights/Legal Owner must approve or reject:

- internal storage and parsing;
- reviewer page/crop display;
- managed OCR upload and permitted regions/retention;
- derived structured output;
- source/crop redistribution;
- model training or fine-tuning.

### B3 — Accountable quality ownership

Required:

- Accountable Data Owner;
- Aviation Quality Owner;
- two independent qualified reviewers;
- adjudicator/release approver;
- approved research or operational acceptance policy.

### B4 — Extraction environment

After B1–B3 permit the work, create a pinned environment containing:

- PyMuPDF plus an independent PDF parser;
- Pillow/OpenCV;
- Tesseract and language data;
- Shapely/pyproj and GDAL where needed;
- JSON Schema validation;
- approved managed OCR adapters, if permitted;
- PostgreSQL/PostGIS for the canonical benchmark store.

### B5 — Representative corpus

VOBL alone is a development fixture. Model/vendor selection requires multiple airports, publishers/templates, native/raster document types, and held-out airport-level splits.

## 7. Recommended next controlled action

Do not start Phase 2 implementation as if extraction quality has been established. First close B1–B3, then complete the deferred Phase 1 experiment:

1. intake and hash the original PDF;
2. inspect native text/vector/images/transforms;
3. freeze double-reviewed source labels for all five classes;
4. run two native parsers, Tesseract multi-DPI, and—if approved—two managed OCR providers;
5. extract taxiway and holding candidates with page evidence;
6. score exact critical tokens, relationships, geometry, topology, latency, review time, and total cost;
7. select the hybrid extraction path using cost per accepted airport edition;
8. rerun this exit decision.

Only after that should Phase 2 build the production-oriented hybrid proof of concept.

## 8. Deliverable index

```text
phase-1/
├── BENCHMARK_SCOPE_AND_INPUTS.md
├── TOOL_INVENTORY.md
├── PHASE_1_DISCOVERY_BENCHMARK_REPORT.md
├── PHASE_1_EXIT_REPORT.md
├── data/
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── vobl-bootstrap-observations.json
│   ├── corpus-manifest.json
│   ├── rights-manifest.json
│   ├── split-manifest.json
│   └── adjudication-log.json
├── scripts/
│   └── normalize_and_validate.py
└── results/
    ├── BASELINE_RESULT.md
    ├── validation-report.json
    ├── vobl-normalized.json
    ├── vobl-features.geojson
    └── benchmark-run.json
```

## 9. Final classification

The package is suitable for:

- architecture review;
- schema and API prototyping;
- deterministic normalization demonstration;
- governance and benchmark planning.

It is not suitable for:

- navigation;
- operational airport decisions;
- representing complete VOBL taxiway/holding data;
- claiming OCR/CV accuracy;
- selecting a production extraction provider;
- training a model;
- external publication without rights approval.
