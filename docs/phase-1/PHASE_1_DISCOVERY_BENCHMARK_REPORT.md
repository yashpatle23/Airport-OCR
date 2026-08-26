# Phase 1 Discovery Benchmark Report

**Project:** VOBL aerodrome-chart extraction and search  
**Prepared:** 2026-08-19  
**Decision:** **conditional go for deterministic normalization; no-go for full extraction benchmark until source and rights blockers close**  
**Use classification:** internal research/evaluation only; non-operational

## 1. Executive result

Phase 1 established a reproducible baseline for values that are reliably visible in the attached VOBL chart. It produced a source-preserving bootstrap fixture, deterministic DMS normalization, domain checks, normalized JSON, and GeoJSON. The final run recorded:

- `25` passed checks;
- `2` informational checks;
- `4` expected blockers;
- `0` failed checks;
- `7` provisional GeoJSON features;
- `0` external API calls;
- `$0.00` measured variable API cost;
- approximately `1–2 ms` local normalization time.

The benchmark correctly retains taxiways and runway holding positions as **present but not extracted**, and retains the `3003 FT` versus `3001 FT` elevation claims as an unresolved conflict.

This is not yet a PDF/OCR/CV benchmark. The original official PDF could not be acquired from the sandbox, the attachment is not exposed as hashable workspace bytes, relevant extraction tools are not installed, and processing/training rights remain unapproved.

## 2. Evidence and limitations

### Available evidence

The attached raster chart visually identifies:

- `VOBL` — Kempegowda International Airport Bengaluru;
- chart `AD 2 VOBL 1-101`;
- displayed date `27 NOV 2025`;
- `AMDT 06/2025`;
- aeronautical information through `AUG 2025`;
- ARP `13°11′56″N 077°42′20″E`;
- displayed AD elevation `3003 ft`;
- runway pairs `09L/27R` and `09R/27L`, each displayed as `4000 M × 45 M`;
- four runway threshold coordinate/elevation rows;
- visible taxiway and runway-holding features that are too small to inventory with trustworthy evidence coordinates from the chat attachment.

### Blocking limitations

1. Original PDF bytes and source SHA-256 are unavailable.
2. The official AAI PDF URL returns HTTP 403 from this sandbox.
3. Source storage, processing, crop display, derived-output, and model-training rights are unconfirmed.
4. No named two-reviewer/adjudicator team exists.
5. No native PDF, OCR, CV, or GIS stack is installed.
6. The raster attachment cannot be supplied to local tools, so OCR accuracy, page-space geometry, and latency cannot be measured.
7. One airport edition cannot estimate generalization across publishers/templates.

## 3. Baseline completed

The implemented baseline is intentionally deterministic and narrow:

```text
Provisional visual transcription
    → source-preserving JSON fixture
    → DMS parser using Decimal
    → domain and completeness checks
    → normalized JSON
    → RFC 7946 GeoJSON
    → validation report and hashed run manifest
```

It validates:

- dataset is provisional and non-operational;
- ICAO format;
- DMS syntax, ranges, hemispheres, and precision metadata;
- CRS84 longitude/latitude output order;
- reciprocal runway designators;
- displayed runway dimensions and units;
- threshold and TDZ elevation units;
- exact four-direction inventory;
- conflict preservation;
- blocked-not-absent taxiway and holding-position semantics.

The generated runway lines connect threshold coordinates only. They are labelled `DERIVED_THRESHOLD_CONNECTOR_NOT_RUNWAY_EXTENT`; they do not claim surveyed runway ends or surfaces.

## 4. Extraction approach comparison

| Approach | What it can recover | Strengths | Principal risks | VOBL Phase 1 state | Recommendation |
|---|---|---|---|---|---|
| Official AIXM/AMDB/eAIP structured data | Identities, attributes, coordinates, temporality, sometimes detailed geometry | Highest semantics and source authority | Availability, licensing, edition alignment | Not obtained | Investigate before reverse engineering PDF |
| Native PDF text parsing | Header/table labels, coordinates, dimensions, some map labels | Deterministic, no OCR substitution, retains page coordinates | Missing Unicode maps, outlined glyphs, fragmented text | Blocked by source/tools | First extraction branch |
| Native PDF vector parsing | Lines, curves, fills, styles, possible geometry | Preserves exact drawing primitives | Paths have no aviation semantics; clipping/transforms/layers | Blocked | First geometry branch, fused with text |
| Self-hosted OCR | Raster/scanned text and independent cross-check | Reproducible, data control, low variable cost | Small rotated labels, line interference, O/0 and digit errors | Blocked | Required baseline at several DPI values |
| Managed document OCR/layout | Text polygons, reading order, scalable service | Fast benchmark and strong general OCR | Provider drift, terms, region/retention, aviation labels still hard | Not authorized | Compare at least two only after rights/security approval |
| Classical CV | Runway/taxiway lines, contours, markings, skeletons | Explainable and efficient | Template/color/scale sensitivity; false connectivity | Blocked | Use for candidates and topology features |
| Learned detection/segmentation | Taxiway surfaces, symbols, holding markings | Better template tolerance after training | Requires licensed representative gold labels and MLOps | Premature | Defer until corpus covers multiple airports/templates |
| VLM/foundation model | Region triage, legend assistance, exception suggestions | Flexible and useful to reviewers | Hallucination, nondeterminism, imprecise geometry | Premature | Assistance only; never direct acceptance |
| Manual aviation/GIS review | Ambiguous labels, associations, final acceptance | Handles rare cases and supplies gold corrections | Dominant cost, consistency/capacity risks | Required but owners absent | Mandatory acceptance path |

### Recommended full benchmark arms

When the source and approvals are available, run these arms against the same immutable source digest:

1. **Native-A:** PyMuPDF text spans, drawings, images, and controlled renders.
2. **Native-B:** pypdf/pdfplumber or PDFBox as an independent parser.
3. **OCR-A:** Tesseract on 150/300/450/600 DPI whole-page and region renders.
4. **OCR-B:** one approved managed layout OCR service.
5. **OCR-C:** a second approved managed OCR service to measure vendor-specific errors.
6. **Hybrid:** native text/vector + best OCR + deterministic aviation rules.
7. **Hybrid-CV:** hybrid plus classical line/morphology/skeleton processing.
8. **Human-only control:** qualified reviewer working from the same source and annotation rules.

Do not add a trained detector until the human-only control and multi-airport gold corpus exist.

## 5. Coordinate and elevation semantics

### 5.1 Source-first coordinate representation

Every coordinate retains:

- exact DMS source string;
- parsed degree, minute, second, and hemisphere components;
- source precision;
- source/document/evidence link;
- normalized numeric coordinate;
- horizontal CRS and axis order;
- conversion code/version;
- review state.

The baseline output uses `OGC:CRS84` and GeoJSON/RFC 7946 longitude-latitude order. Example:

```json
{
  "source": {
    "latitude": "13°12′25.26″N",
    "longitude": "077°41′09.86″E"
  },
  "type": "Point",
  "coordinates": [77.6860722222, 13.2070166667],
  "crs": "OGC:CRS84",
  "axis_order": "longitude_latitude"
}
```

Do not assume that an AIXM/GML `EPSG:4326` tuple uses the same serialized axis order as GeoJSON. AIXM export must apply explicit GML/CRS rules rather than copying the GeoJSON array.

### 5.2 Precision versus accuracy

Decimal conversion preserves the displayed DMS precision; it does not improve positional accuracy. Two decimal places of arc-seconds describe source resolution, not guaranteed survey accuracy. Chart line width must never be interpreted as surveyed geometry precision.

### 5.3 Runway geometry

Threshold coordinates define points. A connector between reciprocal thresholds is useful for visualization and search, but:

- it may be shorter than declared runway length when thresholds are displaced;
- it does not represent runway ends, surface polygon, strip, shoulder, or centreline survey;
- it must carry a non-authoritative geometry role.

The baseline calculated approximately `3994.3 m` for `09L–27R` and `3681.7 m` for `09R–27L`; both are informational only.

### 5.4 Elevation semantics

Each elevation must store:

- original value and unit;
- feature meaning: aerodrome, threshold, or TDZ;
- vertical datum when known;
- vertical accuracy when known;
- effective edition;
- source claim and review state.

The baseline does not invent a vertical datum. It does not encode elevation as an unexplained third GeoJSON ordinate.

The chart's `3003 FT` aerodrome elevation and the separately indexed eAIP `3001 FT` claim remain separate because the eAIP effective edition has not been aligned. No value is selected.

## 6. Expected exports

| Export | Phase 1 result | Intended consumer | Constraints |
|---|---|---|---|
| Source-preserving observation JSON | Produced | Extraction, review, audit | Provisional; evidence bounding boxes unavailable |
| Normalized domain JSON | Produced | Application/API prototype | Research only; incomplete taxiway/holding collections |
| RFC 7946 GeoJSON | Produced | Web map and spatial prototype | CRS84 lon/lat; threshold connectors are not runway extents |
| Validation report JSON | Produced | CI, quality dashboard, release gate | Expected blockers remain visible |
| Benchmark run manifest | Produced | Reproducibility/audit | Hashes fixture/script/outputs, not original chart |
| Corpus/rights/split/adjudication manifests | Produced | Data governance and future ML evaluation | Not gold-eligible |
| CSV | Deferred | Simple reporting | Add only after exact consumer fields are agreed |
| GeoPackage | Deferred | Portable/offline GIS | Requires GDAL/SQLite spatial stack and metadata design |
| OGC API Features | Deferred | Search/API clients | Requires service and canonical spatial store |
| AIXM 5.1.1 GML | Deferred | Aviation interchange | Requires formal mapping, temporality, CRS/GML, and schema validation |
| Reviewer evidence package | Blocked | Qualified review | Requires source bytes and permitted page/crop display |

The canonical future store should be PostgreSQL/PostGIS. GeoJSON and search indexes are rebuildable projections, not systems of record.

## 7. Evaluation metrics

### 7.1 Text and field metrics

Report by field criticality and chart region, not only whole-page averages:

- character error rate and word error rate;
- exact-match rate for ICAO, runway/taxiway designators, coordinates, dimensions, and elevations;
- digit substitution, omission, insertion, and transposition counts;
- unit association accuracy;
- table row/column association accuracy;
- label-to-feature relation precision/recall/F1;
- calibrated confidence (Brier score or expected calibration error);
- explicit reject/unreadable rate.

**Release-oriented target for critical tokens:** exact match, not approximate similarity. One wrong coordinate digit is a critical error even if page-level OCR accuracy is high.

### 7.2 Geometry metrics

When source bytes and adjudicated geometries exist:

- point displacement in page units and metres after georeferencing;
- line centreline distance and Hausdorff distance;
- polygon IoU plus boundary F-score;
- taxiway graph node/edge precision and recall;
- connectivity and unexplained dangling endpoint rates;
- holding-line orientation/position error;
- label-association accuracy;
- independent georeferencing holdout median, RMSE, P95, and maximum error.

### 7.3 End-to-end metrics

- airport-edition completeness by the five requested groups;
- critical false omissions and false additions;
- accepted-feature precision;
- straight-through processing rate;
- reviewer correction count, time, and disagreement rate;
- time from source arrival to reviewed release;
- deterministic replay rate;
- cost per accepted airport edition;
- cycle-to-cycle unexpected change count.

### 7.4 Required evaluation slices

- publisher/template;
- native-vector versus raster/scan;
- whole page versus table/main map/inset;
- text size and rotation;
- runway/taxiway network complexity;
- normal versus rare holding-marking styles;
- known versus previously unseen airport and publisher.

One VOBL chart is a development fixture and must not be reported as a general accuracy result.

## 8. Cost model

### 8.1 Measured current baseline

| Item | Measured result |
|---|---:|
| External API calls | 0 |
| Variable API cost | `$0.00` |
| Normalization runtime | approximately `1–2 ms` |
| Source acquisition/OCR/CV cost | not measurable because blocked |
| Reviewer cost | not measured; reviewers not assigned |

### 8.2 Cost equation

Use total cost per accepted airport edition:

```text
C_airport =
  source/licensing allocation
  + pages × (render + native parse + OCR + CV costs)
  + review hours × loaded reviewer rate
  + adjudication hours × loaded domain rate
  + storage/search/egress allocation
  + platform operations allocation
  + rework and failed-run cost
```

Per-page OCR price alone is not a useful procurement metric. Reviewer correction and source governance are likely to dominate for one-page charts.

### 8.3 Planning scenarios, not vendor quotes

The following ranges are assumptions for budgeting the next experiment and must be replaced with measured invoices and loaded labor rates:

| Cost element | Planning assumption | Comment |
|---|---:|---|
| Basic managed OCR | order of `$0.0015` per page where a `$1.50/1,000-page` SKU applies | Google lists this rate for Enterprise OCR; Azure materials cite a similar basic Read order, while layout/custom capabilities may cost more |
| Two managed OCR calls on one chart | `< $0.01` direct OCR usage | Excludes minimum commitments, storage, network, and orchestration |
| Self-hosted OCR/render compute | `$0.01–$0.25` per one-page chart during a multi-DPI benchmark | Assumption; depends on CPU/GPU, render count, retries, and utilization |
| Initial expert review | `0.5–1.5 hours` per airport edition | Dense taxiway/holding geometry can exceed this |
| Loaded review rate example | `$50–$150/hour` | Organization-specific assumption |
| Initial review labor | `$25–$225` per airport edition | Likely larger than OCR charges |
| Adjudication/release | `0.25–1.0 hour` when conflicts occur | Elevation/source conflicts increase this |
| Object storage | negligible per single chart | Governance, retention, and access controls matter more than bytes |
| Engineering/platform | project-level fixed cost | Must be amortized across volume; not estimated from one chart |

Official pricing and limits change by capability, region, tier, and date. Use current calculators and contract terms during procurement: [Amazon Textract pricing](https://aws.amazon.com/textract/pricing/), [Azure Document Intelligence pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/), and [Google Document AI pricing](https://docs.cloud.google.com/document-ai/pricing). Google currently lists Enterprise Document OCR at `$1.50 per 1,000 pages`; treat this only as a current public list-price reference, not a project quote.

### 8.4 Cost fields to capture in the full run

For each arm record:

- input pages and rendered pixels;
- CPU/GPU seconds and machine type;
- API pages/operations and billed amount;
- storage and egress bytes;
- total latency and retries;
- review/adjudication minutes;
- corrected fields/geometries;
- accepted features;
- final cost per accepted airport and feature class.

## 9. Service constraints relevant to the experiment

- Amazon documents minimum detectable text size guidance and distinct synchronous/asynchronous document constraints; its asynchronous PDF/TIFF limits reach thousands of pages, well beyond this one-page chart, but small labels remain the practical issue. See [Textract limits](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html).
- Azure documents service quotas and paid-tier multi-page processing in its [Document Intelligence limits](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/service-limits?view=doc-intel-4.0.0).
- Google documents Enterprise OCR and a default request quota in [Enterprise Document OCR](https://docs.cloud.google.com/document-ai/docs/enterprise-document-ocr) and maintains separate [Document AI limits](https://cloud.google.com/document-ai/limits).

Provider support for a document size does not establish accuracy on tiny rotated aerodrome labels. The benchmark must test actual chart regions.

## 10. Phase 1 decision and recommendation

### Decision by workstream

| Workstream | Decision | Reason |
|---|---|---|
| Deterministic normalization and schema | **GO** for internal research | Implemented, reproducible, no failed checks |
| Provisional JSON/GeoJSON prototype | **GO WITH WARNINGS** | Useful for search design; incomplete and non-operational |
| PDF/vector extraction benchmark | **NO-GO / BLOCKED** | Exact source bytes and parser stack unavailable |
| OCR vendor comparison | **NO-GO / BLOCKED** | Source bytes and rights/security authorization unavailable |
| Taxiway/holding extraction | **NO-GO / BLOCKED** | Cannot measure completeness or evidence geometry |
| Model training/fine-tuning | **NO-GO** | Rights and representative gold corpus absent |
| Operational release | **NO-GO** | Phase 0 governance, source, quality ownership, and safety criteria unresolved |

### Recommended next experiment

After the exact PDF and approvals arrive:

1. Verify MIME, malware status, page count, header identity, byte size, and SHA-256.
2. Create a pinned `uv` environment for PyMuPDF, an independent PDF parser, Pillow/OpenCV, Tesseract, Shapely/pyproj, and JSON Schema validation.
3. Inventory text spans, fonts, paths, images, clipping, layers, and transforms before rasterization.
4. Define fixed regions for header, runway table, main airport map, and marking/lighting insets.
5. Run native extraction plus Tesseract at 150/300/450/600 DPI.
6. If rights/security permit, run two managed OCR providers on the same whole-page and region inputs.
7. Have two reviewers independently label all five classes and adjudicate differences.
8. Score exact critical tokens, label associations, page-space geometry, topology, latency, review time, and total cost.
9. Select the best **hybrid**, not necessarily the best standalone OCR provider.
10. Only then decide whether learned CV is justified.

### Recommended architecture choice

Proceed with:

- native vector/text parsing as the primary branch;
- self-hosted OCR as an independent fallback/baseline;
- managed OCR behind a provider-neutral adapter only if approved;
- deterministic aviation rules and explicit reject states;
- qualified human review for all requested classes;
- PostgreSQL/PostGIS as the future canonical store;
- evidence-linked observations and bitemporal accepted features;
- JSON/GeoJSON as research projections and AIXM/GeoPackage as later controlled exports.

Do not proceed with OCR-only or VLM-only architecture.

## 11. Phase 1 exit assessment

### Completed

- attached chart inspected and scoped;
- sandbox tool inventory completed;
- provisional corpus package created;
- deterministic normalizer/validator implemented;
- normalized JSON and GeoJSON generated;
- conflicts, provenance limitations, and incomplete classes represented correctly;
- approach matrix, semantics, exports, metrics, cost model, and recommendation documented.

### Not completed because blocked

- original-source checksum and exact source evidence;
- native PDF/vector benchmark;
- OCR comparison;
- page-space annotation and geometry metrics;
- complete taxiway and runway-holding labels;
- reviewer agreement/adjudication metrics;
- measured cost per accepted airport;
- statistically representative multi-airport results.

**Phase 1 status:** `PARTIAL_COMPLETE_WITH_EXTERNAL_BLOCKERS`. The deterministic discovery objective is complete; the extraction-provider benchmark cannot be completed without the source and governance prerequisites.

## 12. References

- [Amazon Textract pricing](https://aws.amazon.com/textract/pricing/)
- [Amazon Textract limits](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html)
- [Azure Document Intelligence pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/)
- [Azure Document Intelligence service limits](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/service-limits?view=doc-intel-4.0.0)
- [Google Document AI pricing](https://docs.cloud.google.com/document-ai/pricing)
- [Google Enterprise Document OCR](https://docs.cloud.google.com/document-ai/docs/enterprise-document-ocr)
- [Google Document AI limits](https://cloud.google.com/document-ai/limits)
- [PyMuPDF documentation](https://pymupdf.readthedocs.io/)
- [Apache PDFBox](https://pdfbox.apache.org/)
- [OpenCV line extraction](https://docs.opencv.org/4.x/dd/dd7/tutorial_morph_lines_detection.html)
- [GDAL Geospatial PDF driver](https://gdal.org/en/stable/drivers/raster/pdf.html)
- [RFC 7946 GeoJSON](https://www.rfc-editor.org/rfc/rfc7946.html)
- [OGC API Features](https://ogcapi.ogc.org/features/overview.html)
- [AIXM](https://www.aixm.aero/)

Web-sourced content was paraphrased for compliance with licensing restrictions. Vendor pricing and limits must be rechecked at procurement and run time.
