"""Validated API DTOs and local application settings.

The API layer follows a Spring-style contract boundary: request options and
response envelopes are explicit Pydantic models, while the deterministic domain
payloads remain owned by the framework-independent core.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from airport_ocr import __version__

MAX_PDF_BYTES = 5 * 1024 * 1024


class ApiModel(BaseModel):
    """Base DTO that rejects undeclared fields."""

    model_config = ConfigDict(extra="forbid")


class AppSettings(ApiModel):
    """Validated local service settings loaded from environment variables."""

    service_name: str = "airport-ocr"
    service_version: str = __version__
    max_pdf_bytes: int = Field(default=MAX_PDF_BYTES, ge=1, le=MAX_PDF_BYTES)
    upload_chunk_bytes: int = Field(default=64 * 1024, ge=4096, le=1024 * 1024)
    max_concurrent_extractions: int = Field(default=2, ge=1, le=8)
    max_pdf_pages: int = Field(default=100, ge=1, le=500)
    max_native_words: int = Field(default=250_000, ge=1, le=1_000_000)
    max_drawings_per_page: int = Field(default=20_000, ge=1, le=100_000)
    max_vector_segments: int = Field(default=100_000, ge=1, le=1_000_000)

    @classmethod
    def from_environment(cls) -> "AppSettings":
        """Load bounded integer settings without adding pydantic-settings."""
        return cls(
            max_concurrent_extractions=os.getenv("AIRPORT_OCR_MAX_CONCURRENCY", "2"),
            max_pdf_pages=os.getenv("AIRPORT_OCR_MAX_PDF_PAGES", "100"),
            max_native_words=os.getenv("AIRPORT_OCR_MAX_NATIVE_WORDS", "250000"),
            max_drawings_per_page=os.getenv(
                "AIRPORT_OCR_MAX_DRAWINGS_PER_PAGE", "20000"
            ),
            max_vector_segments=os.getenv(
                "AIRPORT_OCR_MAX_VECTOR_SEGMENTS", "100000"
            ),
        )


class ExtractionOptions(ApiModel):
    """Validated multipart options for one extraction request."""

    permission_confirmed: Literal[True]
    profile: Literal["auto"] = "auto"


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    operational_use: Literal[False] = False
    max_pdf_bytes: int


class UploadMetadata(ApiModel):
    filename: str
    byte_size: int = Field(ge=1, le=MAX_PDF_BYTES)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    detected_media_type: Literal["application/pdf"]
    permission_attested: Literal[True]
    rights_status: str
    malware_status: str
    warnings: List[str]


class ExtractionResponse(ApiModel):
    api_version: Literal["v1"] = "v1"
    operational_use: Literal[False] = False
    intake: UploadMetadata
    observations: Dict[str, Any]
    normalized: Dict[str, Any]
    geojson: Dict[str, Any]
    validation: Dict[str, Any]
    holding_candidates: Dict[str, Any]
    package: Dict[str, Any]
    summary_markdown: str


class FieldViolation(ApiModel):
    field: str
    message: str
    error_type: Optional[str] = None


class ProblemDetail(ApiModel):
    """RFC-style structured error response, similar to Spring ProblemDetail."""

    type: str = "about:blank"
    title: str
    status: int = Field(ge=400, le=599)
    code: str
    detail: str
    operational_use: Literal[False] = False
    violations: List[FieldViolation] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
