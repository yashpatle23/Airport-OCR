# Rules — Airport-OCR

> Guardrails for anyone (human or AI) working on this codebase. These are
> **binding constraints**, not suggestions. When a rule conflicts with a
> convenient shortcut, the rule wins. See [`PRD.md`](PRD.md) §3 for non-goals and
> [`Architecture.md`](Architecture.md) §6 for trust boundaries.

---

## 1. Safety & domain rules (non-negotiable)

- **R1.1** Output is **non-operational, research-only**. Never emit or imply
  authoritative aeronautical data, and never suggest navigation/operational use.
- **R1.2** `OPERATIONAL_USE` stays `False`. Do not add a flag, mode, or config to
  flip it.
- **R1.3** **Preserve conflicts.** Contradictory source claims (e.g. elevation
  `3003 ft` vs `3001 FT`) are stored unselected. Never auto-pick a winner.
- **R1.4** **Empty ≠ absent.** Unextracted collections use
  `NOT_EXTRACTED_NOT_ABSENT` plus a specific blocker such as
  `BLOCKED_LAYOUT_OR_REVIEW_REQUIRED`; never imply "the airport has none".
- **R1.5** Holding positions are **review-only candidates** (`NEEDS_REVIEW`)
  until a qualified reviewer accepts them. Do not promote candidates
  programmatically.
- **R1.6** Intake **records** provenance/rights/malware status; it must never
  assert a file is clean or that rights are granted.
- **R1.7** Do not commit source PDFs, AIP/eAIP material, or large binary dumps.
  The MIT license covers **code only**, not any chart data.
- **R1.8** Compatibility profiles apply only after a positive airport/layout
  match **and explicit caller selection**. Missing metadata must never activate a
  profile. Never inject VOBL names, runways, dimensions, or elevation claims into
  generic `auto` extraction or a non-VOBL chart.
- **R1.9** Declared distances (TORA/TODA/ASDA/LDA) are not physical runway
  dimensions and must never be substituted for length/width.
- **R1.10** Header facts must be spatially/block-associated; never select the
  first coordinate/date match from flattened chart text.
- **R1.11** Taxiway legends require an explicit designator-list grammar. Prose
  tokens must reject the legend, not become features.
- **R1.12** Preserve extraction completeness and issues through every output
  surface. Zero validation failures must not render `PARTIAL`, candidate, or
  expected-blocker output as complete/success-green.

## 2. Dependency rules

- **R2.1** Core runtime has **zero third-party dependencies** (`dependencies = []`
  in `pyproject.toml`). Prefer the standard library.
- **R2.2** Any new runtime dependency requires an explicit decision recorded in
  [`Memory.md`](Memory.md) with justification. Default answer is "no".
- **R2.3** PyMuPDF is allowed **only** off the runtime path (to produce the word/
  vector dump). The core package must never `import fitz`/`pymupdf`.
- **R2.4** Optional integrations (e.g. Gemini via `google-generativeai`) must be
  **lazy-imported inside a `try`** and degrade gracefully when absent.
- **R2.5** The web UI and HTML report ship **no external assets, CDNs, scripts,
  fonts, or network calls**. Everything is inline and offline.
- **R2.6** `pytest` is the only dev dependency; keep it that way unless justified.

## 3. Coding conventions

- **R3.1** Target **Python 3.9+**; no syntax/stdlib features newer than 3.9.
- **R3.2** Use `decimal.Decimal` for coordinate/dimension math — **never float**
  for DMS conversion. Preserve the exact source string alongside the parsed value.
- **R3.3** GeoJSON is **RFC 7946** with `OGC:CRS84` **lon, lat** order.
- **R3.4** Keep modules single-responsibility per the
  [module map](Architecture.md#2-module-map-srcairport_ocr). New feature
  extractors emit the shared observation contract.
- **R3.5** Normalization/validation must be **deterministic**: identical input →
  identical output. No wall-clock, randomness, or network in the core path.
- **R3.6** Keep functions pure where practical; isolate I/O at the edges (CLI,
  webapp, intake).

## 4. Security rules

- **R4.1** Treat **all** source files, chart text, and AI output as untrusted.
- **R4.2** **HTML-escape every value** rendered in the UI or report (chart/AI
  text can contain injection payloads). This is already covered by tests — keep
  it that way.
- **R4.3** The web app binds locally and is stateless (`/api/process` does not
  persist). Do not add auth-less remote exposure or persistence without review.
- **R4.4** No telemetry, analytics, or outbound calls from the core or UI.

## 5. AI-usage rules

- **R5.1** AI is **paraphrase-only**, downstream of structuring. It must not
  invent, correct, select, or reorder values.
- **R5.2** Always drive AI from `ai_summary_prompt(package)` (system + user). The
  system prompt states the non-authoritative, no-invention constraint — do not
  weaken it.
- **R5.3** AI output is rendered as untrusted text (escaped) and clearly labelled
  "non-authoritative paraphrase".
- **R5.4** The pipeline must produce a complete, correct result **without** AI.
  AI is strictly additive; the deterministic summary is the fallback.
- **R5.5** Never send more than the structured package to a model; do not upload
  raw source PDFs to third-party APIs.

## 6. Error-handling rules

- **R6.1** **Fail loud in the core** — missing required identity/ARP/elevation/
  reciprocal-runway evidence raises a specific unsupported-layout error; do not
  emit a misleading package.
- **R6.2** **Fail soft at optional edges** — missing optional dimensions, TDZ,
  taxiway widths, API key, network, or optional library becomes a visible
  blocker/fallback, never fabricated data or a hidden crash.
- **R6.3** Distinguish **expected blockers** from **real failures**. CLI exit
  codes: `0` = `PASS_WITH_EXPECTED_BLOCKERS`, `1` = real validation failure,
  `3` = expected blockers remain under `--fail-on-blockers`.
- **R6.4** Error messages must be specific and actionable; never mask the root
  cause with a generic catch-all.
- **R6.5** Prefer explicit status enums over booleans for completeness/trust.

## 7. Process & workflow rules

- **R7.1** Work on `feat/airport-ocr-poc` (or a new branch); **never push
  straight to `main`** unless explicitly asked.
- **R7.2** Open PRs via `gh api repos/{owner}/{repo}/pulls` (not `gh pr create`).
- **R7.3** Run `pytest` before every commit; keep the suite green.
- **R7.4** Do **not** add tests unless requested — but never remove/weaken
  existing safety tests (escaping, conflict preservation, completeness).
- **R7.5** Update [`Memory.md`](Memory.md) whenever a decision, blocker, or
  milestone changes, so context survives across sessions/tools.
- **R7.6** The full notebook is generated by
  `scripts/build_full_pipeline_notebook.py` (valid nbformat JSON); do not
  hand-edit `Airport_OCR_Full_Pipeline.ipynb`. Regenerate and review the diff.

## 8. Hard "do NOT" list

- ❌ Claim operational/authoritative status or enable navigation use.
- ❌ Auto-resolve conflicting source values.
- ❌ Treat empty collections as "none present".
- ❌ Add runtime third-party deps to the core, or external assets to the UI/report.
- ❌ Let AI edit, correct, or select data values.
- ❌ Commit source charts, AIP/eAIP data, or large binary dumps.
- ❌ Use floats for coordinate math.
- ❌ Push to `main` without explicit instruction.
