# Airport-OCR local API standards

## Scope

These conventions apply to the FastAPI application under `/api/v1`. The API is
local, stateless, non-operational, and designed for one PDF extraction per
request. The deterministic domain core remains framework-independent.

## Resource and versioning conventions

- Version application endpoints in the path (`/api/v1`).
- Use plural resource nouns (`/extractions`), standard HTTP methods, and JSON
  response bodies.
- Keep health and OpenAPI under `/api`; static UI paths are not API resources.
- Backward-compatible additions may remain in `v1`. Removing or changing fields,
  status semantics, or accepted media types requires a new API version.
- Never add an API option that enables operational use.

## Multipart extraction contract

`POST /api/v1/extractions` uses `multipart/form-data`:

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

- Return `200 OK` only after the supported extraction path completes and the
  response envelope passes Pydantic validation.
- Include `api_version: "v1"` and `operational_use: false`.
- Return intake metadata, observations, normalized JSON, GeoJSON, validation,
  holding candidates, package, and summary together so reviewers can see
  partial/failure states in context.
- Nested domain payloads preserve the core's versioned dictionaries; the API DTO
  validates the envelope. Changes to those domain contracts must follow their
  own compatibility rules.

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
| `422` | field validation, unsupported PDF capability, or bounded extraction error |
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
- Submit native work through non-blocking bounded admission and the tracked
  `asyncio.to_thread` boundary; reject overflow with `503` rather than queueing
  complete PDF payloads.
- Capacity must remain owned until native work ends, even after client
  cancellation.
- One supplied Uvicorn worker is part of the resource model; multiple processes
  multiply admission capacity.

## Browser-client rules

- Serve assets from the same package and origin; no CDN or outbound call.
- Validate obvious file errors before upload, but treat server validation as
  authoritative.
- Render response/chart content with `textContent` and DOM node construction,
  never `innerHTML`.
- Keep the non-operational warning visible and preserve validation/blocker states.

## Examples

```bash
curl http://127.0.0.1:8000/api/v1/health

curl --fail-with-body \
  -F 'file=@chart.pdf;type=application/pdf' \
  -F 'permission_confirmed=true' \
  -F 'profile=auto' \
  http://127.0.0.1:8000/api/v1/extractions
```

Clients should branch on HTTP status plus `code`, not parse `detail` text.
