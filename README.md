# Airport-OCR

Turn aerodrome-chart PDFs into validated, normalized, searchable research data — safely.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yashpatle23/Airport-OCR/blob/4f180eca52dcbe1d35314b68e8c31ee14bf35056/notebooks/Airport_OCR_Full_Pipeline.ipynb)

**Recommended:** open the [full upload-first Colab pipeline](notebooks/Airport_OCR_Full_Pipeline.ipynb),
choose **Upload PDF**, tick the permission acknowledgement, and upload one
native-text aerodrome chart. The notebook executes:

```text
PDF → Extract → Identify → Structure → Search
```

It produces a single ZIP containing intake provenance, positioned words,
observations, normalized JSON, GeoJSON, validation, a structured package,
deterministic/optional-AI summaries, an HTML report, and review-only holding
candidates. An explicit optional mode downloads the VOBL sample chart.

> **Non-operational / research-only.** Nothing emitted by this project is
> authoritative aeronautical data, and it must never be used for navigation or
> operational decisions. Uploading a PDF does not grant source rights. Every
> result remains provisional until rights and qualified aviation review are
> recorded.

## Problem scope

Aerodrome charts are visually structured PDFs containing text, tables, vector
linework, and symbols. Airport-OCR extracts only five groups:

1. airport identity;
2. runways;
3. taxiways;
4. runway holding positions;
5. airport coordinates/elevation.

The project is provenance-first: source strings are retained, missing optional
values become explicit blockers, and conflicting claims are never silently
resolved.

## What works now

- **Upload-first Colab UX** — browser upload button, exact-one-PDF/signature gate,
  preserved original name, SHA-qualified run ID, all-page processing, dynamic
  search/map labels, and one complete result ZIP.
- **Controlled intake** — SHA-256, magic-byte detection, extension mismatch, and
  optional content-addressed quarantine. Intake records malware/rights state; it
  never claims to scan or grant rights.
- **Page-aware native-text extraction** — positioned PyMuPDF words retain page
  identity. Header coordinates are associated with a unique non-runway header
  region rather than selected globally. Independent adapters detect AAI-style
  chart IDs/titles, ARP, `AD ELEV` variants, arbitrary runway rows, explicit
  physical dimensions, strict width-first taxiway lists, and explicit `TWY X`
  references.
- **Airport-independent domain assembly** — dynamic reciprocal runway pairing
  supports `07/25`, `12/30`, `09L/27R`, and other valid 01–36 L/R/C pairs.
- **Deterministic coordinate normalization** — exact DMS parsing with `Decimal`;
  RFC 7946/CRS84 longitude-latitude output with original strings preserved.
- **Invariant validation** — validates ICAO, reciprocal pairs, units/ranges,
  elevation claim state, and collection completeness—not VOBL-specific values.
- **Taxiway honesty** — a structured width legend produces reviewed-pending
  features; hot-spot/map text references become candidates with unknown width,
  never a false complete inventory.
- **Holding-position boundary** — page-qualified black-linework clusters remain
  `NEEDS_REVIEW`; accepted positions stay blocked-not-absent.
- **Exports/search/report** — normalized JSON, GeoJSON, attribute/bbox search,
  self-contained safe HTML, and optional Gemini paraphrase.
- **Offline web app** — stdlib API + dynamic browser UI + inline SVG, with no
  third-party runtime dependencies or external UI assets.

## Honest support boundary

"Upload any airport map" means the notebook will intake and diagnose it safely;
it does **not** mean every world-wide layout can be fully extracted today.

- **Supported:** native-text AAI/ICAO-style aerodrome charts matching the current
  deterministic adapters.
- **Partial:** unknown optional layouts (e.g. no supported taxiway legend) retain
  `PARTIAL`, `CANDIDATES_PENDING_REVIEW`, or
  `BLOCKED_LAYOUT_OR_REVIEW_REQUIRED`.
- **Stopped safely:** scanned/textless PDFs return
  `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED`; OCR is a future adapter.
- Declared TORA/TODA/ASDA/LDA values are **never** substituted for physical
  runway dimensions.
- Threshold connectors are labelled derived connectors, not surveyed runway
  surfaces.

## Case studies

### VOBL — Bengaluru regression/sample profile

`AD 2 VOBL 1-101`: 09L/27R and 09R/27L; 43 width-legend taxiways; ARP
`[77.7055555556, 13.1988888889]`. The explicit sample profile preserves the
separate 3003/3001 FT elevation claims unresolved.

### VOMM — Chennai multi-layout check

The attached `AD 2 VOMM 1-101` layout exercises a different title/elevation
format, runways 07/25 and 12/30, one THR-elevation column (no TDZ column),
separate declared-distance data, explicit hot-spot `TWY` references, and
cartographic holding symbols. The committed rights-safe synthetic check produces:

- ARP `[80.1736036111, 12.9950988889]` from
  `12°59′42.356″N 080°10′24.973″E`;
- 54 FT single-source elevation;
- 07/25 (3658×45 m) and 12/30 (2890×45 m);
- threshold elevations 43/54/44/48 FT;
- missing TDZ/taxiway widths as expected blockers, not fabricated values.

This is a structural regression from a committed, rights-safe synthetic
positioned-word fixture shaped from the supplied chart image; it is not an
operational dataset or a substitute for running the original permitted PDF.
Extraction remains visibly `PARTIAL` because TDZ values, complete taxiway
inventory/widths, and accepted holding geometry are unavailable.

## Install

```bash
python -m pip install -e ".[dev]"
# or: export PYTHONPATH=src
```

Core requires Python 3.9+ and has **zero third-party runtime dependencies**.
PyMuPDF, matplotlib, and Gemini are optional notebook/adaptor dependencies.

## CLI usage

```bash
# Inspect an untrusted source
airport-ocr intake chart.pdf --manifest out/intake.json

# Produce a PyMuPDF words dump outside the zero-dependency core, then extract
airport-ocr extract-pdf-words chart-words.json \
  --metadata out/intake.json --output out/observations.json

# Normalize, validate, export, search
airport-ocr process out/observations.json --output-dir out
airport-ocr search out/features.geojson --feature-type runway_threshold
airport-ocr search out/features.geojson --designator 07
airport-ocr search out/features.geojson --bbox 80.15,12.98,80.20,13.02

# Offline app
airport-ocr serve out/observations.json --port 8000
```

`extract-pdf-words` defaults to `profile=auto`. `--profile vobl-sample` is only
for the VOBL regression chart, must be selected explicitly, and refuses non-VOBL
input. Missing metadata never activates compatibility facts. Optional external
elevation claims are explicit CLI/user inputs; generic mode never injects one.

Produce a page-aware words dump with PyMuPDF:

```python
import json, pymupdf

doc = pymupdf.open("airport-chart.pdf")
pages = [
    {"page": i, "size": [p.rect.width, p.rect.height], "words": p.get_text("words")}
    for i, p in enumerate(doc)
]
json.dump(pages, open("chart-words.json", "w"))
```

## Web API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | liveness + dataset identity |
| GET | `/api/airport` | normalized airport/runways/collections |
| GET | `/api/features` | GeoJSON `FeatureCollection` |
| GET | `/api/validation` | validation report |
| GET | `/api/search` | filters: `feature_type`, `airport`, `designator`, `bbox` |
| POST | `/api/process` | stateless observation normalization |

The browser title/name/elevation state is now data-driven; it no longer displays
VOBL/Bengaluru for another airport.

## Exit codes

`airport-ocr process` exits `0` on `PASS_WITH_EXPECTED_BLOCKERS`, `1` on real
validation failures, and `3` under `--fail-on-blockers` while expected blockers
remain.

## Project layout

```text
src/airport_ocr/       intake, page-aware extraction, validation, exports, search, UI
notebooks/             upload-first Full Pipeline + smaller step-by-step notebook
scripts/               deterministic notebook builder + local VOBL demo
examples/              VOBL regression + rights-safe synthetic VOMM fixtures
docs/research/         enterprise + multi-airport extraction research
docs/architecture/     POC + multi-airport adapter/capability design
docs/phase-0, phase-1/ governance and historical benchmark evidence
planning/              PRD, Architecture, Rules, Phases, Design, Memory
```

Regenerate the full notebook (do not hand-edit notebook JSON):

```bash
python scripts/build_full_pipeline_notebook.py
```

## Testing

```bash
pytest -q
```

## Status / next boundary

The deterministic native-text multi-layout increment is implemented. Complete
OCR/CV, complete taxiway map-label extraction, accepted holding geometry, source
rights, and an accountable SME review workflow remain future/gated work. See
[`planning/`](planning/), the
[multi-airport design](docs/architecture/MULTI_AIRPORT_DESIGN.md), and the
[multi-airport research](docs/research/MULTI_AIRPORT_EXTRACTION_RESEARCH.md).

## License

Code is MIT licensed. It does **not** grant rights to source charts or AIP/eAIP
material; see [`LICENSE`](LICENSE) and `docs/phase-0`.
