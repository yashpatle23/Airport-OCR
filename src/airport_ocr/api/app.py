"""FastAPI application factory for the portable local Airport-OCR service."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional, Set

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from airport_ocr.api.errors import ApplicationError
from airport_ocr.api.models import AppSettings, FieldViolation, ProblemDetail
from airport_ocr.api.routes import router

_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
_LOGGER = logging.getLogger(__name__)


def _problem_response(problem: ProblemDetail) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json"),
        media_type="application/problem+json",
    )


class _SafetyHeadersMiddleware:
    """Pure ASGI middleware that preserves client-facing send backpressure."""

    def __init__(self, application: Any) -> None:
        self.application = application

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        async def send_with_safety_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                names = {name.lower() for name, _ in headers}
                safety_headers = {
                    b"x-operational-use": b"false",
                    b"cache-control": b"no-store",
                    b"x-content-type-options": b"nosniff",
                    b"referrer-policy": b"no-referrer",
                    b"content-security-policy": (
                        b"default-src 'self'; object-src 'none'; base-uri 'none'; "
                        b"form-action 'self'; frame-ancestors 'none'"
                    ),
                }
                headers.extend(
                    (name, value)
                    for name, value in safety_headers.items()
                    if name not in names
                )
                message["headers"] = headers
            await send(message)

        await self.application(scope, receive, send_with_safety_headers)


def create_app(settings: Optional[AppSettings] = None) -> FastAPI:
    """Create a stateless ASGI application with request-scoped extraction."""
    resolved = settings or AppSettings.from_environment()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # asyncio primitives are created on the Uvicorn event loop. The bounded
        # token queue provides non-blocking admission without retaining queued
        # PDF payloads and avoids cross-loop waiters on Python 3.9.
        application.state.extraction_slots = asyncio.Queue(
            maxsize=resolved.max_concurrent_extractions
        )
        for _ in range(resolved.max_concurrent_extractions):
            application.state.extraction_slots.put_nowait(object())
        application.state.active_extractions = set()
        yield
        active: Set[asyncio.Task] = application.state.active_extractions
        if active:
            await asyncio.gather(*list(active), return_exceptions=True)

    application = FastAPI(
        title="Airport-OCR Local API",
        summary="Non-operational aerodrome-chart PDF extraction service",
        version=resolved.service_version,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = resolved
    application.add_middleware(_SafetyHeadersMiddleware)

    @application.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request, exc: ApplicationError
    ) -> JSONResponse:
        return _problem_response(
            ProblemDetail(
                title=exc.title,
                status=exc.status_code,
                code=exc.code,
                detail=exc.detail,
                context=exc.context,
            )
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        violations = [
            FieldViolation(
                field=".".join(str(part) for part in error.get("loc", [])),
                message=error.get("msg", "Invalid request value"),
                error_type=error.get("type"),
            )
            for error in exc.errors()
        ]
        return _problem_response(
            ProblemDetail(
                title="Request validation failed",
                status=422,
                code="REQUEST_VALIDATION_FAILED",
                detail="One or more request fields are invalid.",
                violations=violations,
            )
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        titles = {
            400: "Bad request",
            404: "Resource not found",
            405: "Method not allowed",
        }
        return _problem_response(
            ProblemDetail(
                title=titles.get(exc.status_code, "HTTP request failed"),
                status=exc.status_code,
                code=f"HTTP_{exc.status_code}",
                detail=str(exc.detail),
            )
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        _LOGGER.exception(
            "Unhandled Airport-OCR request failure: %s %s",
            request.method,
            request.url.path,
            exc_info=True,
        )
        return _problem_response(
            ProblemDetail(
                title="Internal server error",
                status=500,
                code="INTERNAL_ERROR",
                detail="The request could not be completed.",
            )
        )

    application.include_router(router)
    application.mount("/assets", StaticFiles(directory=_STATIC_DIR), name="assets")

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")

    return application


app = create_app()
