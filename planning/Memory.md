# Memory — Airport-OCR

> Read this first when resuming. Append the newest dated log entry at the top and
> refresh the snapshot whenever branch/tests/PR state changes.

Companion docs: [`PRD.md`](PRD.md) · [`Architecture.md`](Architecture.md) ·
[`Rules.md`](Rules.md) · [`Phases.md`](Phases.md) · [`Design.md`](Design.md)

## Snapshot

- **Repo:** `yashpatle23/Airport-OCR`
- **Working clone:** `/projects/sandbox/Airport-OCR-clone`
- **Branch:** `feat/local-fastapi-app` (created from `feat/multi-airport-upload`).
- **Current task:** version 0.3.0 local FastAPI application and infrastructure
  are implemented, verified to the available sandbox boundary, and published.
- **Review:** [PR #4](https://github.com/yashpatle23/Airport-OCR/pull/4) from
  `feat/local-fastapi-app` into `main`.
- **Parent review:** [PR #3](https://github.com/yashpatle23/Airport-OCR/pull/3)
  contains the earlier multi-airport/Colab increment.
- **Tests/checks:** **94/94 existing regressions pass**; compileall, Node
  JavaScript syntax, diff checks, HTML/Compose parsing, wheel build, and packaged
  API/service/static-asset inspection pass. The sandbox lacks all FastAPI/PyMuPDF
  runtime dependencies and a Compose provider, so ASGI/native/container smoke is
  explicitly unverified and the existing suite does not cover the new API.
- **Representative checks:** VOBL regression + source-shaped VOMM + scanned-PDF
  safe-stop + profile-mismatch rejection all pass.
- **Notebook:** 22 cells; regeneration byte-identical; upload/default/ZIP/dynamic-
  search/all-page-holding assertions pass.
- **Domain core:** Python 3.9+, framework-independent and stdlib-only.
- **Application runtime:** FastAPI, Pydantic, PyMuPDF, python-multipart, Uvicorn;
  reviewed direct versions are in `constraints-app.txt`.
- **Primary interface:** local FastAPI central PDF upload and JSON display;
  generated Colab remains an optional immutable demo.
- **Safety:** `OPERATIONAL_USE = False`; no operational/authoritative mode.

## Current architecture

`Browser → FastAPI/Pydantic upload gate → tracked bounded async task → PyMuPDF
service → page-aware evidence → layout adapters → normalization/validation →
Pydantic JSON response`

- Local FastAPI is primary; it accepts one PDF up to exactly 5 MiB and never
  persists source/result data.
- Request I/O is awaited; synchronous native/domain processing runs through
  bounded tracked `asyncio.to_thread` work on one supplied Uvicorn process.
- Domain modules remain framework-independent; PyMuPDF is isolated to the PDF
  application service.
- Docker/Compose binds host loopback and applies non-root/read-only/capability/
  CPU/memory/PID controls.
- The earlier artifact flow remains available in the optional generated Colab:
  `PDF → intake → evidence → adapters → validation → JSON/GeoJSON → ZIP`.

- Uploads use `profile="auto"`; airport facts come only from that source.
- `vobl-sample` is an explicit compatibility/regression profile and refuses a
  non-VOBL ICAO.
- Required unsupported fields stop extraction; optional omissions are expected
  blockers.
- Holding geometry and text-reference taxiways remain review candidates.
- AI is optional downstream paraphrase only.

## Case-study facts

### VOBL regression
- `AD 2 VOBL 1-101`; 09L/27R + 09R/27L; 4000×45 m.
- 43 width-legend taxiways (B3 15 m, rest 23 m).
- ARP `[77.7055555556, 13.1988888889]`.
- Explicit sample profile preserves separate 3003/3001 FT claims unresolved.
- Recorded source SHA-256:
  `ef0541fca479c35eb9d47208fddf12d59c011294e047ebfa5c4ac55dc060bf05`.

### VOMM attached-chart structural check
- `AD 2 VOMM 1-101`, 30 NOV 2023; Chennai Intl. Airport.
- ARP `12°59′42.356″N 080°10′24.973″E` →
  `[80.1736036111, 12.9950988889]`; AD elevation 54 FT.
- Runways 07/25 and 12/30; explicit map dimension labels represented in the
  synthetic check as 3658×45 m and 2890×45 m.
- THR elevations 43/54/44/48 FT; no TDZ column, so TDZ remains not extracted.
- Taxiway references come from hot-spot `TWY` text and remain candidate-grade;
  holding positions are cartographic line symbols and remain review-only.
- The permitted VOMM source is not committed. A rights-safe synthetic positioned-
  word fixture now provides a durable structural regression; the original PDF is
  still required to verify actual PyMuPDF block/word ordering.

## Standing decisions

1. **No false universality.** “Upload any map” means safe intake/diagnosis;
   current deterministic adapters do not promise full extraction from every
   publisher/layout or scanned PDF.
2. **No cross-airport defaults.** The old Bengaluru name, exact VOBL runway set,
   4000×45 dimensions, and 3001 FT external claim exist only behind explicit
   `profile="vobl-sample"`; missing metadata never activates compatibility mode.
3. **Declared distances are not dimensions.** TORA/TODA/ASDA/LDA are never used
   to fill physical length/width.
4. **Required vs optional.** Missing ICAO/ARP/elevation/complete reciprocal pair
   stops; missing physical dimensions/TDZ/taxiway width becomes a blocker.
5. **Page evidence.** Equal PyMuPDF block IDs on different pages are never merged.
6. **Candidate boundary.** Bare map letters are not accepted as taxiways;
   explicit `TWY X` references and vector holds remain review candidates.
7. **Notebook is generated.** Edit
   `scripts/build_full_pipeline_notebook.py`, then regenerate
   `notebooks/Airport_OCR_Full_Pipeline.ipynb`.
8. **Upload-first artifacts.** Preserve source name, use `<stem>-<sha8>`, and
   download one ZIP containing every evidence/output artifact.
9. **HTML/UI safety.** Dynamic chart/AI text is escaped; no external UI assets.
10. **Large/source data excluded.** Do not commit source PDFs or regenerable
    word/drawing/candidate dumps.
11. **Local-first dependency separation.** FastAPI was selected over Django for
    the stateless ASGI/OpenAPI/Pydantic use case. Application dependencies are
    mandatory, but only the PDF service imports PyMuPDF and domain modules stay
    framework-independent/stdlib-only.
12. **Async is coordination, not isolation.** Reject overflow through bounded
    non-blocking admission, await upload I/O, and retain an admitted token through
    native work; threads cannot terminate hostile PDF work, so remote/adversarial
    use requires process isolation and ingress controls.

## Workflow reminders

- Test runner: `~/.pyenv/versions/3.11.15/bin/python -m pytest -q`.
- Work/push branch: `feat/local-fastapi-app`; never push `main` unprompted.
- Before push: fetch/rebase safely if needed, run full tests, regenerate notebook,
  inspect git diff/status.
- GitHub PRs: use `gh api repos/{owner}/{repo}/pulls`, not `gh pr create`.

## Log (newest first)

### 2026-08-19 — Local FastAPI application and infrastructure (verification pending)
- Siva's local-portability mandate moved the primary workflow from Colab to a
  FastAPI microservice and same-origin central PDF upload-to-JSON UI.
- Added versioned Pydantic/OpenAPI contracts, Spring-style controller/DTO/service/
  exception layers, exact 5 MiB extension/MIME/signature checks, and structured
  problem details.
- Added awaited upload I/O plus event-loop-safe, non-blocking bounded admission
  and tracked cancellation-aware `asyncio.to_thread` PyMuPDF/domain work.
- Added page/word/drawing/vector complexity limits and deterministic upload/PDF
  cleanup; domain validation remains visible in returned research JSON.
- Added local Uvicorn plus non-root/read-only/local-interface Docker/Compose with
  health, tmpfs, capability, CPU, memory, and PID controls.
- Recorded the dependency-rule change: application edges now require FastAPI,
  Pydantic, PyMuPDF, multipart, and Uvicorn while the domain core stays stdlib and
  framework-independent.
- Added local architecture/operator, API standards, and project-specific Python
  heap/stack/reference-counting/cyclic-GC/native-memory documentation.
- Verification: 94 existing regressions, compileall, JavaScript syntax, diff,
  HTML/Compose parsing, and wheel/package-data checks pass. Two semantic reviews
  led to non-blocking bounded admission/503, disabled CDN docs, CSP, and aligned
  problem media-type/OpenAPI fixes.
- Remaining limitation: dependencies and Compose provider are absent in this
  sandbox, so ASGI/native-PDF/container smoke is not claimed; no new tests were
  added without an explicit request, and post-materialization PyMuPDF page
  allocations remain a documented local-scope boundary.
- Published implementation commit `3949a7e` on `feat/local-fastapi-app` and
  opened [PR #4](https://github.com/yashpatle23/Airport-OCR/pull/4) into `main`.

### 2026-08-19 — Consolidated implementation documentation
- Added `docs/PROJECT_IMPLEMENTATION_SUMMARY.md` as the single project-level
  account of completed goals, architecture, features, workflows, artifacts,
  case studies, verification, design decisions, limitations, and delivery links.
- Linked the summary from the root README and documentation index for easier
  onboarding and project review.

### 2026-08-19 — Semantic review remediation
- Removed implicit VOBL compatibility activation from `auto`; only explicit
  `vobl-sample` may supply demo facts.
- Replaced global ARP/date matching with header-block association and evidence;
  added controlled missing-bearing handling and strict taxiway-list parsing.
- Preserved extraction status/issues through normalized/package/report/UI output
  and changed partial/candidate/expected-blocker presentation to warnings.
- Added explicit name provenance plus a rights-safe synthetic VOMM fixture and
  cross-layer regression coverage. Final semantic review is **APPROVED** with no
  confirmed high/medium findings; full suite passes **94 tests**.
- Hardened terminal-axis DMS, source-byte/SHA provenance, numeric-domain checks,
  and ordinary CLI file/JSON errors so malformed input fails closed without
  traceback or misleading PASS output.
- Delivery complete: branch pushed, immutable GitHub commit/notebook paths
  verified, exact Git install target resolved as `airport-ocr 0.2.0`, and
  [PR #3](https://github.com/yashpatle23/Airport-OCR/pull/3) opened.

### 2026-08-19 — Multi-airport + upload-first implementation (in progress)
- Investigated old VOBL-specific assumptions and the supplied VOMM chart.
- Added research (`MULTI_AIRPORT_EXTRACTION_RESEARCH.md`) and detailed design
  (`MULTI_AIRPORT_DESIGN.md`) with ICAO/AIXM/RFC/PyMuPDF sources.
- Generalized `pdf_words.py` and `pipeline.py`: page-aware blocks, flexible
  header/elevation, dynamic reciprocal runway pairing, explicit dimensions,
  taxiway references, diagnostics, invariant validation and safe blockers.
- Generalized report/web UI/CLI; holding candidate IDs now include page.
- Added deterministic notebook builder and 22-cell upload-first Full Pipeline:
  upload button, permission gate, SHA run ID, all-page candidates, dynamic
  search/map, Gemini fallback, complete ZIP.
- Synthetic VOMM run: correct airport/ARP/elevation/runway pairs/dimensions/THR
  values and taxiway candidates `B/C/E/F/G/I/M`; 0 failures.
- Full regression suite: **69 passed**. `compileall`, `git diff --check`, scanned-
  PDF stop, VOBL-profile mismatch rejection, and notebook reproducibility checks
  pass. Notebook regeneration is byte-identical.
- **Next:** semantic review, commit, push, create review link.

### 2026-08-19 — Planning set / Gemini report foundation
- Added PRD/Architecture/Rules/Phases/Design/Memory.
- Added `render_html` and Gemini notebook summary; 69 tests passed at that point.
- PR #1 merged; PR #2 carried the VOBL POC branch before this new increment.

### Earlier — foundation
- Controlled intake, exact DMS normalization, VOBL fixtures/benchmark,
  GeoJSON/search, offline web app, report, demo script and holding candidates.
