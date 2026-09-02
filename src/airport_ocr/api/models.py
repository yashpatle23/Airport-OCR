"""Validated API DTOs and local application settings.

The API layer follows a Spring-style contract boundary: request options and
response envelopes are explicit Pydantic models, while the deterministic domain
payloads remain owned by the framework-independent core.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from airport_ocr import __version__

MAX_PDF_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_PIPELINE_RESPONSE_BYTES = 64 * 1024 * 1024
MAX_PIPELINE_RESPONSE_BYTES = 128 * 1024 * 1024

RunStatus = Literal[
    "FAIL",
    "PARTIAL",
    "PASS_WITH_EXPECTED_BLOCKERS",
    "COMPLETE",
    "NOT_REPORTED",
]
StageStatus = Literal[
    "COMPLETE",
    "PARTIAL",
    "FAIL",
    "PASS_WITH_EXPECTED_BLOCKERS",
    "CANDIDATES_PENDING_REVIEW",
    "NEEDS_REVIEW",
    "READY",
    "NOT_REPORTED",
]
ArtifactKey = Literal[
    "intake",
    "words",
    "observations",
    "holding_candidates",
    "normalized",
    "geojson",
    "validation",
    "package",
    "summary",
    "report",
    "manifest",
]


class ApiModel(BaseModel):
    """Base DTO that rejects undeclared fields."""

    model_config = ConfigDict(extra="forbid")


class AppSettings(ApiModel):
    """Validated local service settings loaded from environment variables."""

    service_name: str = "airport-ocr"
    service_version: str = __version__
    max_pdf_bytes: int = Field(default=MAX_PDF_BYTES, ge=1, le=MAX_PDF_BYTES)
    max_pipeline_response_bytes: int = Field(
        default=DEFAULT_MAX_PIPELINE_RESPONSE_BYTES,
        ge=1024 * 1024,
        le=MAX_PIPELINE_RESPONSE_BYTES,
    )
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
            max_pipeline_response_bytes=os.getenv(
                "AIRPORT_OCR_MAX_PIPELINE_RESPONSE_BYTES", "67108864"
            ),
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


class PipelineRunMetadata(ApiModel):
    run_id: str = Field(min_length=1)
    source_filename: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    airport_icao: Optional[str] = Field(default=None, pattern=r"^[A-Z]{4}$")
    page_count: int = Field(ge=1)
    native_word_count: int = Field(ge=1)
    black_vector_segment_count: int = Field(ge=0)


class PipelineIntake(ApiModel):
    manifest_version: Literal["1.0"]
    filename: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    byte_size: int = Field(ge=1, le=MAX_PDF_BYTES)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    detected_media_type: Literal["application/pdf"]
    extension_signature_match: Literal[True]
    original_bytes_available: Literal[True]
    permission_attested: Literal[True]
    rights_status: Literal["UNCONFIRMED_PERMISSION_REQUIRED"]
    malware_status: Literal["NOT_SCANNED"]
    intake_status: Literal["ACCEPTED_FOR_LOCAL_RESEARCH_PROCESSING"]
    warnings: List[str]


class PipelineStage(ApiModel):
    id: Literal[
        "intake",
        "native_text",
        "identify",
        "holding_candidates",
        "normalize_validate",
        "search",
        "report",
        "artifacts",
    ]
    label: str = Field(min_length=1)
    status: StageStatus


class PipelineMetadata(ApiModel):
    status: RunStatus
    flow: Literal[
        "PDF -> Intake -> Extract -> Identify -> Validate -> Structure -> Search -> Report -> Artifacts"
    ]
    stages: List[PipelineStage]

    @model_validator(mode="after")
    def validate_stage_order(self) -> "PipelineMetadata":
        expected = [
            "intake",
            "native_text",
            "identify",
            "holding_candidates",
            "normalize_validate",
            "search",
            "report",
            "artifacts",
        ]
        if [stage.id for stage in self.stages] != expected:
            raise ValueError("pipeline stages must contain the eight stages in order")
        return self


class PipelineEvidence(ApiModel):
    positioned_words: List[Dict[str, Any]]
    page_count: int = Field(ge=1)
    native_word_count: int = Field(ge=1)
    black_vector_segment_count: int = Field(ge=0)
    vector_segments_retained_in_response: Literal[False]


class PipelineResults(ApiModel):
    """Wrapper for independently versioned deterministic domain documents."""

    observations: Dict[str, Any]
    holding_candidates: Dict[str, Any]
    normalized: Dict[str, Any]
    geojson: Dict[str, Any]
    validation: Dict[str, Any]
    package: Dict[str, Any]


class DocumentFindings(ApiModel):
    airport_icao: Optional[str] = None
    airport_name: Optional[str] = None
    runway_pairs: List[str]
    taxiway_count: int = Field(ge=0)
    holding_candidate_count: int = Field(ge=0)
    extraction_status: Optional[Literal["COMPLETE", "PARTIAL"]] = None
    validation_status: Optional[
        Literal["FAIL", "PASS_WITH_EXPECTED_BLOCKERS"]
    ] = None
    validation_failure_count: int = Field(ge=0)
    validation_expected_blocker_count: int = Field(ge=0)


class SearchExamples(ApiModel):
    airport: Dict[str, Any]
    first_runway_designator: Optional[Dict[str, Any]] = None


class DocumentResearch(ApiModel):
    title: Literal["Document-derived research outline"]
    scope: str = Field(min_length=1)
    document_findings: DocumentFindings
    extraction_diagnostics: Dict[str, Any]
    search_examples: SearchExamples
    supported_input_boundary: List[str]
    limitations: List[str]


class OfflineAiSummary(ApiModel):
    status: Literal["SKIPPED_OFFLINE_POLICY"]
    markdown: None
    detail: str = Field(min_length=1)


class PipelineSummary(ApiModel):
    markdown: str
    report_html: str
    ai: OfflineAiSummary


class ArtifactDescriptor(ApiModel):
    key: ArtifactKey
    filename: str = Field(min_length=1)
    media_type: Literal[
        "application/json",
        "application/geo+json",
        "text/markdown",
        "text/html",
    ]
    content_ref: Literal[
        "#/intake",
        "#/evidence/positioned_words",
        "#/results/observations",
        "#/results/holding_candidates",
        "#/results/normalized",
        "#/results/geojson",
        "#/results/validation",
        "#/results/package",
        "#/summary/markdown",
        "#/summary/report_html",
        "#/manifest",
    ]


class ArtifactManifest(ApiModel):
    run_id: str = Field(min_length=1)
    source_filename: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    airport_icao: Optional[str] = Field(default=None, pattern=r"^[A-Z]{4}$")
    operational_use: Literal[False]
    pipeline_status: RunStatus
    ai_summary_status: Literal["SKIPPED_OFFLINE_POLICY"]
    artifacts: List[str]


class PipelineRunResponse(ApiModel):
    """Complete request-scoped equivalent of the generated Colab pipeline."""

    api_version: Literal["v1"] = "v1"
    operational_use: Literal[False] = False
    run: PipelineRunMetadata
    intake: PipelineIntake
    pipeline: PipelineMetadata
    evidence: PipelineEvidence
    results: PipelineResults
    research: DocumentResearch
    summary: PipelineSummary
    artifacts: List[ArtifactDescriptor]
    manifest: ArtifactManifest

    @model_validator(mode="after")
    def validate_envelope_consistency(self) -> "PipelineRunResponse":
        if self.run.run_id != self.intake.run_id or self.run.run_id != self.manifest.run_id:
            raise ValueError("run identifiers must match across the response")
        if self.run.sha256 != self.intake.sha256 or self.run.sha256 != self.manifest.sha256:
            raise ValueError("source digests must match across the response")
        if self.run.source_filename != self.intake.filename:
            raise ValueError("source filenames must match across the response")
        if self.run.source_filename != self.manifest.source_filename:
            raise ValueError("manifest source filename must match the run")
        if self.run.airport_icao != self.manifest.airport_icao:
            raise ValueError("airport identifiers must match across the response")
        if self.pipeline.status != self.manifest.pipeline_status:
            raise ValueError("pipeline and manifest statuses must match")
        if self.run.page_count != self.evidence.page_count:
            raise ValueError("page counts must match across the response")
        if self.run.native_word_count != self.evidence.native_word_count:
            raise ValueError("word counts must match across the response")
        if (
            self.run.black_vector_segment_count
            != self.evidence.black_vector_segment_count
        ):
            raise ValueError("vector segment counts must match across the response")

        specifications = {
            "intake": ("intake.json", "application/json", "#/intake"),
            "words": (
                "words.json",
                "application/json",
                "#/evidence/positioned_words",
            ),
            "observations": (
                "observations.json",
                "application/json",
                "#/results/observations",
            ),
            "holding_candidates": (
                "holding-candidates.json",
                "application/json",
                "#/results/holding_candidates",
            ),
            "normalized": (
                "normalized.json",
                "application/json",
                "#/results/normalized",
            ),
            "geojson": (
                "features.geojson",
                "application/geo+json",
                "#/results/geojson",
            ),
            "validation": (
                "validation.json",
                "application/json",
                "#/results/validation",
            ),
            "package": (
                "package.json",
                "application/json",
                "#/results/package",
            ),
            "summary": ("summary.md", "text/markdown", "#/summary/markdown"),
            "report": ("report.html", "text/html", "#/summary/report_html"),
            "manifest": ("manifest.json", "application/json", "#/manifest"),
        }
        if len(self.artifacts) != len(specifications):
            raise ValueError("the response must describe all eleven artifacts")
        seen_keys = set()
        seen_filenames = set()
        for artifact in self.artifacts:
            if artifact.key in seen_keys or artifact.filename in seen_filenames:
                raise ValueError("artifact keys and filenames must be unique")
            seen_keys.add(artifact.key)
            seen_filenames.add(artifact.filename)
            suffix, media_type, content_ref = specifications[artifact.key]
            if artifact.filename != f"{self.run.run_id}-{suffix}":
                raise ValueError(f"unexpected filename for artifact {artifact.key}")
            if artifact.media_type != media_type or artifact.content_ref != content_ref:
                raise ValueError(f"unexpected mapping for artifact {artifact.key}")
        if seen_keys != set(specifications):
            raise ValueError("the response must describe every artifact key exactly once")

        expected_manifest_files = [
            artifact.filename for artifact in self.artifacts if artifact.key != "manifest"
        ]
        if self.manifest.artifacts != expected_manifest_files:
            raise ValueError("manifest filenames must match non-manifest descriptors")
        return self


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
