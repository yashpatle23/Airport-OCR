# Airport-OCR local API standards

## Scope

These conventions apply to the FastAPI application under `/api/v1`. The API is
local, stateless, non-operational, and designed for one request-scoped PDF
pipeline run. `/pipeline-runs` is the primary complete resource;
`/extractions` is the compact compatibility resource. The deterministic domain
core remains framework-independent.

## Resource and versioning conventions

- Version application endpoints in the path (`/api/v1`).
- Use plural resource nouns (`/extractions`), standard HTTP methods, and JSON
  response bodies.
- Keep health and OpenAPI under `/api`; static UI paths are not API resources.
- Backward-compatible additions may remain in `v1`. Removing or changing fields,
  status semantics, or accepted media types requires a new API version.
- Never add an API option that enables operational use.

## Multipart pipeline contract

`POST /api/v1/pipeline-runs` and `POST /api/v1/extractions` use the same
`multipart/form-data` request:

| Field | Type | Rule |
|---|---|---|
| `file` | file | exactly one `.pdf`, part type `application/pdf`, `%PDF-` signature, 1..5,242,880 bytes |
| `permission_confirmed` | boolean | must validate as literal `true` |
| `profile` | string | optional; only `auto` is accepted |

Validation is layered intentionally: FastAPI validates multipart field types,
Pydantic validates the options DTO, the controller validates transport/file
properties, and the PDF service validates native document capability and
complexity. Upload permission is an attestation, not rights verification.

## Success responses

- Return `200 OK` only after the supported processing path completes and the
  response envelope passes Pydantic validation.
- Include `api_version: "v1"` and `operational_use: false`.
- The primary pipeline response returns run/intake metadata, stage outline,
  positioned-word evidence, observations, normalized JSON, GeoJSON, validation,
  holding candidates, package, document-derived research/diagnostics and search
  examples, deterministic Markdown, escaped HTML report, offline-AI status,
  artifact descriptors, and manifest.
- The compact extraction response preserves the earlier intake/results/summary
  shape for compatibility.
- “Research” means deterministic findings, source evidence, extraction
  diagnostics, support boundaries, and limitations derived from the uploaded
  document. It must not imply external research or authoritative facts.
- API-owned run, intake, stage, evidence, research, summary, artifact, and
  manifest wrappers are strict nested DTOs with cross-envelope consistency
  checks. Independently versioned observation/normalized/GeoJSON/validation/
  package documents remain opaque domain dictionaries.
- Each validated response is encoded once off the event loop and returned as an
  already-materialized JSON response while the route retains its OpenAPI model.

## Error responses

Expected errors use `application/problem+json` with a Spring-like, RFC-style
Pydantic envelope:

```json
{
  "type": "about:blank",
  "title": "Unsupported media type",
  "status": 415,
  "code": "PDF_SIGNATURE_REQUIRED",
  "detail": "The uploaded bytes do not have a PDF signature.",
  "operational_use": false,
  "violations": [],
  "context": {}
}
```

`code` is the stable machine-readable extension; `detail` is human-readable and
may be improved without a version change. Never expose tracebacks, native parser
internals, filesystem paths, or uploaded chart text in generic errors.

| Status | Meaning |
|---|---|
| `400` | malformed HTTP or multipart request |
| `404` | resource not found |
| `405` | method not allowed |
| `413` | PDF file part exceeds exactly 5 MiB |
| `415` | extension, part media type, or signature is not accepted as PDF |
| `422` | field validation, unsupported PDF capability, bounded extraction error, or generated output above the configured response limit |
| `500` | unexpected internal failure; details are logged, not returned |
| `503` | all bounded local extraction slots are active; retry later |

## Pydantic and Spring-style boundaries

- DTOs inherit a base model with `extra="forbid"`.
- Settings use explicit numeric ranges and fail startup on invalid values.
- Controllers do HTTP coordination, not domain extraction.
- The synchronous application service owns PyMuPDF and calls the domain core.
- Known service exceptions are translated once into problem details.
- OpenAPI is generated from route signatures and response models.
- All public DTO changes require review for OpenAPI and compatibility impact.

## Async rules

- Await request I/O (`UploadFile.read`, `UploadFile.close`).
- Do not execute PyMuPDF or the deterministic pipeline directly on the event-loop
  thread.
- Submit native work, explicit response-model validation, and JSON byte
  materialization through non-blocking bounded admission and the tracked
  `asyncio.to_thread` boundary; reject overflow with `503` rather than queueing
  complete PDF payloads.
- Reject encoded output above `AIRPORT_OCR_MAX_PIPELINE_RESPONSE_BYTES` (64 MiB
  default; 1..128 MiB allowed) with `PIPELINE_OUTPUT_LIMIT_EXCEEDED`.
- Capacity remains owned through native work, validation, encoding, and the
  client-facing ASGI body handoff, even after client cancellation. Pure ASGI
  safety-header middleware preserves outer-send backpressure; send failures and
  abandoned completed results release the token exactly once.
- One supplied Uvicorn worker is part of the resource model; multiple processes
  multiply admission capacity.

## Browser-client rules

- Serve assets from the same package and origin; no CDN or outbound call.
- Validate obvious file errors before upload, but treat server validation as
  authoritative. Picker and drag/drop must share one canonical selected-file
  state; browser-native `required` validation must not suppress the submit
  handler for dropped files.
- A `.pdf` with empty browser MIME metadata may be submitted as
  `application/pdf`; nonempty conflicting MIME remains a client error and the
  server still verifies extension, exact part type, bytes, and signature.
- Render response/chart content with `textContent` and DOM node construction,
  never `innerHTML`.
- Search and provisional maps must derive only from returned GeoJSON and use no
  external tiles or assets.
- Individual artifacts are serialized only when downloaded; artifact-table size
  labels must not eagerly materialize every file.
- The complete store-only ZIP is built in browser memory from the response and
  discarded on reset/page close. ZIP generation temporarily retains every
  serialized artifact plus the final archive, so users should generate it only
  when needed; never persist it silently.
- Keep the non-operational warning visible and preserve validation/blocker states.

## Examples

```bash
curl http://127.0.0.1:8000/api/v1/health

curl --fail-with-body \
  -F 'file=@chart.pdf;type=application/pdf' \
  -F 'permission_confirmed=true' \
  -F 'profile=auto' \
  http://127.0.0.1:8000/api/v1/pipeline-runs \
  --output pipeline-run.json
```

Clients should branch on HTTP status plus `code`, not parse `detail` text.
