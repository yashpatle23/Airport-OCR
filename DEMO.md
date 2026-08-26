# Airport-OCR — demo walkthrough

A 5–8 minute demo showing how the BLR/VOBL aerodrome chart is turned into
structured, searchable data: **PDF → Extract → Identify → Structure → Search**.

> Everything here is **non-operational / research-only** — not authoritative
> aeronautical data, not for navigation. Say this up front.

---

## 0. One-time setup (before the meeting)

```bash
git clone https://github.com/yashpatle23/Airport-OCR.git
cd Airport-OCR
python -m pip install -e ".[dev]"     # or:  export PYTHONPATH=src
```

Runs on Python 3.9+ with **no third-party runtime dependencies**.

---

## 1. The 30-second framing (say this)

- **Problem:** an aerodrome chart is an unstructured PDF. We need machine-readable
  data for five things: **airport, runways, taxiways, runway holding positions,
  and coordinates/elevation**.
- **Approach:** a provenance-first pipeline that extracts *evidence*, validates it
  deterministically, and never fabricates or auto-accepts safety-relevant data.
- **Honesty is a feature:** unreadable/uncertain things stay explicitly blocked or
  marked "needs review" instead of being guessed.

---

## 2. Live demo — one command (can't fail)

```bash
python scripts/demo.py
```

This runs the whole flow on a **real word-sample** bundled in the repo (no PDF or
internet needed) and narrates each stage. Talk through the output:

- **Extract** — ICAO `VOBL`, runway pairs `09L/27R` & `09R/27L`, **43 taxiways**
  parsed from the legend.
- **Identify + validate** — `PASS_WITH_EXPECTED_BLOCKERS`, **0 failures**
  (26 PASS / 2 INFO / 3 expected blockers). Point out the blockers are *honest*
  (source rights, original bytes, holding positions) — not errors.
- **Structure** — one `vobl_package.json` + `vobl_features.geojson` covering all
  five groups.
- **Search** — query by feature type / designator / bounding box.
- **Summary** — a deterministic Markdown summary; note the **3003 ft vs 3001 ft
  elevation conflict is preserved, not silently resolved**.

Artifacts land in `./demo_out/`.

### Optional: run it on the real PDF (adds holding-position candidates)

```bash
pip install pymupdf
python scripts/demo.py --pdf VOBL-ADC.pdf
```

Now the **runway holding positions** step runs: it clusters black marking strokes
into **review-only candidates** (status `NEEDS_REVIEW`) — emphasise these are
candidates, not accepted data, because black linework also includes taxiway
centreline dashes.

---

## 3. Show the web app (optional, ~1 min)

```bash
airport-ocr serve examples/vobl-from-pdf-observations.json --port 8000
# open http://127.0.0.1:8000
```

A dependency-free browser UI: airport card, the **elevation-conflict** banner,
the runway table, the 43 taxiways, a feature **search** box, and a self-contained
**map** of ARP + runway thresholds. No external assets or network calls.

---

## 4. Show the Colab notebook (great for a non-technical audience)

**Open in Colab (full pipeline):**
<https://colab.research.google.com/github/yashpatle23/Airport-OCR/blob/feat/airport-ocr-poc/notebooks/Airport_OCR_Full_Pipeline.ipynb>

`Runtime ▸ Run all` → it downloads the PDF (or you upload it), extracts all five
groups, structures + searches, draws the map, and writes a summary (with an
optional AI paraphrase if an `OPENAI_API_KEY` secret is set).

---

## 5. Show it's engineered, not a script (~1 min)

```bash
pytest -q            # 67 passing tests
```

Point at the package layout:

```
src/airport_ocr/
  intake.py       SHA-256 + file-signature + quarantine (never fakes a scan)
  pdf_words.py    native PDF text -> observations (airport/runways/43 taxiways)
  coordinates.py  deterministic DMS -> CRS84 (keeps the exact source string)
  pipeline.py     validation + normalized JSON + GeoJSON
  holding.py      review-only holding-position candidate detector
  report.py       structured package + summary (+ safe optional-AI prompt)
  search.py       GeoJSON query;   webapp.py / webui.py  offline web app
docs/             research, Phase 0 governance, Phase 1 benchmark
notebooks/        full + step-by-step Colab notebooks
```

Mention the docs: an enterprise architecture study, a Phase 0 governance/rights
package, and a Phase 1 discovery benchmark — the code is the runnable core of a
larger, documented plan.

---

## 6. What was built (summary slide)

| Group | Result |
|---|---|
| Airport | ICAO + name from native text |
| Coordinates/elevation | ARP in CRS84; elevation **conflict preserved** |
| Runways | 2 pairs, 4 thresholds, dims/units validated; coords corrected from native text |
| Taxiways | **43** extracted from the legend (was previously blocked) |
| Runway holding positions | **review-only candidates** from the vector layer |

Plus: intake/SHA-256 provenance, deterministic validation (67 tests), a web app,
two Colab notebooks, and a full research/governance doc set.

---

## 7. Honest limitations (say these — they build trust)

- **Non-operational**; holding positions are **candidates pending review**.
- **Source rights** (AAI/BIAL) and a **named reviewer** are still required before
  the data can be treated as anything beyond research.
- The recorded PDF **SHA-256** anchors provenance; it isn't yet cross-checked
  against a publisher digest.

---

## 8. Likely questions

- *"Is this OCR?"* — No; it reads the PDF's native text layer (exact, no OCR
  errors). OCR is a documented fallback for scanned charts.
- *"Why are holding positions only candidates?"* — They're drawn in the generic
  black line layer (not colour-separable), so we cluster and flag for review
  rather than guess.
- *"Why keep two elevation values?"* — The chart and the eAIP text disagree
  (3003 vs 3001 ft); we never silently pick one for safety-relevant data.
- *"Can it scale to other airports?"* — Yes; the extractor is generic. Per-chart
  tuning + a labelled gold set are the documented next steps.

---

## 9. One-line pitch

> "It turns an aerodrome-chart PDF into validated, searchable JSON for the five
> requested feature groups — and it's honest about what it can't yet verify."
