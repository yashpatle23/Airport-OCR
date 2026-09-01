# Airport-OCR research and architecture artifacts

All documents are **non-operational, research-only** and must not be treated as
authoritative aeronautical data.

## Current local application

- [Local FastAPI application and infrastructure](architecture/LOCAL_FASTAPI_APPLICATION.md)
  — component boundaries, async request lifecycle, PDF/resource limits, local
  setup, Docker operations, and deployment/security boundary.
- [API standards](API_STANDARDS.md) — versioning, multipart validation,
  Pydantic/Spring-style layering, problem details, status codes, and async rules.
- [Python memory and concurrency](PYTHON_MEMORY_AND_CONCURRENCY.md) — project-
  specific heap, thread-stack/frame, reference-counting, cyclic-GC, native
  PyMuPDF memory, cleanup, cancellation, and measurement guidance.

## Project overview

- [Completed implementation summary](PROJECT_IMPLEMENTATION_SUMMARY.md) — a
  consolidated account of the problem, redesign, delivered capabilities,
  workflows, artifacts, tests, safety decisions, limitations, and delivery
  references.

## Current architecture/research

- [Multi-airport extraction research](research/MULTI_AIRPORT_EXTRACTION_RESEARCH.md)
  — why VOBL-only assumptions fail on VOMM, standards references, PDF/layout
  findings, safe support boundary, and upload-first UX decision.
- [Multi-airport extraction design](architecture/MULTI_AIRPORT_DESIGN.md) —
  page-aware evidence, deterministic adapters, required/optional gates,
  completeness state machine, profile isolation, and notebook run contract.
- [POC design](architecture/POC_DESIGN.md) — current package/trust boundaries and
  acceptance criteria.
- [Enterprise airport-chart extraction research](research/ENTERPRISE_AIRPORT_CHART_EXTRACTION_RESEARCH.md)
  — long-term extraction, validation, search, review, and delivery architecture.

## Historical governance/benchmark phases

- **Phase 0 — blocked:** governance artifacts exist, but source rights and named
  accountable review roles remain unresolved. See the
  [Phase 0 exit report](phase-0/PHASE_0_EXIT_REPORT.md).
- **Phase 1 — historical/provisional benchmark:** deterministic normalization
  fixtures/results are retained as evidence. See the
  [discovery benchmark](phase-1/PHASE_1_DISCOVERY_BENCHMARK_REPORT.md) and
  [exit report](phase-1/PHASE_1_EXIT_REPORT.md).

`phase-1/scripts/normalize_and_validate.py` is historical benchmark code. The
current application lives in `src/airport_ocr/`; the current planning contract
lives in [`../planning/`](../planning/).
