"""Versioned FastAPI controllers for health and PDF extraction."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Dict

from fastapi import APIRouter, File, Form, Request, UploadFile

from airport_ocr.api.errors import ApplicationError
from airport_ocr.api.models import (
    AppSettings,
    ExtractionOptions,
    ExtractionResponse,
    HealthResponse,
    ProblemDetail,
)
from airport_ocr.services.pdf_extraction import (
    ExtractionLimits,
    PdfProcessingError,
    extract_pdf_bytes,
)

router = APIRouter(prefix="/api/v1", tags=["airport-extraction"])


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


async def _run_admitted_extraction(
    request: Request,
    payload: bytes,
    filename: str,
    limits: ExtractionLimits,
    admission_token: object,
) -> Dict[str, Any]:
    """Retain an admitted slot until native work ends, including cancellation."""
    try:
        return await asyncio.to_thread(extract_pdf_bytes, payload, filename, limits)
    finally:
        request.app.state.extraction_slots.put_nowait(admission_token)


def _consume_finished_extraction(task: asyncio.Task, active: set) -> None:
    active.discard(task)
    try:
        task.exception()
    except asyncio.CancelledError:
        pass


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
    responses={
        413: _problem_response_doc("PDF exceeds 5 MiB"),
        415: _problem_response_doc("Upload is not a PDF"),
        422: _problem_response_doc("Validation or extraction failed"),
        503: _problem_response_doc("All extraction slots are active"),
        500: _problem_response_doc("Unexpected service failure"),
    },
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
) -> ExtractionResponse:
    admission_token = None
    token_transferred = False
    try:
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

        try:
            admission_token = request.app.state.extraction_slots.get_nowait()
        except asyncio.QueueEmpty as exc:
            raise ApplicationError(
                status_code=503,
                code="EXTRACTION_CAPACITY_EXHAUSTED",
                title="Extraction service busy",
                detail="All local extraction slots are active; retry after one completes.",
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
                _run_admitted_extraction(
                    request,
                    payload,
                    filename,
                    limits,
                    admission_token,
                )
            )
            token_transferred = True
            active.add(task)
            task.add_done_callback(
                lambda completed: _consume_finished_extraction(completed, active)
            )
            result = await asyncio.shield(task)
            return ExtractionResponse.model_validate(result)
        except PdfProcessingError as exc:
            raise ApplicationError(
                status_code=422,
                code=exc.code,
                title="PDF extraction failed",
                detail=exc.message,
                context=exc.context,
            ) from exc
    finally:
        if admission_token is not None and not token_transferred:
            request.app.state.extraction_slots.put_nowait(admission_token)
        await file.close()
