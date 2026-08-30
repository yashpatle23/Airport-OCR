# Multi-airport aerodrome-chart extraction research

**Status:** architecture research for a non-operational, research-only extractor.
**Case studies:** VOBL (Bengaluru) and the user-supplied VOMM (Chennai) chart image.
**Last updated:** 2026-08-19.

> Nothing in this document or the implementation is authoritative aeronautical
> data. Outputs require source-rights confirmation and qualified human review and
> must not be used for navigation.

## 1. Why the VOBL-only implementation failed on VOMM

The previous extractor did not merely contain a VOBL example; it encoded the
example as its algorithm. It fixed the airport name to Bengaluru, built only
`09L/27R` and `09R/27L`, injected `4000 × 45 M`, added a separate 3001 FT
VOBL elevation claim, recognized only `AD ELEVATION.`, and extracted taxiways
only from a VOBL width-first pavement legend. The validator then required those
exact facts.

The attached VOMM chart uses another legitimate layout:

- title/header: **CHENNAI INTL. AIRPORT**, `AD 2 VOMM 1-101`, ARP
  `12°59'42.356"N 80°10'24.973"E`, `AD.ELEV. 54ft.`;
- four runway-direction rows: `07`, `25`, `12`, `30`, paired as `07/25` and
  `12/30`;
- runway dimensions are printed on the map while declared distances occupy a
  separate table;
- taxiways are primarily map labels and hot-spot references, not a VOBL-style
  width legend;
- runway-holding positions are shown as a cartographic line symbol and named in
  the legend, so text alone cannot establish accepted point/line geometry.

A filename upload button alone would therefore be dangerous: the old code could
accept another PDF and silently emit VOBL facts. Generic ingestion must be
paired with generic parsing or a clear **unsupported/partial** outcome.

## 2. Standards and data-model findings

- ICAO Annex 4 defines the aeronautical-chart family, while Annex 14 covers
  aerodrome physical characteristics and visual aids. The implementation must
  not assume every publisher positions the same required information in the
  same PDF blocks. See the [ICAO Annex 4 catalogue](https://store.icao.int/en/annex-4-aeronautical-charts)
  and [ICAO Annex 14 overview](https://www.icao.int/sites/default/files/postalhistory/annex_14_aerodromes.htm).
- AIXM distinguishes the operational **TaxiHoldingPosition** from its marking
  geometry. A holding position may be encoded as a point, while the corresponding
  marking is represented as line geometry. Consequently, nearest-label/vector
  clusters must remain review-only candidates rather than accepted holding
  positions. See [EUROCONTROL's AIXM/AMD holding-position encoding guidance](https://ext.eurocontrol.int/aixm_confluence/display/ACGAMD/TaxiwayHoldingPosition+encoding).
- RFC 7946 GeoJSON uses WGS 84 decimal coordinates in **longitude, latitude**
  order. Source DMS strings should remain preserved alongside normalized values.
  See [RFC 7946](https://www.ietf.org/rfc/rfc7946.txt) and the
  [OGC GeoJSON summary](https://www.ogc.org/standards/json-fg/).
- The official AAI search result for the Chennai chart identifies it as VOMM and
  exposes `ELEV. 54ft.`, corroborating the attached chart header. See the
  [AAI VOMM aerodrome chart](https://aim-india.aai.aero/eaip/eaip-v2-06-2025/eAIP/VOMM-ADC.pdf?amdt=show).

## 3. PDF extraction findings

PDF text is not a logical document tree. It is a set of positioned glyphs/words,
and reading order can differ from visual order. PyMuPDF's
[`get_text("words")`](https://pymupdf.readthedocs.io/en/latest/recipes-text.html)
returns each word with its page rectangle, which is the right primitive for
reconstructing headers and table rows. Its
[text-extraction appendix](https://pymupdf.readthedocs.io/en/latest/app1.html)
also documents block/line extraction behavior.

The safe extraction stack is therefore:

1. **Native-text gate** — count words per page; if none exist, stop with
   `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED` rather than guess.
2. **Page-aware evidence layer** — preserve page, bbox, block, line and source
   text. Never merge equal block numbers from different pages.
3. **Layout adapters** — independent recognizers for chart identity/header,
   runway rows, runway-dimension labels, taxiway legends/references and vector
   holding candidates.
4. **Domain assembly** — pair runway ends with reciprocal-designator rules;
   keep missing optional values null and status-bearing.
5. **Validation** — enforce domain invariants, not one airport's values.
6. **Human review boundary** — incomplete taxiways and all inferred holding
   geometry stay pending review.

Table extraction is spatial: values derive meaning from row and column headers,
not flattened reading order. Recent document-extraction work likewise uses
multi-stage layout/table/OCR pipelines rather than plain OCR alone; see
[PdfTable's overview](https://arxiv.org/html/2409.05125) and this
[NVIDIA survey of PDF extraction approaches](https://developer.nvidia.com/blog/approaches-to-pdf-data-extraction-for-information-retrieval/).
The first implementation remains deterministic/native-text only; OCR and model
inference stay a future adapter behind the same evidence contract.

## 4. Chosen architecture

### Core versus profiles

The core is airport-independent. A profile may supply known publisher metadata
or parsing hints, but it must never inject airport facts into an unrelated run.
VOBL remains a regression/sample profile; uploaded files use `auto` and facts
are derived from their own words.

### Confidence/completeness states

- `EXTRACTED_FROM_NATIVE_TEXT_PENDING_REVIEW` — value directly read from text.
- `CANDIDATES_PENDING_REVIEW` — labels/geometry heuristically associated.
- `BLOCKED_LAYOUT_OR_REVIEW_REQUIRED` — feature likely exists, but the available
  adapter cannot structure it safely.
- `NOT_EXTRACTED_NOT_ABSENT` — an empty array is explicitly not evidence of
  absence.
- `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED` — no native text; deterministic branch
  stops before normalization.

### Generic validation invariants

- ICAO: four uppercase letters.
- At least one runway pair; exactly two unique, reciprocal ends per pair; no end
  reused across pairs.
- Dimensions, when extracted, are positive metric values; missing dimensions are
  an expected blocker, never fabricated from TORA/LDA.
- Threshold coordinates parse as DMS and normalize to valid CRS84 values.
- Threshold elevation is positive FT when present; TDZ elevation may be absent
  and becomes an expected blocker.
- One elevation claim → `SINGLE_SOURCE`; differing claims → unresolved conflict
  and no selected value.
- Taxiway widths may be unknown for map-label candidates. This is partial data,
  not a validation failure and not a complete inventory.

## 5. Colab UX decision

The full notebook becomes **upload-first**:

1. Select `Upload PDF` (default) or explicit `Use VOBL sample URL`.
2. Upload exactly one PDF; preserve its original name and verify `%PDF-` through
   controlled intake.
3. Derive a collision-safe run ID from sanitized filename + SHA-256 prefix.
4. Show capability diagnostics before normalization.
5. Use dynamic ICAO/runway/map/search values, never `VOBL`, `09L`, or a Bengaluru
   bbox in generic cells.
6. Generate all artifacts with the run ID and download one ZIP, including the
   intake manifest, words, observations, normalized JSON, GeoJSON, validation,
   package, summaries, HTML report, and review-only holding candidates.

## 6. Honest support boundary

This change targets native-text AAI/ICAO-style aerodrome charts and removes the
harmful VOBL constants. It does **not** guarantee that every airport PDF layout
in the world is fully extracted. Unknown native-text layouts produce partial or
blocked collections; scanned PDFs stop with an OCR-required diagnostic. Adding
OCR, table models, publisher profiles and SME adjudication are separate future
phases.

---

*Content from linked sources was rephrased for compliance with licensing restrictions.*
