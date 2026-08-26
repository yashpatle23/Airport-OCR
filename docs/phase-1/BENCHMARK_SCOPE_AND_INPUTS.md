# Phase 1 Benchmark Scope and Inputs

**Project:** VOBL aerodrome-chart discovery benchmark  
**Prepared:** 2026-08-19  
**Phase status:** provisional non-operational benchmark; Phase 0 blockers remain open

## 1. Input inspected

The newly attached chart image has been explicitly incorporated into this benchmark. It is a higher-resolution raster representation of:

- AIP India;
- Kempegowda International Airport Bengaluru (`VOBL`);
- Aerodrome Chart `AD 2 VOBL 1-101`;
- displayed date `27 NOV 2025`;
- `AMDT 06/2025`;
- aeronautical information through `AUG 2025`;
- compiled and published by BIAL.

The attachment is visible in the conversation but is not exposed as file bytes in the workspace. It therefore cannot be hashed, OCR-processed, cropped, or measured in page coordinates by local tools. The matching official PDF URL was located in Phase 0, but direct access from the sandbox returned HTTP 403.

## 2. Benchmark intent

This phase bootstraps a deterministic, testable extraction baseline for information that is reliably legible in the attachment. It does **not** claim to complete production extraction or create an approved gold corpus.

The benchmark covers the five approved groups:

1. airport identity;
2. runways and runway directions/thresholds;
3. taxiways;
4. runway holding positions;
5. airport coordinates/elevation.

For taxiways and runway holding positions, only the class and blocked completeness state are benchmarked. Their small identifiers and source geometries cannot be reliably enumerated from the supplied raster without guessing. Original PDF bytes remain mandatory for their extraction benchmark.

## 3. Reliable provisional observations

| Group | Observation | Benchmark treatment |
|---|---|---|
| Airport | `VOBL`; Kempegowda International Airport Bengaluru | Provisional visible label |
| ARP | `13° 11′ 56″ N`, `077° 42′ 20″ E` | Exact source string plus deterministic decimal conversion |
| AD elevation | `3003 ft` | Candidate with open conflict against separately indexed eAIP `3001 FT` |
| Runway pair | `09L/27R`, `4000 m × 45 m` | Provisional visible value |
| Runway pair | `09R/27L`, `4000 m × 45 m` | Provisional visible value |
| Threshold 09L | `13°12′25.26″N 077°41′09.86″E`; THR/TDZ `3003/3003 ft` | Provisional visible value |
| Threshold 27R | `13°12′24.65″N 077°43′22.69″E`; THR/TDZ `2919/2937 ft` | Provisional visible value |
| Threshold 09R | `13°11′23.04″N 077°41′23.92″E`; THR/TDZ `2973/2973 ft` | Provisional visible value |
| Threshold 27L | `13°11′21.92″N 077°43′26.34″E`; THR/TDZ `2964/2965 ft` | Provisional visible value |
| Taxiways | Features and labels visibly exist | Inventory intentionally blocked pending source bytes |
| Runway holding positions | Marking symbols/lines visibly exist in map/insets | Inventory intentionally blocked pending source bytes |

Exact table glyphs, bearing values, surfaces, and operational categories outside the approved scope are not benchmarked here.

## 4. Benchmark source classes

| ID | Source | Availability | Use |
|---|---|---|---|
| `session-vobl-image-2026-08-19` | User-attached raster image | Visual only; no bytes/hash | Manual provisional transcription and limitation assessment |
| `AAI-AIP-VOBL-ADC-2025-11-27-AMDT-06-2025` | Matching official ADC URL | Located, not acquired | Identity/provenance anchor only |
| `AAI-EAIP-VOBL-AD2.1-TEXT-INDEXED` | Indexed official eAIP text result | Search snippet only | Conflict evidence for `3001 FT`; effective-edition reconciliation required |

## 5. Benchmark tracks

### Track A — deterministic normalization

- Parse controlled DMS coordinate strings.
- Convert to decimal degrees without losing the source string.
- Validate range, hemisphere, reciprocal runway pairing, dimensions, units, and GeoJSON coordinate order.
- Produce JSON and GeoJSON research projections.

This track can run now because it operates on explicitly transcribed provisional values.

### Track B — source extraction

- Native PDF text and vector parsing.
- Raster rendering and OCR.
- Taxiway/holding symbol and line extraction.
- Page-space evidence geometry.
- Georeferencing and topology.

This track is blocked until the original PDF or hashable full-resolution image is available.

## 6. Non-goals

- No operational or navigation use.
- No claim of AAI/BIAL authority for derived output.
- No complete taxiway or holding-position inventory.
- No model training.
- No position-accuracy claim from the chart drawing.
- No evidence bounding boxes because source image bytes/page coordinates are unavailable.
- No managed OCR upload without rights/security approval.

## 7. Benchmark success criteria

This provisional Phase 1 benchmark succeeds when:

- the transcribed airport/runway observations are represented in a schema with explicit provisional status;
- all DMS conversions and output axis order pass deterministic checks;
- reciprocal runway and dimension rules pass;
- the elevation conflict remains unresolved and visible;
- taxiway/holding incompleteness is machine-readable and cannot be mistaken for an empty authoritative inventory;
- available tool capabilities and missing dependencies are documented;
- extraction approaches are compared with a recommended next experiment;
- all artifacts are reproducible without implying that Phase 0 has exited.

## 8. Blocking input required for the full benchmark

Upload the exact original `VOBL-ADC.pdf` corresponding to `AD 2 VOBL 1-101`, `27 NOV 2025`, and `AMDT 06/2025`. Once available, the benchmark can measure native extraction, OCR, vector geometry, evidence coordinates, taxiway/holding recall, latency, and cost.
