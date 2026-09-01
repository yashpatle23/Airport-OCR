# Local FastAPI application and infrastructure

> **Non-operational, research-only.** The service does not produce authoritative
aeronautical data and must not be exposed as a navigation or operational system.

## 1. Decision and scope

Local development is the primary workflow from version 0.3.0. FastAPI was chosen
over Django because Airport-OCR is a stateless extraction microservice: it needs
multipart upload handling, Pydantic/OpenAPI contracts, and asynchronous request
coordination, but not an ORM, admin site, sessions, or server-rendered templates.
The generated Colab notebook remains an optional immutable demonstration.

The application accepts one permitted native-text aerodrome-chart PDF, enforces a
fixed 5 MiB file limit, extracts the supported evidence, and returns the complete
research result as JSON. It persists neither uploads nor results.

## 2. Component model

```text
Browser (same-origin HTML/CSS/JS)
        │ multipart/form-data
        ▼
FastAPI /api/v1 controller              src/airport_ocr/api/routes.py
  ├─ extension, MIME, size, signature
  ├─ Pydantic option validation
  ├─ async UploadFile reads
  └─ bounded extraction task
        │ asyncio.to_thread
        ▼
Synchronous PDF application service     services/pdf_extraction.py
  ├─ PyMuPDF open/page/word/vector limits
  ├─ page-aware evidence
  └─ deterministic domain calls
        ▼
Framework-independent domain core
  pdf_words → pipeline → validation → holding/report
        │
        ▼
Pydantic response envelope → JSON UI
```

The layers mirror common Spring Boot separation without turning the deterministic
core into framework classes:

- **Controller/router:** HTTP and multipart concerns only.
- **DTOs/settings:** Pydantic input, output, problem details, and bounded config.
- **Application service:** PyMuPDF lifecycle and orchestration of the core.
- **Domain core:** extraction rules, normalization, validation, packaging.
- **Exception translation:** one `application/problem+json` boundary.

## 3. Request lifecycle and limits

1. Starlette/python-multipart parses the multipart request and exposes an
   `UploadFile`; it can spool multipart data to `/tmp` before controller checks.
2. The controller requires a `.pdf` filename and exact `application/pdf` part
   media type.
3. The file is read with awaited 64 KiB chunks. More than 5,242,880 file bytes
   returns `413`; exactly 5,242,880 is permitted.
4. Empty input and missing `%PDF-` signature fail before native parsing.
5. Permission must validate as literal `true`; only `profile=auto` is accepted.
6. A process-local bounded token queue performs non-blocking admission before
   controller file reads. If all slots are active, the request receives a
   retryable `503` instead of retaining an in-memory extraction backlog. The
   queue is created in ASGI lifespan on Uvicorn's event loop.
7. `asyncio.to_thread` moves synchronous PyMuPDF and domain work off the event
   loop. A shielded tracked task retains its admission token if the client
   disconnects; shutting down waits for active native work to finish.
8. After PyMuPDF materializes a page's word/drawing structures, the service
   applies page, native-word, per-page drawing, and total retained vector-segment
   rejection thresholds. These counters constrain retained/continued work but
   cannot prevent a single native page parse from allocating heavily. The
   document still closes in `finally`.
9. The result is validated against the Pydantic response envelope and rendered
   by the browser with `textContent`, not injected HTML.
10. The upload is closed in the controller `finally` block.

The 5 MiB rule is an exact **file-part** policy, not a complete network ingress
limit. Multipart headers add bytes, and the parser may spool data before the
controller rejects an oversized file. The supplied service binds only to
loopback. Any reviewed remote deployment must add an upstream request-body
limit, authentication, TLS, rate limiting, malware scanning, and observability.

## 4. Async and concurrency behavior

`async` does not make PDF parsing asynchronous or reduce its CPU cost. It keeps
network/file awaits and the ASGI event loop responsive while synchronous native
work runs in worker threads. Important consequences:

- concurrency is per process; additional Uvicorn workers multiply extraction
  concurrency and memory, so the supplied command deliberately uses one worker;
- worker threads are not a security sandbox and cannot be force-killed safely;
- cancellation of an awaiting request does not stop already-running native code;
- tracked tasks keep capacity reserved until native work actually returns;
- no extraction timeout is claimed, because timing out the coroutine would not
  terminate the PyMuPDF thread;
- hostile/untrusted remote workloads need process isolation with OS CPU, memory,
  and time limits rather than only `to_thread`.

## 5. API and UI surfaces

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Same-origin upload-to-JSON browser UI |
| `GET` | `/assets/*` | Packaged local CSS and JavaScript |
| `GET` | `/api/v1/health` | Liveness, version, safety flag, fixed file limit |
| `POST` | `/api/v1/extractions` | One multipart PDF extraction |
| `GET` | `/api/openapi.json` | OpenAPI contract (interactive CDN docs disabled) |

See [`../API_STANDARDS.md`](../API_STANDARDS.md) for HTTP conventions.

## 6. Local development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --constraint constraints-app.txt -e .
airport-ocr-api --host 127.0.0.1 --port 8000
```

Use `--reload` only while developing. The constraints file pins reviewed direct
application versions; it is not a hash-locked transitive dependency set.

Example health request:

```bash
curl --fail http://127.0.0.1:8000/api/v1/health
```

Example extraction:

```bash
curl --fail-with-body \
  -F 'file=@chart.pdf;type=application/pdf' \
  -F 'permission_confirmed=true' \
  -F 'profile=auto' \
  http://127.0.0.1:8000/api/v1/extractions
```

## 7. Container operations

```bash
cp .env.example .env       # optional bounded overrides
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs -f airport-ocr
docker compose down
```

The image runs as UID/GID 10001. Compose publishes only
`127.0.0.1:8000`, uses one worker, drops all capabilities, enables
`no-new-privileges`, makes the root filesystem read-only, provides a 64 MiB
memory-backed `/tmp`, and limits the container to 512 MiB, 1 CPU, and 128 PIDs.
The health check is liveness only; it does not report queue saturation, available
temporary storage, or memory headroom.

Operational troubleshooting:

- **Port in use:** change only the host side of the `ports` mapping.
- **Startup validation error:** restore `.env.example` ranges or remove `.env`.
- **Unhealthy:** inspect `docker compose logs airport-ocr` and the health URL.
- **OOM/container exit:** lower concurrency or PDF complexity limits; inspect
  container state before increasing memory.
- **Clean rebuild:** `docker compose build --no-cache && docker compose up -d`.

The runtime image intentionally excludes tests, notebooks, planning material,
source PDFs, and documentation via `.dockerignore`.

## 8. Security and deployment boundary

The local service records that permission was attested but cannot verify rights.
It does not malware-scan files. It has no authentication, tenant isolation,
database, remote object store, telemetry, or public-deployment profile. The
container controls reduce impact but do not make native PDF parsing safe against
all malicious documents. Keep the supplied service local and non-operational.

## 9. Extension points

- process-isolated extraction pool for adversarial remote input;
- upstream ingress/body limits and explicit overload responses;
- typed nested domain DTOs or versioned JSON Schemas;
- request IDs, metrics, structured logs, and readiness/saturation signals;
- malware scanning and a rights/reviewer workflow;
- accepted-candidate persistence only after governance gates are met.
