# Architecture — Airport-OCR

> Local-first, multi-airport architecture for non-operational aerodrome-chart
> extraction. Pairs with [`PRD.md`](PRD.md), [`Rules.md`](Rules.md), the
> [local application design](../docs/architecture/LOCAL_FASTAPI_APPLICATION.md),
> and the [multi-airport design](../docs/architecture/MULTI_AIRPORT_DESIGN.md).

## 1. End-to-end flow

```text
Browser / API client
  │ one permitted multipart PDF (fixed ≤5 MiB)
  ▼
FastAPI v1 controller
  │ extension + MIME + signature + size + permission / Pydantic validation
  ▼
Tracked bounded extraction task
  │ async request I/O; asyncio.to_thread for synchronous native work
  ▼
PyMuPDF application service
  │ SHA-256 + page/word/drawing/vector limits + deterministic cleanup
  ▼
Page-aware evidence → layout adapters → domain assembly
  ▼
Normalize + invariant validation + review/candidate states
  ▼
Pydantic full-pipeline envelope
  ├─ run/intake + all-page positioned-word evidence
  ├─ observations / normalized JSON / GeoJSON / validation / candidates / package
  ├─ pipeline outline + document research + search + Markdown/HTML report
  └─ same-origin overview/map/raw views + individual artifacts + browser ZIP
```

The primary development/runtime path is local FastAPI. The generated Colab
notebook remains an optional immutable demo. The legacy stdlib observation-JSON
server remains for compatibility.

## 2. Layering and module map (`src/airport_ocr/`)

| Layer/module | Responsibility | Allowed dependencies |
|---|---|---|
| `api/app.py` | ASGI lifecycle, middleware, error mapping, static UI | FastAPI/Starlette/Pydantic DTOs |
| `api/routes.py` | Versioned controllers, multipart checks, async coordination | FastAPI + application service |
| `api/models.py` | Pydantic DTOs and bounded environment settings | Pydantic |
| `api/run.py` | Local one-worker Uvicorn launcher | Uvicorn (lazy import) |
| `services/pdf_extraction.py` | PyMuPDF lifecycle, PDF complexity controls, core orchestration | PyMuPDF + domain core |
| `pdf_words.py` | Page-aware adapters → observations/diagnostics | standard-library domain core |
| `pipeline.py` / `validation.py` | Normalization, GeoJSON, invariant validation | standard-library domain core |
| `holding.py` / `report.py` | review candidates, package and summary | standard-library domain core |
| `intake.py`, `coordinates.py`, `search.py` | provenance, exact coordinates, search | standard library |
| `webapp.py` / `webui.py` | legacy observation-JSON stdlib server | standard library |
| `static/` | same-origin full pipeline, research, search/map and artifact/ZIP UI | browser platform only; no CDN |
| `cli.py` / `__main__.py` | legacy/core command boundary | domain core |

This is Spring-style separation—controller, DTO, application service, domain,
exception translation—without coupling domain modules to FastAPI or Pydantic.

## 3. Upload and extraction contract

The primary endpoint is `POST /api/v1/pipeline-runs`; the compact
`POST /api/v1/extractions` endpoint remains compatible. Both use fields `file`,
`permission_confirmed=true`, and `profile=auto`.

The controller requires:

- one basename ending in `.pdf`;
- exact multipart part type `application/pdf`;
- 1..5,242,880 file bytes (exactly 5 MiB is accepted);
- `%PDF-` file signature;
- literal permission attestation and the generic `auto` profile.

The service then requires a readable, unencrypted, nonempty PDF and enforces
configured page, native-word, per-page drawing, and total retained segment limits.
Textless scans stop with `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED`; unsupported
required layouts fail explicitly. Domain validation reports—including failures—
remain attached to returned research output rather than being silently discarded.

Starlette can parse/spool multipart content before the controller checks the file
size. The fixed limit is therefore a file-part limit, not a public ingress limit.
The supplied application is loopback-only; any remote design needs an upstream
body limit and a separate security review.

## 4. Async and lifecycle architecture

- `UploadFile.read()` and `close()` are awaited.
- A bounded token queue is created inside ASGI lifespan on Uvicorn's event loop,
  including on Python 3.9. Admission is non-blocking; overflow receives `503`
  rather than becoming an in-memory queue.
- An admitted tracked task calls either compact or full synchronous PDF service,
  validates the corresponding Pydantic model, and materializes JSON bytes through
  `asyncio.to_thread(...)`. The compact path shares core extraction but does not
  build full-only research/report/artifact structures.
- The same token remains owned through the bounded encoded-response check and
  client-facing ASGI body handoff. Pure ASGI safety-header middleware wraps the
  original `send` without an intermediate response stream. Shielding prevents
  request cancellation from releasing capacity while native work is still
  running; abandoned results/send failures return the token exactly once.
  Finished tasks are consumed and shutdown waits for active tasks.
- PyMuPDF/document traversal never executes directly on the event-loop thread.
- Threads are not a parser sandbox and cannot be force-stopped. One Uvicorn
  worker is part of the supplied resource model; more workers multiply capacity.

See [Python memory and concurrency](../docs/PYTHON_MEMORY_AND_CONCURRENCY.md).

## 5. Extraction strategy

### 5.1 Core, adapters, profiles

- **Core:** page-aware words, source evidence, domain assembly and invariants.
- **Adapters:** independent recognizers for chart header, runway rows, explicit
  physical dimensions, width-first taxiway legends and `TWY X` references.
- **Profiles:** uploads use `auto`; `vobl-sample` is an explicit legacy regression
  hint and cannot apply facts to another ICAO.

### 5.2 Capability gate

Native-text extraction requires a unique ICAO, ARP DMS pair, aerodrome-elevation
claim, and at least one complete reciprocal runway pair with threshold DMS.
Unknown optional layouts remain partial. Holding geometry remains `NEEDS_REVIEW`.

### 5.3 Completeness vocabulary

- `EXTRACTED_FROM_NATIVE_TEXT_PENDING_REVIEW`
- `CANDIDATES_PENDING_REVIEW`
- `BLOCKED_LAYOUT_OR_REVIEW_REQUIRED`
- `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED`
- `NOT_EXTRACTED_NOT_ABSENT`

## 6. API and data contracts

1. **Multipart request** — PDF plus permission/profile form fields.
2. **Problem detail** — `application/problem+json`, stable `code`, field
   violations/context, and `operational_use=false`.
3. **Intake metadata** — filename, bytes, SHA-256, media type, attestation,
   malware/rights warnings.
4. **Page evidence** — page number + positioned words; no cross-page collisions.
5. **Observation JSON** — source-preserving values and extraction diagnostics.
6. **Normalized JSON/GeoJSON** — canonical model and RFC 7946 CRS84 lon/lat.
7. **Validation report** — failures versus expected blockers/info.
8. **Holding candidates/package/summary** — review-only candidates and five
   requested feature groups.
9. **Full pipeline response** — run/intake, stage outline, positioned words,
   results, document-derived research/search examples, Markdown/HTML summary,
   offline-AI status, artifact descriptors, and manifest.
10. **Browser artifact bundle** — SHA-qualified Colab-equivalent files and ZIP
    constructed without server persistence or external assets.
11. **Compact response** — the earlier extraction envelope retained for clients
    that do not need complete evidence/artifacts.

See [`../docs/API_STANDARDS.md`](../docs/API_STANDARDS.md).

## 7. Infrastructure

| Concern | Local Python | Container profile |
|---|---|---|
| Process | `airport-ocr-api` | Uvicorn, one worker |
| Bind | `127.0.0.1:8000` | container `0.0.0.0`, host `127.0.0.1:8000` |
| Identity | developer user | UID/GID 10001 |
| Filesystem | project/venv | read-only root + 64 MiB `/tmp` tmpfs |
| Security | local only | all capabilities dropped, no-new-privileges |
| Limits | bounded app settings | 512 MiB, 1 CPU, 128 PIDs + app settings |
| Health | `/api/v1/health` | Docker/Compose liveness check |

`constraints-app.txt` pins reviewed **direct** application versions; transitive
resolution is not hash-locked. Static assets are included in package data. Tests,
notebooks, docs, planning files, PDFs, and local state are excluded from the
runtime image.

## 8. Technology decisions

| Layer | Choice | Reason |
|---|---|---|
| API | FastAPI | async ASGI, multipart, OpenAPI, Pydantic integration |
| Contracts | Pydantic v2 | strict DTO/settings validation and generated schema |
| Server | Uvicorn | focused local ASGI runtime |
| PDF service | PyMuPDF | positioned native words and vector drawings |
| Domain core | Python 3.9+ stdlib | deterministic, portable, framework-independent |
| Exact numerics | `decimal.Decimal` | source-faithful DMS normalization |
| Web UI | packaged HTML/CSS/JS | same-origin, offline, no external assets |
| Infrastructure | Docker/Compose | portable local runtime and resource guardrails |
| Optional AI | Gemini at legacy edge | paraphrase-only, deterministic fallback |
| Tests | pytest | existing behavioral regression suite |

Django was not selected because this stateless service does not need its ORM,
admin, sessions, or template stack.

## 9. Trust boundaries

1. PDFs are untrusted; attestation does not grant rights or claim malware scan.
2. Native PDF parsing occurs in-process; container/thread limits reduce but do
   not eliminate native parser risk.
3. Chart and AI text are untrusted and rendered as text/escaped output.
4. Profiles cannot inject facts into a non-matching airport.
5. Declared distances are not physical dimensions.
6. Empty is never absence without evidence; conflicts stay unselected.
7. Holding/taxiway candidates require qualified review.
8. No operational/authoritative mode, persistence, auth-less remote exposure, or
   outbound UI call exists.

## 10. Extension points

- OCR/image adapter behind the same evidence contract;
- process-isolated worker pool for hostile remote inputs;
- upstream ingress/rate/auth/TLS/malware controls;
- additional positively detected publisher/layout adapters;
- typed nested API schemas, request IDs, metrics, and readiness;
- governed SME review and persistence after rights/release gates.
