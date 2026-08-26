# Phases — Airport-OCR

> The project broken into shippable stages. Each phase has a goal, concrete
> deliverables, and an exit gate. Status reflects reality as of the last
> [`Memory.md`](Memory.md) update. Legend: ✅ done · 🟡 partial · ⛔ blocked · ⬜ planned.

---

## Phase 0 — Governance & source access ⛔ BLOCKED

**Goal:** establish the rights, provenance, and review controls that make any
extraction defensible before parsing a real chart.

**Deliverables**
- Governance charter, decision register, quality/acceptance & review policy.
- Source register + rights manifest; controlled intake (SHA-256, signature
  sniff, quarantine).
- Gold-corpus policy.

**Exit gate:** original PDF bytes + hash recorded, **source rights confirmed**,
and named accountable owners in place.

**Status:** BLOCKED — SHA-256 recorded
(`ef0541fca479c35eb9d47208fddf12d59c011294e047ebfa5c4ac55dc060bf05`), but source
**rights are unconfirmed** and `original_bytes_available` stays `False`.
Governance docs live in `docs/phase-0/`.

---

## Phase 1 — Discovery benchmark & deterministic core 🟡 PARTIAL

**Goal:** prove the safe-to-run spine — deterministic normalization, validation,
exports, search — and benchmark discovery scope.

**Deliverables**
- ✅ `coordinates.py` (DMS→Decimal→CRS84), `pipeline.normalize`, `validation.py`.
- ✅ Normalized JSON + RFC 7946 GeoJSON exports.
- ✅ `search.search_features` (feature type, airport, designator, bbox).
- ✅ Benchmark scope, tool inventory, baseline result, validation report
  (`docs/phase-1/`).

**Exit gate:** deterministic pipeline green on the VOBL fixture with
`PASS_WITH_EXPECTED_BLOCKERS`; PDF/OCR/CV benchmarking scoped.

**Status:** PARTIAL — deterministic normalization complete; PDF/OCR/CV
benchmarking and complete taxiway/holding extraction remain blocked on Phase 0.

---

## Phase 2 — Native PDF text extraction ✅ DONE (within limits)

**Goal:** turn a PyMuPDF word dump into observations without adding runtime deps.

**Deliverables**
- ✅ `pdf_words.extract_from_words(dump, dataset_id=...)` — airport header, ARP,
  elevation, runway table, and the **43 VOBL taxiways** (B3 = 15 m, rest 23 m)
  from the pavement legend.
- ✅ `extract-pdf-words` CLI subcommand.

**Exit gate:** word-dump → observations → normalize/validate round-trips green.

**Status:** DONE. Runway holding positions intentionally stay
`BLOCKED_SOURCE_BYTES_REQUIRED` (identifiers/associations need the marking
geometry layer, not the word stream).

---

## Phase 3 — Runway holding positions (review-only candidates) 🟡 PARTIAL

**Goal:** surface holding-position **candidates** from vector linework for human
review — without ever presenting them as accepted data.

**Deliverables**
- ✅ `holding.holding_candidates(segments, taxiway_labels, ...)` clustering
  black linework (`#000000`); each candidate `NEEDS_REVIEW`.
- ✅ 25 candidates produced on the real VOBL PDF (`CANDIDATES_PENDING_REVIEW`).

**Exit gate:** candidates generated + clearly quarantined from the accepted set.

**Status:** PARTIAL by design — accepted holding set stays blocked pending
qualified review. Color-separable markings (stop bar `#ff0000`, no-entry
`#bf00ff`) are out of scope.

---

## Phase 4 — Interfaces: CLI, web app, report ✅ DONE

**Goal:** make the pipeline usable and demoable end to end.

**Deliverables**
- ✅ CLI: `intake`, `process`, `search`, `serve`, `extract-pdf-words`.
- ✅ Offline web app: stdlib HTTP API + browser UI + inline SVG map.
- ✅ `report.build_package`, `summarize`, `render_html(package, ai_text=None)` —
  self-contained styled HTML card (escaped, no external assets).

**Exit gate:** `serve` renders the VOBL package; `render_html` produces a
shareable report; behavioral tests green.

**Status:** DONE.

---

## Phase 5 — Demo & reproducibility ✅ DONE

**Goal:** one-click reproducible demo for reviewers/seniors.

**Deliverables**
- ✅ Colab: `Airport_OCR_Full_Pipeline.ipynb` (`PDF → … → Search` + summary +
  polished `render_html`), plus step-by-step notebook.
- ✅ `DEMO.md` + `scripts/demo.py`.
- ✅ Optional **Gemini** AI paraphrase (`models/gemini-flash-latest`), with
  deterministic fallback.

**Exit gate:** notebook runs top-to-bottom on VOBL and writes JSON, GeoJSON, and
`vobl_report.html`.

**Status:** DONE.

---

## Phase 6 — Planning & documentation set ✅ DONE

**Goal:** capture intent, architecture, rules, staging, design, and memory so the
project is legible to humans and AI tools across sessions.

**Deliverables**
- ✅ `planning/` : PRD, Architecture, Rules, Phases, Design, Memory.

**Exit gate:** all six docs committed and pushed.

**Status:** DONE (this document set).

---

## Future phases (⬜ planned, gated on Phase 0 rights)

| Phase | Goal | Blocked on |
|-------|------|-----------|
| **7 — OCR / CV extraction** | Symbol & geometry extraction (holding, stop bars, aprons) via OCR/computer vision behind the observation contract | Source bytes + rights (Phase 0) |
| **8 — Multi-airport corpus** | Generalize beyond VOBL; persistent, searchable store | Rights per source; storage design |
| **9 — Review workflow** | UI/flow for SMEs to accept/reject candidates and adjudicate conflicts | Phase 3 candidates + reviewer roles |
| **10 — Hardening & packaging** | Perf, CI gates, release packaging, richer validation | Phases 7–9 |

> No future phase may relax the safety rules in [`Rules.md`](Rules.md) §1. New
> extraction capability increases what we *record*, never what we *assert*.
