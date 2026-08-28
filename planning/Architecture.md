# Architecture — Airport-OCR

> Multi-airport, upload-first architecture for non-operational aerodrome-chart
> extraction. Pairs with [`PRD.md`](PRD.md), [`Rules.md`](Rules.md), and the
> detailed [`multi-airport design`](../docs/architecture/MULTI_AIRPORT_DESIGN.md).

## 1. End-to-end flow

```text
                      ┌────────────────┐
 uploaded/sample PDF ►│ CONTROLLED     │ SHA-256, PDF signature, original name,
                      │ INTAKE         │ rights/malware status (record, don't assert)
                      └───────┬────────┘
                              ▼
                      ┌────────────────┐
                      │ CAPABILITY GATE│ positioned native words per page
                      └───────┬────────┘
                     no text  │ supported native text
          OCR-required ◄──────┤
                              ▼
               ┌──────────────────────────────┐
               │ PAGE-AWARE EVIDENCE          │
               │ page + bbox + block/line/text│
               └──────────────┬───────────────┘
                              ▼
       ┌────────────────────────────────────────────┐
       │ DETERMINISTIC LAYOUT ADAPTERS              │
       │ header/ARP/elevation · runway rows/dims    │
       │ taxiway legends/references · vector holds  │
       └──────────────────────┬─────────────────────┘
                              ▼
                      ┌────────────────┐
                      │ DOMAIN ASSEMBLY│ dynamic reciprocal pairs, claims,
                      │ + DIAGNOSTICS  │ explicit null/blocker/candidate states
                      └───────┬────────┘
                              ▼
                      ┌────────────────┐
                      │ NORMALIZE +    │ domain invariants, DMS→CRS84,
                      │ VALIDATE       │ no airport-specific assertions
                      └───────┬────────┘
                              ▼
                ┌─────────────┼──────────────┐
                ▼             ▼              ▼
          JSON/GeoJSON     Search        Package/report
                                             │
                                  optional AI paraphrase
                                             │
                                     artifact ZIP
```

`PDF → Extract → Identify → Structure → Search`. AI never feeds back into data.

## 2. Extraction strategy

### 2.1 Core, adapters, profiles

- **Core:** page-aware words, source evidence, domain assembly and invariants.
- **Adapters:** independent recognizers for chart header, runway row blocks,
  explicit runway-dimension text, width-first taxiway legends and `TWY X`
  references. An adapter may emit facts or a blocker; it may not invent values.
- **Profiles:** optional publisher/sample hints. `auto` is used for uploads.
  `vobl-sample` preserves the known regression case but cannot apply its facts to
  any other ICAO.

### 2.2 Required capability gate

A native-text run requires: unique ICAO, ARP DMS pair, aerodrome-elevation
claim, and at least one complete reciprocal runway pair with threshold DMS.
Textless scanned PDFs stop with `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED`.
Unknown optional layouts remain partial.

### 2.3 Completeness vocabulary

- `EXTRACTED_FROM_NATIVE_TEXT_PENDING_REVIEW`
- `CANDIDATES_PENDING_REVIEW`
- `BLOCKED_LAYOUT_OR_REVIEW_REQUIRED`
- `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED`
- `NOT_EXTRACTED_NOT_ABSENT`

Holding candidates always remain `NEEDS_REVIEW`; missing taxiway widths or TDZ
values are expected blockers rather than fabricated numbers.

## 3. Module map (`src/airport_ocr/`)

| Module | Responsibility | Key entry points |
|--------|----------------|------------------|
| `intake.py` | Untrusted source provenance/integrity | `intake_file` |
| `coordinates.py` | Exact DMS + runway reciprocal rules | `parse_dms`, `reciprocal_designator` |
| `pdf_words.py` | Page-aware adapters → observations/diagnostics | `extract_from_words` |
| `pipeline.py` | Airport-independent normalization/invariant validation | `normalize` |
| `validation.py` | PASS/FAIL/EXPECTED_BLOCKER/INFO report | `Validation` |
| `holding.py` | Page-qualified vector candidates | `holding_candidates` |
| `report.py` | Package, deterministic/AI prompt, safe HTML | `build_package`, `summarize`, `render_html` |
| `search.py` | GeoJSON attribute/bbox query | `search_features` |
| `webapp.py` / `webui.py` | Offline stdlib API + UI/SVG | `serve` |
| `cli.py` / `__main__.py` | Command boundary | five subcommands |

CLI: `intake` · `extract-pdf-words` · `process` · `search` · `serve`.

## 4. Data contracts

1. **Intake manifest** — filename, SHA-256, size, media signature,
   rights/malware state.
2. **Page evidence** — page number + positioned word tuples; no cross-page block
   collisions.
3. **Observation JSON 1.0.0** — source-preserving values, `extraction`
   diagnostics, feature completeness states.
4. **Normalized JSON** — canonical airport/runway/collection model.
5. **GeoJSON** — RFC 7946 CRS84 lon/lat: ARP, thresholds and explicitly labelled
   threshold connectors (not surveyed runway surfaces).
6. **Validation report** — domain failures versus expected blockers.
7. **Package 1.0** — five requested feature groups + optional holding candidates.
8. **Run artifact manifest/ZIP** — all generated evidence and outputs under a
   filename/SHA-derived run ID.

## 5. Colab architecture

The full notebook is generated by `scripts/build_full_pipeline_notebook.py` and
has two explicit source modes:

- **Upload PDF** (default): browser upload button, exactly one PDF, preserve name.
- **Use VOBL sample URL**: explicit optional demo profile; download failures
  instruct the user to switch to upload rather than silently changing input.

The notebook computes `<safe-stem>-<sha8>`, scans all pages, performs a native-
text gate, calls `extract_from_words(..., profile="auto")`, derives example
search/map values from output, and creates one ZIP containing intake, words,
observations, normalized JSON, GeoJSON, validation, package, summaries, HTML and
holding candidates.

## 6. Tech stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Core | Python 3.9+, standard library only | portability/auditability |
| PDF adapter in notebook | PyMuPDF | positioned words + vector drawings |
| Exact numerics | `decimal.Decimal` | source-faithful DMS normalization |
| Geospatial output | RFC 7946 GeoJSON | interoperable lon/lat search projection |
| Web/report | stdlib HTTP, inline SVG/CSS | offline; no external assets/scripts |
| Optional AI | Gemini, lazy notebook import | paraphrase-only, deterministic fallback |
| Tests | pytest | behavioral regression suite |

## 7. Trust boundaries

1. Source PDFs are untrusted; intake does not grant rights or claim malware scan.
2. Chart text/AI output are untrusted and HTML-escaped.
3. Profiles cannot inject facts into a non-matching ICAO.
4. Declared distances are not physical runway dimensions; no substitution.
5. Empty is never absence without explicit evidence.
6. Conflicts stay as separate claims, unselected.
7. Holding geometry and map-label taxiways are candidates until human review.
8. No operational/authoritative mode exists.

## 8. Repository layout

```text
src/airport_ocr/       core package
notebooks/             generated Colab notebooks
scripts/               notebook builder + local VOBL demo
tests/                 behavioral regressions
examples/              VOBL fixtures (case study, not global defaults)
docs/research/         enterprise + multi-airport research
docs/architecture/     POC + multi-airport designs
planning/              PRD, Architecture, Rules, Phases, Design, Memory
```

## 9. Extension points

- OCR/image adapter for scanned PDFs behind the same evidence contract.
- Publisher/layout profiles selected by positive detection, never filename alone.
- Table/vision models that emit candidates, not canonical data.
- SME review UI for acceptance/rejection and conflict adjudication.
- Multi-airport persistence behind package/search interfaces.
