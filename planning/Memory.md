# Memory — Airport-OCR

> Rolling progress log so context survives across chats, tools, and sessions.
> **Append newest entries at the top.** When you finish meaningful work, add a
> dated entry: what changed, why, key decisions, and what's next. This is the
> file to read first when resuming.

Companion docs: [`PRD.md`](PRD.md) · [`Architecture.md`](Architecture.md) ·
[`Rules.md`](Rules.md) · [`Phases.md`](Phases.md) · [`Design.md`](Design.md)

---

## Snapshot (current state)

- **Repo:** `yashpatle23/Airport-OCR` · working branch **`feat/airport-ocr-poc`**.
- **Tests:** **69 passing** (`pytest`). Runtime deps: **none**; Python **3.9+**.
- **Pipeline:** `PDF → Extract → Identify → Structure → Search` runs end-to-end
  on VOBL; validation = `PASS_WITH_EXPECTED_BLOCKERS`, **0 real failures**.
- **Interfaces:** CLI (`intake`, `process`, `search`, `serve`,
  `extract-pdf-words`), offline web app (API + UI + SVG map), and
  `report.render_html(package, ai_text=None)` styled HTML card.
- **AI:** optional **Gemini** paraphrase (`models/gemini-flash-latest` via
  `google-generativeai`), deterministic fallback; paraphrase-only.
- **PRs:** PR #1 **merged** into `main`; PR #2 **open** (base `main` ←
  `feat/airport-ocr-poc`).

## Key facts (VOBL case study)

- ICAO **VOBL**, chart `AD 2 VOBL 1-101` (AMDT 06/2025).
- Runways **09L/27R** & **09R/27L**, 4000 × 45 m.
- **43 taxiways** (B3 = 15 m, rest 23 m) from the pavement legend.
- ARP 13°11′56″N 077°42′20″E → `[77.7055555556, 13.1988888889]` (CRS84).
- **Elevation conflict preserved unresolved:** `3003 ft` (chart) vs `3001 ft`
  (eAIP index) — selected value stays `null`.
- Holding positions: **25 review-only candidates** (`CANDIDATES_PENDING_REVIEW`,
  each `NEEDS_REVIEW`); accepted set `BLOCKED_SOURCE_BYTES_REQUIRED`.
- Source PDF SHA-256:
  `ef0541fca479c35eb9d47208fddf12d59c011294e047ebfa5c4ac55dc060bf05`
  (recorded in `docs/phase-0/source-register.json`).

## Standing decisions (why things are the way they are)

- **`render_html` is self-contained** (inline CSS, escaped values) — rejected
  external CSS/JS for offline + safety.
- **Holding = review-only candidates** via black-linework clustering — color
  filtering rejected (holding marking is `#000000`, not color-separable; stop-bar
  `#ff0000` / no-entry `#bf00ff` are separable but out of scope).
- **Taxiways populated only** in `examples/vobl-from-pdf-observations.json`;
  bootstrap example stays blocked (avoid cascading test churn).
- **`original_bytes_available = False`** kept even after SHA-256 recorded — we
  have text/hash, not authoritative rights; rights blocker **not** flipped.
- **Large exports gitignored:** `holding_candidates.json`, `drawings*.json`,
  `vobl_words.json`, `demo_out/`.
- **Notebooks built via a Python builder** (valid nbformat JSON) — never
  hand-edit `.ipynb` JSON.
- **AI switched OpenAI → Gemini** at user's request (secret `GEMINI_API_KEY`).

## Environment / workflow reminders

- Test runner: `~/.pyenv/versions/3.11.15/bin/python -m pytest -q`
  (system `python3` is 3.9 and lacks pytest).
- Push to `feat/airport-ocr-poc` (never `main` unprompted). Rebase onto
  `origin/feat/airport-ocr-poc` before pushing (remote has moved several times).
- Open PRs with `gh api repos/{owner}/{repo}/pulls` — **not** `gh pr create`
  (GraphQL-backed, fails here). Default-branch PATCH returns 403 (known limit).

---

## Log

### 2026-08-19 — Planning doc set added
- Added `planning/`: **PRD, Architecture, Rules, Phases, Design, Memory** —
  grounded in the real repo (module map, CLI surface, actual CSS tokens,
  phase statuses).
- Design tokens captured from `report.py` (slate palette, `system-ui` stack,
  920px card). Rules codify the non-operational / zero-dep / escape-everything /
  preserve-conflicts guarantees.
- **Next:** commit + push these docs to `feat/airport-ocr-poc`; optionally link
  from `README.md`; decide on merging PR #2.

### 2026-08-19 — Notebook AI cell → Gemini + polished render (commit `66dc630`)
- Rewrote the Full-Pipeline notebook's summary cell: pulls `GEMINI_API_KEY` from
  Colab secrets, calls `models/gemini-flash-latest`, then renders the whole
  package via `render_html`, saving `vobl_report.html`. Deterministic fallback
  when no key.

### 2026-08-19 — `render_html` renderer (commit `4105267`)
- Added `report.render_html(package, ai_text=None)` → self-contained styled HTML
  (header + badges, fact grid with highlighted elevation conflict, runway table,
  taxiway chips, holding-candidate tile, AI/deterministic narrative, caveat
  footer). Escapes all values (untrusted chart/AI text). +2 tests. 69 pass.

### earlier — foundation (see `git log` and `docs/`)
- `f42ced2` demo script + walkthrough (`DEMO.md`, `scripts/demo.py`).
- `6f399eb` full end-to-end pipeline: report module + Colab notebook.
- `87f4c0b` stop tracking large regenerable exports (gitignore).
- `7438dd3` review-only holding-position candidate detector (`holding.py`).
- `9d04cd2` recorded VOBL PDF provenance (SHA-256) in source register.
- Core package (`intake`, `coordinates`, `pdf_words`, `pipeline`, `validation`,
  `report`, `search`, `webapp`, `webui`, `cli`) + Phase-0/1 governance docs.

---

### How to update this file
1. Add a dated entry at the top of **Log** (newest first).
2. Refresh **Snapshot** if branch/tests/PR state changed.
3. Record any new **standing decision** with its rationale.
4. Note the immediate **Next** step so the next session resumes cleanly.
