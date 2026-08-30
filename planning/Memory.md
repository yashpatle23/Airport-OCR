# Memory — Airport-OCR

> Read this first when resuming. Append the newest dated log entry at the top and
> refresh the snapshot whenever branch/tests/PR state changes.

Companion docs: [`PRD.md`](PRD.md) · [`Architecture.md`](Architecture.md) ·
[`Rules.md`](Rules.md) · [`Phases.md`](Phases.md) · [`Design.md`](Design.md)

## Snapshot

- **Repo:** `yashpatle23/Airport-OCR`
- **Working clone:** `/projects/sandbox/Airport-OCR-clone`
- **Branch:** `feat/multi-airport-upload` (created from `feat/airport-ocr-poc`).
- **Current task:** delivered on `feat/multi-airport-upload`; reviewed
  implementation `4f180eca52dcbe1d35314b68e8c31ee14bf35056` is the immutable
  notebook/install target.
- **Review:** [PR #3](https://github.com/yashpatle23/Airport-OCR/pull/3).
- **Tests:** **94/94 passing** with rights-safe VOMM, profile/header isolation,
  strict list/coordinate/provenance/numeric handling, controlled CLI errors, and
  cross-layer partial-status coverage.
- **Representative checks:** VOBL regression + source-shaped VOMM + scanned-PDF
  safe-stop + profile-mismatch rejection all pass.
- **Notebook:** 22 cells; regeneration byte-identical; upload/default/ZIP/dynamic-
  search/all-page-holding assertions pass.
- **Core runtime:** Python 3.9+, zero third-party dependencies.
- **Colab adapters:** PyMuPDF, matplotlib, optional `google-generativeai`.
- **Safety:** `OPERATIONAL_USE = False`; no operational/authoritative mode.

## Current architecture

`PDF → controlled intake → native-text capability gate → page-aware words →
layout adapters → reciprocal/domain assembly → invariant validation →
JSON/GeoJSON → search/package/report → artifact ZIP`

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

## Workflow reminders

- Test runner: `~/.pyenv/versions/3.11.15/bin/python -m pytest -q`.
- Work/push branch: `feat/multi-airport-upload`; never push `main` unprompted.
- Before push: fetch/rebase safely if needed, run full tests, regenerate notebook,
  inspect git diff/status.
- GitHub PRs: use `gh api repos/{owner}/{repo}/pulls`, not `gh pr create`.

## Log (newest first)

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
