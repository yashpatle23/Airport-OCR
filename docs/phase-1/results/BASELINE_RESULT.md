# Phase 1 Deterministic Baseline Result

**Run date:** 2026-08-19  
**Result:** `PASS_WITH_EXPECTED_BLOCKERS`  
**Operational use:** prohibited

## What ran

`phase-1/scripts/normalize_and_validate.py` processed the provisional source-preserving VOBL fixture using Python's standard library. It performed DMS parsing, decimal conversion, domain validation, conflict preservation, reciprocal-runway checks, unit checks, completeness checks, GeoJSON generation, and run-manifest hashing.

No OCR, PDF parsing, CV, external API, or model call was used.

## Results

| Outcome | Count |
|---|---:|
| Passed checks | 25 |
| Informational checks | 2 |
| Expected blockers | 4 |
| Failed checks | 0 |

Expected blockers are:

1. original source bytes/SHA-256 unavailable;
2. source processing/training rights unconfirmed;
3. taxiway inventory requires source bytes;
4. runway-holding-position inventory requires source bytes.

## Normalized coordinates

All output coordinates use `OGC:CRS84` / RFC 7946 longitude-latitude order.

| Feature | Longitude | Latitude |
|---|---:|---:|
| VOBL ARP | 77.7055555556 | 13.1988888889 |
| RWY 09L threshold | 77.6860722222 | 13.2070166667 |
| RWY 27R threshold | 77.7229694444 | 13.2068472222 |
| RWY 09R threshold | 77.6899777778 | 13.1897333333 |
| RWY 27L threshold | 77.7239833333 | 13.1894222222 |

The exact source DMS strings remain attached to every normalized point.

## Runway checks

- Reciprocal pairs `09L/27R` and `09R/27L` passed.
- Both provisional runway records preserve displayed dimensions `4000 M × 45 M`.
- Threshold-to-threshold connector distances are approximately `3994.3 m` and `3681.7 m`.
- Connector length is not asserted to equal declared runway length because thresholds may be displaced.
- Generated lines are explicitly labelled `DERIVED_THRESHOLD_CONNECTOR_NOT_RUNWAY_EXTENT`; no surveyed runway geometry is claimed.

## Conflict behavior

The chart claim `3003 FT` and separately indexed eAIP claim `3001 FT` remain independent. `selected_value` is `null`; the system did not average or silently select a value.

## Outputs

- `validation-report.json`
- `vobl-normalized.json`
- `vobl-features.geojson`
- `benchmark-run.json`

The run manifest records fixture hash, script hash, output hashes, runtime, zero external calls, and zero estimated variable API cost.
