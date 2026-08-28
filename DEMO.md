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

## 2. Recommended live demo — Colab upload

Open:

<https://colab.research.google.com/github/yashpatle23/Airport-OCR/blob/4f180eca52dcbe1d35314b68e8c31ee14bf35056/notebooks/Airport_OCR_Full_Pipeline.ipynb>

Then:

1. `Runtime → Run all`.
2. Set `SOURCE_MODE = Upload PDF` (the default).
3. Tick `I_HAVE_PERMISSION_TO_PROCESS`.
4. Click the browser **Choose Files** upload button and select exactly one PDF.
5. At the end, download `<source>-<sha8>-airport-ocr-results.zip`.

Talk through the gates:

- SHA-256 + PDF signature + original filename;
- native-text capability check (a scanned PDF stops and requests a future OCR
  adapter rather than guessing);
- page-aware header/runway/taxiway adapters;
- dynamic reciprocal runway pairing and CRS84 coordinates;
- expected blockers for values not present in a layout;
- all-page black-linework holding **candidates**, all `NEEDS_REVIEW`;
- dynamic search/map/report; optional Gemini paraphrase using `GEMINI_API_KEY`;
- one complete artifact ZIP.

### Optional deterministic VOBL demo

Choose `Use optional VOBL sample URL`. This explicit profile demonstrates the
known VOBL result, including 43 legend taxiways and the unresolved 3003/3001 FT
external-claim conflict. If AAI blocks the download, switch to Upload PDF.

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

## 4. Local no-network regression demo

```bash
git clone https://github.com/yashpatle23/Airport-OCR.git
cd Airport-OCR
git checkout 4f180eca52dcbe1d35314b68e8c31ee14bf35056  # immutable reviewed implementation
python -m pip install -e ".[dev]"
python scripts/demo.py
```

This intentionally remains the bundled **VOBL regression fixture** so a demo can
run without source PDF/network access. Artifacts land in `demo_out/`.

With a permitted VOBL PDF and PyMuPDF:

```bash
pip install pymupdf
python scripts/demo.py --pdf VOBL-ADC.pdf
```

## 5. Show the offline web app

```bash
airport-ocr serve examples/vobl-from-pdf-observations.json --port 8000
# http://127.0.0.1:8000
```

The title, airport name, elevation state, runway table, and map are data-driven;
they no longer display VOBL/Bengaluru when processing another airport. The UI
has no external assets/network calls.

## 6. Show the engineering

```bash
pytest -q
python scripts/build_full_pipeline_notebook.py
```

Key files:

```text
src/airport_ocr/pdf_words.py   page-aware multi-layout adapters + diagnostics
src/airport_ocr/pipeline.py    airport-independent domain invariants
src/airport_ocr/coordinates.py exact DMS→CRS84 + reciprocal runway rules
src/airport_ocr/holding.py     page-qualified review-only vector candidates
src/airport_ocr/report.py      package, summary, escaped self-contained HTML
src/airport_ocr/web*.py        dynamic offline API/UI
scripts/build_full_pipeline_notebook.py  deterministic Colab generator
planning/ + docs/              PRD, architecture, rules, phases, research, memory
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
