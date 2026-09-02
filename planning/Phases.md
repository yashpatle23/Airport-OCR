# Phases — Airport-OCR

> Shippable stages with honest gates. ✅ done · 🟡 partial · ⛔ blocked · ⬜ planned.

## Phase 0 — Governance & source access ⛔ BLOCKED

**Goal:** rights, provenance, and accountable review controls.

**Done:** governance charter, decision/quality policies, controlled intake,
source register, gold-corpus policy. VOBL SHA-256 is recorded.

**Exit gate:** rights confirmed and named accountable owners/reviewers.

**Still blocked:** AIP/eAIP processing/publication rights remain unconfirmed.
Uploading a file does not close this gate.

## Phase 1 — Deterministic domain core ✅ DONE (within research scope)

**Goal:** source-preserving normalization, validation, JSON/GeoJSON, search.

**Delivered:** `coordinates.py`, `pipeline.normalize`, `validation.py`, RFC 7946
exports, attribute/bbox search, explicit blocker/conflict semantics.

**Exit gate met:** supported observations normalize deterministically with no
real validation failures; blockers remain visible.

## Phase 2 — Native-text extraction adapters ✅ DONE (multi-layout increment)

**Goal:** convert page-aware PyMuPDF words into observations without adding core
runtime dependencies or airport-specific global defaults.

**Delivered:**
- chart ID/title, ARP and `AD ELEV`/`AD ELEVATION` variants;
- arbitrary reciprocal runway pairing + source threshold rows;
- explicit physical runway-dimension labels (never declared-distance inference);
- VOBL width-first taxiway legend + explicit `TWY X` reference candidates;
- page evidence, extraction profile/diagnostics, partial/unsupported states;
- VOBL sample compatibility isolated to `vobl-sample`.

**Exit gate met:** VOBL regressions remain green; the committed rights-safe
synthetic VOMM positioned-word fixture extracts VOMM/Chennai, 07/25 + 12/30,
ARP/elevation, dimensions and THR values with 0 failures while retaining
`PARTIAL`. Missing VOMM TDZ/taxiway widths and accepted holds remain blockers.

## Phase 3 — Holding positions 🟡 PARTIAL BY DESIGN

**Goal:** surface possible holding markings without calling them accepted data.

**Delivered:** all-page black-linework clustering, page-qualified IDs/evidence,
nearest known taxiway association, `NEEDS_REVIEW` candidates.

**Exit gate remaining:** qualified SME acceptance/rejection workflow and
point/marking geometry adjudication. Candidates cannot be promoted by code.

## Phase 4 — Interfaces ✅ DONE

**Delivered:** CLI (`intake`, `extract-pdf-words`, `process`, `search`, `serve`),
dynamic stdlib web API/UI, self-contained SVG map, `build_package`, deterministic
summary, escaped `render_html`, optional Gemini prompt.

**Multi-airport correction:** browser title/name/elevation/table are data-driven;
no VOBL/Bengaluru UI defaults for another airport.

## Phase 5 — Upload-first Colab & reproducibility ✅ DONE

**Delivered:**
- generated full notebook (`scripts/build_full_pipeline_notebook.py`);
- default **Upload PDF** browser button + permission acknowledgement;
- explicit optional VOBL sample URL mode;
- exact-one-PDF/signature/native-text gates;
- filename + SHA-derived run ID; all-page extraction/holding;
- dynamic search, bbox, title, map and output names;
- complete artifact ZIP; optional Gemini with deterministic fallback.

**Exit gate met:** generated notebook JSON is deterministic/valid, contains an
upload button and has no hard-coded `09L`/Bengaluru generic search.

## Phase 6 — Planning/research refresh ✅ DONE

**Delivered:** PRD, Architecture, Rules, Phases, Design, Memory; POC +
multi-airport architecture; multi-airport research; README/demo guidance.

## Phase 7 — Verification & delivery ✅ DONE

**Delivered:** 94 regressions pass; VOBL and rights-safe synthetic VOMM criteria
are recorded; final semantic review found no high/medium issues; implementation
commit `4f180eca52dcbe1d35314b68e8c31ee14bf35056` is the immutable Colab/install
target; branch and [PR #3](https://github.com/yashpatle23/Airport-OCR/pull/3)
are published.

**Exit gate met:** full tests, compileall, diff checks, deterministic notebook,
remote commit/notebook lookup, and exact Git installer resolution all pass.

## Phase 8 — Local application and infrastructure ✅ DELIVERED

**Goal:** replace Colab as the primary development path with a portable local
Python microservice and container profile.

**Implemented:** FastAPI/Pydantic v1 API, reliable central PDF upload, fixed
5 MiB PDF checks, tracked bounded `asyncio.to_thread` processing, PyMuPDF
complexity controls, and a complete request-scoped UI pipeline: run/intake,
stage outline, positioned evidence, all core results, document research and
diagnostics, GeoJSON search/no-tile map, Markdown/HTML report, individual
artifacts, manifest, and browser-generated ZIP. Local Uvicorn, hardened local-
only Docker/Compose, API/architecture/operator documentation, and Python
heap/stack/GC study are included.

**Verification:** 94 existing regressions, compileall, JavaScript syntax, diff,
HTML/Compose parsing, wheel build, and package-data inspection pass. Runtime
ASGI/native-PDF and Compose startup smoke are not claimed because the sandbox
lacks the application dependencies and Compose provider; the existing suite has
no new API coverage because tests require an explicit request.

**Delivery:** implementation commit `3949a7e` is published on
`feat/local-fastapi-app`; [PR #4](https://github.com/yashpatle23/Airport-OCR/pull/4)
targets `main`. Before any remote or hostile-input deployment, add dependency-
enabled API/service regressions and a process-isolated parser with enforceable
memory/CPU/time limits. Colab remains an optional old demo.

## Future phases

| Phase | Goal | Gate |
|-------|------|------|
| **9 — OCR/image adapter** | Detect textless scans, render safely, OCR/layout candidates behind evidence contract | approved source rights + benchmark corpus |
| **10 — Publisher/layout profiles** | Add positively detected adapters for other chart families | diverse permitted corpus; no filename-only profile selection |
| **11 — SME review workflow** | Accept/reject taxiway/holding candidates and adjudicate claims | roles, audit trail, bitemporal decisions |
| **12 — Multi-airport persistence** | Versioned store and API over reviewed packages | rights per source + release policy |
| **13 — Hardening** | process isolation, ingress/rate/auth controls, fully resolved locking, observability | phases 9–12 |

No future phase may relax [`Rules.md`](Rules.md): capability increases what is
recorded, never what is asserted as authoritative.
