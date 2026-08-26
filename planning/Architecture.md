# Architecture — Airport-OCR

> How the system is put together: the end-to-end flow, the module map, the tech
> stack, and the trust boundaries. Pairs with [`PRD.md`](PRD.md) (the *what*) and
> [`Rules.md`](Rules.md) (the *constraints*).

---

## 1. End-to-end flow

```
                    ┌─────────────┐
   source PDF  ───► │   INTAKE    │  SHA-256, magic-byte sniff, quarantine copy,
                    │ (untrusted) │  records malware/rights status (never asserts)
                    └──────┬──────┘
                           │  (off-runtime: PyMuPDF word/vector dump)
                           ▼
                    ┌─────────────┐
                    │   EXTRACT   │  pdf_words: header/ARP/elevation/runway table
                    │             │  + 43 taxiways from legend
                    │             │  holding: black-linework candidate clustering
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │  IDENTIFY / │  coordinates: DMS→Decimal→CRS84
                    │  NORMALIZE  │  pipeline.normalize()
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │  VALIDATE   │  ICAO format, reciprocal pairs, units,
                    │             │  conflict preservation, completeness status
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │  STRUCTURE  │  report.build_package → normalized JSON +
                    │             │  RFC 7946 GeoJSON FeatureCollection
                    └──────┬──────┘
                           ▼
              ┌────────────┼─────────────┬───────────────┐
              ▼            ▼             ▼               ▼
        ┌─────────┐  ┌──────────┐  ┌──────────┐   ┌──────────────┐
        │ SEARCH  │  │ WEB APP  │  │ HTML     │   │ AI SUMMARY   │
        │ filters │  │ API + UI │  │ report   │   │ (paraphrase- │
        │         │  │ (offline)│  │render_html│  │  only, opt.) │
        └─────────┘  └──────────┘  └──────────┘   └──────────────┘
```

`PDF → Extract → Identify → Structure → Search` — the AI summary sits **after**
structuring and only paraphrases the finished package (it never feeds back into
the data).

## 2. Module map (`src/airport_ocr/`)

| Module | Responsibility | Key entry points |
|--------|----------------|------------------|
| `intake.py` | Provenance & integrity of untrusted source files | intake manifest (SHA-256, signature, quarantine) |
| `coordinates.py` | Deterministic DMS parsing | DMS string → `Decimal` lon/lat (`OGC:CRS84`) |
| `pdf_words.py` | Native PDF text → observations | `extract_from_words(dump, dataset_id=...)` |
| `pipeline.py` | Normalize + orchestrate | `normalize(document)` → `(normalized, geojson, report)` |
| `validation.py` | Domain rules & completeness semantics | validation report with statuses |
| `holding.py` | Review-only holding candidates | `holding_candidates(segments, taxiway_labels, ...)` |
| `report.py` | Structuring, summary, HTML | `build_package`, `summarize`, `ai_summary_prompt`, `render_html` |
| `search.py` | Query the GeoJSON projection | `search_features(geojson, feature_type=, airport=, designator=, bbox=)` |
| `webapp.py` | Stdlib HTTP API | `/api/health|airport|features|validation|search|process` |
| `webui.py` | Offline browser UI | self-contained HTML/SVG, no external assets |
| `cli.py` / `__main__.py` | Command-line entry | subcommands below |
| `__init__.py` | Package metadata | `__version__`, `OPERATIONAL_USE = False` |

### CLI surface
`intake` · `process` · `search` · `serve` · `extract-pdf-words`
(also runnable as `python -m airport_ocr ...`).

## 3. Data contracts

- **Observations** — intermediate dict emitted by extraction (airport, runways,
  taxiways, holding, coordinates), each field annotated with provenance.
- **Normalized JSON** — validated canonical document.
- **GeoJSON** — RFC 7946 `FeatureCollection` (ARP, runway thresholds, …);
  `OGC:CRS84` lon/lat order.
- **Validation report** — pass/fail plus completeness statuses
  (`EXTRACTED_FROM_NATIVE_TEXT_PENDING_REVIEW`, `NOT_EXTRACTED_NOT_ABSENT`,
  `BLOCKED_SOURCE_BYTES_REQUIRED`, `CANDIDATES_PENDING_REVIEW`, …).
- **Package** — `build_package(normalized, report, holding_candidates=None)`;
  consumed by `summarize`, `ai_summary_prompt`, and `render_html`.

## 4. Tech stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | **Python 3.9+** | Ubiquitous in data/GIS/aviation tooling |
| Core runtime deps | **none** | Portability, auditability, safety (`dependencies = []`) |
| PDF word/vector dump | **PyMuPDF** (off runtime path) | Only to produce the upstream dump; not imported by the core |
| Numerics | `decimal.Decimal` | Exact DMS→decimal, no float drift |
| Web | **stdlib `http.server`** | Zero-dep local API + UI |
| Map | **inline SVG** | Offline, no tile/network dependency |
| Report | self-contained **HTML + inline CSS** | Shareable, no external assets/scripts |
| AI summary (optional) | **Google Gemini** (`google-generativeai`, `models/gemini-flash-latest`) | Paraphrase-only; optional and sandboxed |
| Tests | **pytest** | Behavioral tests |
| Packaging | `pyproject.toml` (setuptools), `airport-ocr` console script | Standard, `pip install -e ".[dev]"` |
| Demo | **Google Colab** notebooks | Reproducible, no local setup |

## 5. Repository layout

```
Airport-OCR/
├── src/airport_ocr/      core package (see module map)
├── tests/                behavioral tests (pytest)
├── examples/             provisional VOBL observation fixtures
├── notebooks/            Colab: Full_Pipeline + step-by-step
├── scripts/              demo.py
├── docs/
│   ├── research/         enterprise extraction research
│   ├── phase-0/          governance, rights, source intake (BLOCKED)
│   ├── phase-1/          discovery benchmark, results, tool inventory (PARTIAL)
│   └── architecture/     POC_DESIGN.md, trust boundaries
├── planning/             PRD, Architecture, Rules, Phases, Design, Memory (this set)
├── DEMO.md · README.md · LICENSE · pyproject.toml
```

## 6. Trust boundaries (critical)

1. **Source files are untrusted.** Intake never scans or grants rights; it only
   records status. Parsing/publication is gated on rights + review.
2. **Chart text and AI output are untrusted.** All values are HTML-escaped in
   the UI and report; the web UI ships no external assets, scripts, or network calls.
3. **AI is downstream and read-only.** It paraphrases the structured package and
   must not invent, correct, or select values.
4. **Blocked ≠ empty.** Empty collections mean `NOT_EXTRACTED_NOT_ABSENT`.
5. **Conflicts are preserved.** Contradictory source claims (e.g. elevation
   `3003 ft` vs `3001 FT`) are stored unselected for human adjudication.

## 7. Extension points (deliberately replaceable)

- OCR / computer-vision extractors → feed the same observation contract.
- Additional feature extractors (stop bars, no-entry, aprons) → new candidate producers.
- Alternative AI providers → same `ai_summary_prompt(package)` contract.
- Persistent storage / multi-airport corpus → behind the search/report layer.
