# Airport-OCR — senior demo walkthrough

A 6–10 minute demo of **PDF → Extract → Identify → Structure → Search** for the
five requested aerodrome-chart groups.

> Start with: **non-operational, research-only, not authoritative, not for
> navigation.** Rights and qualified human review remain required.

## 1. Thirty-second framing

- **Problem:** airport charts are visually structured PDFs, not machine-readable
  airport databases.
- **Scope:** airport, runways, taxiways, runway holding positions, and airport
  coordinates/elevation.
- **Safety approach:** preserve source evidence; validate deterministic domain
  invariants; leave missing/uncertain fields blocked or pending review.
- **Key improvement:** the pipeline is no longer a VOBL-shaped algorithm. It now
  accepts uploads, derives the airport/runways from the source, and safely stops
  or stays partial on unsupported layouts.

## 2. Recommended live demo — local FastAPI upload

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --constraint constraints-app.txt -e .
airport-ocr-api --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>, then:

1. Drag/drop or choose exactly one permitted PDF no larger than 5 MiB.
2. Confirm permission and select **Run full pipeline**.
3. Review the overview and eight-stage outline from intake through artifacts.
4. Show the deterministic document summary, document-derived research and
   extraction diagnostics, support limitations, validation/blocker states, and
   provisional search/map.
5. Inspect positioned words, observations, normalized data, GeoJSON, validation,
   candidates, package, manifest, and complete response.
6. Download an individual SHA-qualified artifact, the escaped HTML report, or
   the complete `<run-id>-airport-ocr-results.zip`.

Talk through the gates:

- one canonical picker/drop file state and explicit PDF/permission validation;
- `.pdf` extension, exact PDF part MIME, fixed file-byte limit, and `%PDF-`;
- Pydantic permission/profile validation and versioned OpenAPI/problem details;
- awaited upload reads plus tracked bounded extraction, nested Pydantic
  validation, one JSON encoding pass, a default 64 MiB output cap, and token
  ownership through ASGI body handoff;
- native-text capability check (a scanned PDF stops rather than guessing);
- page/word/drawing/vector limits and deterministic document cleanup;
- full request-scoped intake/evidence/extract/normalize/validate/search/report flow;
- dynamic reciprocal runway pairing and CRS84 coordinates;
- visible expected blockers and review-only holding candidates;
- document-derived research is evidence/diagnostics, not external authority;
- on-demand individual artifacts and an explicit in-browser ZIP action (which
  transiently retains all artifact bytes), plus offline-AI skip (no API key required);
- same-origin UI with no CDN, analytics, persistence, or outbound browser calls.

### Optional immutable Colab demo

The earlier generated notebook remains available for historical/artifact-ZIP
demonstrations:

<https://colab.research.google.com/github/yashpatle23/Airport-OCR/blob/4f180eca52dcbe1d35314b68e8c31ee14bf35056/notebooks/Airport_OCR_Full_Pipeline.ipynb>

It is not the current development environment. Its explicit VOBL sample mode
preserves the known 43-taxiway/conflicting-elevation regression.

## 3. Show the VOMM architecture difference

Use the supplied Chennai/VOMM chart image to explain why a filename upload was
not enough:

- title/header format is `CHENNAI INTL. AIRPORT`, `AD.ELEV. 54ft.`;
- runways are 07/25 and 12/30, not VOBL's 09L/27R and 09R/27L;
- the runway table has THR elevation but no TDZ column;
- declared distances are a separate table and must not be treated as physical
  dimensions;
- taxiways appear through map/hot-spot `TWY` references rather than VOBL's width
  legend;
- holding positions are a line symbol, so vector detections remain candidates.

The committed rights-safe synthetic positioned-word regression returns VOMM,
ARP `[80.1736036111, 12.9950988889]`, 54 FT, 07/25 + 12/30, physical dimensions
3658×45 and 2890×45 m when the explicit labels are present, threshold elevations
43/54/44/48 FT, and **0 validation failures**. Its extraction status is still
`PARTIAL`: missing TDZ/taxiway widths and accepted holding geometry remain
expected blockers rather than being hidden by the zero-failure count.

## 4. Optional no-PDF core regression demo

```bash
python scripts/demo.py
```

This uses the bundled VOBL regression fixture so domain behavior can be shown
without source-PDF rights or network access. Artifacts land in `demo_out/`.

## 5. Optional legacy observation web app

```bash
airport-ocr serve examples/vobl-from-pdf-observations.json --port 8001
# http://127.0.0.1:8001
```

This compatibility surface accepts existing observations rather than a PDF. The
FastAPI application on port 8000 is the primary upload workflow.

## 6. Show the engineering

```bash
pytest -q
python scripts/build_full_pipeline_notebook.py
```

Key files:

```text
src/airport_ocr/api/            FastAPI lifecycle, controllers, Pydantic DTOs
src/airport_ocr/services/       bounded synchronous PyMuPDF application service
src/airport_ocr/static/         central upload and JSON display UI
src/airport_ocr/pdf_words.py    page-aware multi-layout adapters + diagnostics
src/airport_ocr/pipeline.py     airport-independent domain invariants
src/airport_ocr/coordinates.py  exact DMS→CRS84 + reciprocal runway rules
Dockerfile + compose.yaml       portable local runtime/security/resource controls
docs/ + planning/               architecture, API, memory/GC, requirements/decisions
```

## 7. Honest limitations (say these)

- Native-text/layout adapters do not equal universal extraction. Scanned PDFs
  need OCR; unknown optional layouts stay partial.
- Explicit `TWY X` references are candidate inventory, not proof of completeness.
- Holding clusters can include other black linework and need human review.
- No surveyed runway polygons; connectors join source thresholds only.
- No operational mode exists. Source rights and an accountable reviewer remain
  mandatory.

## 8. Likely questions

- **“Can I upload another airport?”** Yes. Upload is the default. Supported
  native-text layouts are structured; unsupported required layouts stop safely;
  optional gaps remain visible blockers.
- **“Is this OCR?”** Not yet. The current branch reads exact native PDF words.
  OCR is a planned adapter for scanned documents.
- **“Why not use AI to read everything?”** AI is only an optional downstream
  paraphrase. It cannot create/correct/select aeronautical facts.
- **“Why no TDZ value for VOMM?”** The supplied runway table does not contain a
  TDZ column. The system returns `not extracted`; it does not invent one.
- **“Why are holding positions candidates?”** The chart represents them as
  linework among other black vectors. AIXM also distinguishes the operational
  holding position from its marking geometry; review is required.

## One-line pitch

> Airport-OCR accepts an aerodrome-chart PDF, extracts the five requested groups
> into searchable JSON/GeoJSON, and makes every unsupported or unverified fact
> visible instead of guessing.
