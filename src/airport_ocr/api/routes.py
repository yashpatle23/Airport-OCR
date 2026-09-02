"""Versioned FastAPI controllers for health and PDF processing."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Callable, Dict, Type

from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from pydantic import BaseModel

from airport_ocr.api.errors import ApplicationError
from airport_ocr.api.models import (
    AppSettings,
    ExtractionOptions,
    ExtractionResponse,
    HealthResponse,
    PipelineRunResponse,
    ProblemDetail,
)
from airport_ocr.services.pdf_extraction import (
    ExtractionLimits,
    PdfProcessingError,
    extract_full_pipeline_bytes,
    extract_pdf_bytes,
)

router = APIRouter(prefix="/api/v1", tags=["airport-extraction"])
Extractor = Callable[[bytes, str, ExtractionLimits], Dict[str, Any]]
ResponseModel = Type[BaseModel]


class _AdmissionReleasingResponse(Response):
    """Release one processing slot after the ASGI body handoff finishes."""

    media_type = "application/json"

    def __init__(self, content: bytes, request: Request, admission_token: object) -> None:
        super().__init__(content=content, media_type=self.media_type)
        self._slot_queue = request.app.state.extraction_slots
        self._admission_token = admission_token
        self._released = False

    def _release(self) -> None:
        if not self._released:
            self._slot_queue.put_nowait(self._admission_token)
            self._released = True

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._release()


def _problem_response_doc(description: str) -> Dict[str, Any]:
    """Document the same problem media type emitted by exception handlers."""
    return {
        "description": description,
        "content": {
            "application/problem+json": {
                "schema": ProblemDetail.model_json_schema(),
            }
        },
    }


def _error_responses() -> Dict[int, Dict[str, Any]]:
    return {
        413: _problem_response_doc("PDF exceeds 5 MiB"),
        415: _problem_response_doc("Upload is not a PDF"),
        422: _problem_response_doc("Validation, PDF processing, or output limit failed"),
        503: _problem_response_doc("All processing slots are active"),
        500: _problem_response_doc("Unexpected service failure"),
    }


def _safe_filename(raw: str) -> str:
    return raw.replace("\\", "/").rsplit("/", 1)[-1].strip()


async def _read_validated_pdf(upload: UploadFile, settings: AppSettings) -> tuple[str, bytes]:
    filename = _safe_filename(upload.filename or "")
    if not filename:
        raise ApplicationError(
            status_code=422,
            code="PDF_FILENAME_REQUIRED",
            title="PDF filename required",
            detail="The multipart upload must include a filename.",
        )
    if not filename.lower().endswith(".pdf"):
        raise ApplicationError(
            status_code=415,
            code="PDF_EXTENSION_REQUIRED",
            title="Unsupported media type",
            detail="Only files with a .pdf extension are accepted.",
        )
    if upload.content_type != "application/pdf":
        raise ApplicationError(
            status_code=415,
            code="PDF_CONTENT_TYPE_REQUIRED",
            title="Unsupported media type",
            detail="The multipart content type must be application/pdf.",
            context={"received_content_type": upload.content_type},
        )

    payload = bytearray()
    while True:
        chunk = await upload.read(settings.upload_chunk_bytes)
        if not chunk:
            break
        if len(payload) + len(chunk) > settings.max_pdf_bytes:
            raise ApplicationError(
                status_code=413,
                code="PDF_SIZE_LIMIT_EXCEEDED",
                title="PDF too large",
                detail=f"The PDF exceeds the {settings.max_pdf_bytes}-byte (5 MiB) limit.",
                context={"max_pdf_bytes": settings.max_pdf_bytes},
            )
        payload.extend(chunk)

    if not payload:
        raise ApplicationError(
            status_code=422,
            code="EMPTY_PDF_UPLOAD",
            title="Empty upload",
            detail="The uploaded PDF is empty.",
        )
    if not payload.startswith(b"%PDF-"):
        raise ApplicationError(
            status_code=415,
            code="PDF_SIGNATURE_REQUIRED",
            title="Unsupported media type",
            detail="The uploaded bytes do not have a PDF signature.",
        )
    return filename, bytes(payload)


def _extract_validate_and_serialize(
    payload: bytes,
    filename: str,
    limits: ExtractionLimits,
    extractor: Extractor,
    response_model: ResponseModel,
    max_response_bytes: int,
) -> bytes:
    """Run, validate, and encode one response within the admitted worker."""
    result = extractor(payload, filename, limits)
    validated = response_model.model_validate(result)
    encoded = validated.model_dump_json(exclude_unset=True).encode("utf-8")
    if len(encoded) > max_response_bytes:
        raise PdfProcessingError(
            "PIPELINE_OUTPUT_LIMIT_EXCEEDED",
            "The generated response exceeds the configured local output limit.",
            context={
                "response_bytes": len(encoded),
                "max_pipeline_response_bytes": max_response_bytes,
            },
        )
    return encoded


async def _run_admitted_processing(
    request: Request,
    payload: bytes,
    filename: str,
    limits: ExtractionLimits,
    admission_token: object,
    extractor: Extractor,
    response_model: ResponseModel,
    max_response_bytes: int,
) -> bytes:
    """Retain a slot through native work, model validation, and JSON encoding."""
    queue = request.app.state.extraction_slots
    worker = asyncio.create_task(
        asyncio.to_thread(
            _extract_validate_and_serialize,
            payload,
            filename,
            limits,
            extractor,
            response_model,
            max_response_bytes,
        )
    )
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        # Native work cannot be cancelled safely. Wait for it before releasing
        # the slot if the tracked processing task itself is cancelled.
        try:
            await asyncio.shield(worker)
        finally:
            queue.put_nowait(admission_token)
        raise
    except Exception:
        queue.put_nowait(admission_token)
        raise


def _consume_finished_processing(task: asyncio.Task, active: set) -> None:
    active.discard(task)
    try:
        task.exception()
    except asyncio.CancelledError:
        pass


def _release_abandoned_success(
    task: asyncio.Task,
    request: Request,
    admission_token: object,
) -> None:
    """Release a successful result that lost its disconnected request owner."""
    try:
        task.result()
    except (asyncio.CancelledError, Exception):
        # Failure paths release inside _run_admitted_processing.
        return
    request.app.state.extraction_slots.put_nowait(admission_token)


def _validate_options(permission_confirmed: bool, profile: str) -> None:
    try:
        ExtractionOptions(
            permission_confirmed=permission_confirmed,
            profile=profile,
        )
    except ValueError as exc:
        raise ApplicationError(
            status_code=422,
            code="INVALID_EXTRACTION_OPTIONS",
            title="Invalid extraction options",
            detail="Permission confirmation is required and profile must be 'auto'.",
        ) from exc


async def _process_pdf_request(
    request: Request,
    file: UploadFile,
    permission_confirmed: bool,
    profile: str,
    extractor: Extractor,
    response_model: ResponseModel,
) -> Response:
    admission_token = None
    token_transferred = False
    try:
        _validate_options(permission_confirmed, profile)
        try:
            admission_token = request.app.state.extraction_slots.get_nowait()
        except asyncio.QueueEmpty as exc:
            raise ApplicationError(
                status_code=503,
                code="EXTRACTION_CAPACITY_EXHAUSTED",
                title="PDF processing service busy",
                detail="All local processing slots are active; retry after one completes.",
                context={"retryable": True},
            ) from exc

        settings: AppSettings = request.app.state.settings
        try:
            filename, payload = await _read_validated_pdf(file, settings)
            limits = ExtractionLimits(
                max_pages=settings.max_pdf_pages,
                max_native_words=settings.max_native_words,
                max_drawings_per_page=settings.max_drawings_per_page,
                max_vector_segments=settings.max_vector_segments,
            )
            active = request.app.state.active_extractions
            task = asyncio.create_task(
                _run_admitted_processing(
                    request,
                    payload,
                    filename,
                    limits,
                    admission_token,
                    extractor,
                    response_model,
                    settings.max_pipeline_response_bytes,
                )
            )
            token_transferred = True
            active.add(task)
            task.add_done_callback(
                lambda completed: _consume_finished_processing(completed, active)
            )
            try:
                content = await asyncio.shield(task)
            except asyncio.CancelledError:
                task.add_done_callback(
                    lambda completed: _release_abandoned_success(
                        completed,
                        request,
                        admission_token,
                    )
                )
                raise
            return _AdmissionReleasingResponse(content, request, admission_token)
        except PdfProcessingError as exc:
            raise ApplicationError(
                status_code=422,
                code=exc.code,
                title="PDF processing failed",
                detail=exc.message,
                context=exc.context,
            ) from exc
    finally:
        if admission_token is not None and not token_transferred:
            request.app.state.extraction_slots.put_nowait(admission_token)
        await file.close()


@router.get("/health", response_model=HealthResponse, summary="Service health")
async def health(request: Request) -> HealthResponse:
    settings: AppSettings = request.app.state.settings
    return HealthResponse(
        service=settings.service_name,
        version=settings.service_version,
        max_pdf_bytes=settings.max_pdf_bytes,
    )


@router.post(
    "/extractions",
    response_model=ExtractionResponse,
    responses=_error_responses(),
    summary="Upload and extract one aerodrome-chart PDF",
)
async def create_extraction(
    request: Request,
    file: Annotated[UploadFile, File(description="One aerodrome-chart PDF, maximum 5 MiB")],
    permission_confirmed: Annotated[
        bool, Form(description="Must be true to attest permission to process the PDF")
    ] = False,
    profile: Annotated[
        str, Form(description="Extraction profile; only 'auto' is accepted")
    ] = "auto",
) -> Response:
    return await _process_pdf_request(
        request,
        file,
        permission_confirmed,
        profile,
        extract_pdf_bytes,
        ExtractionResponse,
    )


@router.post(
    "/pipeline-runs",
    response_model=PipelineRunResponse,
    responses=_error_responses(),
    summary="Run the complete local PDF-to-research-artifacts pipeline",
)
async def create_pipeline_run(
    request: Request,
    file: Annotated[UploadFile, File(description="One aerodrome-chart PDF, maximum 5 MiB")],
    permission_confirmed: Annotated[
        bool, Form(description="Must be true to attest permission to process the PDF")
    ] = False,
    profile: Annotated[
        str, Form(description="Extraction profile; only 'auto' is accepted")
    ] = "auto",
) -> Response:
    return await _process_pdf_request(
        request,
        file,
        permission_confirmed,
        profile,
        extract_full_pipeline_bytes,
        PipelineRunResponse,
    )
