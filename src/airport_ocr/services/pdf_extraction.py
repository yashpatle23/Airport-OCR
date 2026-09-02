"""Synchronous PDF application service.

PyMuPDF is isolated in this adapter. FastAPI offloads this CPU/native-library
work with ``asyncio.to_thread`` so it never blocks the ASGI event loop directly.
The full-pipeline entry point mirrors the deterministic Colab stages without
filesystem persistence or outbound model calls.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pymupdf

from airport_ocr.holding import holding_candidates
from airport_ocr.pdf_words import ExtractionError, extract_from_words
from airport_ocr.pipeline import PipelineError, normalize
from airport_ocr.report import build_package, render_html, summarize
from airport_ocr.search import search_features


@dataclass(frozen=True)
class ExtractionLimits:
    max_pages: int
    max_native_words: int
    max_drawings_per_page: int
    max_vector_segments: int


@dataclass(frozen=True)
class ExtractionCore:
    """Shared deterministic extraction result before API-specific assembly."""

    filename: str
    byte_size: int
    digest: str
    run_id: str
    pages: List[Dict[str, Any]]
    total_words: int
    total_segments: int
    observations: Dict[str, Any]
    normalized: Dict[str, Any]
    geojson: Dict[str, Any]
    validation: Dict[str, Any]
    holding: Dict[str, Any]
    package: Dict[str, Any]


class PdfProcessingError(ValueError):
    """Expected PDF/domain processing error safe to expose through the API."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context or {}


def _safe_stem(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-_.").lower()
    return cleaned or "airport-chart"


def _is_black(value: Any) -> bool:
    if value is None:
        return False
    try:
        return all(abs(float(component)) <= 0.01 for component in value[:3])
    except (TypeError, ValueError):
        return False


def _black_segments(
    page: Any,
    *,
    max_drawings: int,
    max_segments: int,
) -> List[Tuple[float, float, float, float]]:
    drawings = page.get_drawings()
    if len(drawings) > max_drawings:
        raise PdfProcessingError(
            "PDF_DRAWING_LIMIT_EXCEEDED",
            "A PDF page contains more vector drawings than this local service allows.",
            context={"drawing_count": len(drawings), "max_drawings_per_page": max_drawings},
        )

    segments: List[Tuple[float, float, float, float]] = []
    for drawing in drawings:
        if not (_is_black(drawing.get("color")) or _is_black(drawing.get("fill"))):
            continue
        for item in drawing.get("items", []):
            if item[0] == "l":
                if len(segments) + 1 > max_segments:
                    raise PdfProcessingError(
                        "PDF_VECTOR_SEGMENT_LIMIT_EXCEEDED",
                        "The PDF contains more vector segments than this local service allows.",
                        context={"max_vector_segments": max_segments},
                    )
                first, second = item[1], item[2]
                segments.append((first.x, first.y, second.x, second.y))
            elif item[0] == "re":
                if len(segments) + 4 > max_segments:
                    raise PdfProcessingError(
                        "PDF_VECTOR_SEGMENT_LIMIT_EXCEEDED",
                        "The PDF contains more vector segments than this local service allows.",
                        context={"max_vector_segments": max_segments},
                    )
                rect = item[1]
                segments.extend(
                    [
                        (rect.x0, rect.y0, rect.x1, rect.y0),
                        (rect.x1, rect.y0, rect.x1, rect.y1),
                        (rect.x1, rect.y1, rect.x0, rect.y1),
                        (rect.x0, rect.y1, rect.x0, rect.y0),
                    ]
                )
    return segments


def _holding_collection(
    pages: Sequence[Dict[str, Any]],
    page_segments: Sequence[Sequence[Tuple[float, float, float, float]]],
    observations: Dict[str, Any],
) -> Dict[str, Any]:
    known = {feature["designator"] for feature in observations["taxiways"]["features"]}
    features: List[Dict[str, Any]] = []
    detectors: List[Dict[str, Any]] = []
    for page_data, segments in zip(pages, page_segments):
        labels = []
        for word in page_data["words"]:
            token = str(word[4]).strip().strip(".,&\"'“”")
            if token in known:
                labels.append(
                    {
                        "designator": token,
                        "x": (word[0] + word[2]) / 2,
                        "y": (word[1] + word[3]) / 2,
                    }
                )
        result = holding_candidates(
            segments,
            labels,
            airport_icao=observations["airport_icao"],
            page_number=page_data["page"],
            page_size=page_data["size"],
            cell=14.0,
            min_segments=6,
            max_label_distance=80.0,
        )
        features.extend(result["features"])
        detectors.append(result["detector"])

    return {
        "feature_type": "runway_holding_position_collection",
        "features": features,
        "presence_observed": True,
        "empty_array_semantics": "CANDIDATES_NOT_ACCEPTED",
        "completeness_status": "CANDIDATES_PENDING_REVIEW",
        "operational_use": False,
        "detector": {"method": "per-page black-linework clustering", "pages": detectors},
        "review_required": True,
        "warning": "UNVERIFIED candidates; false positives expected; never use operationally.",
    }


def _extraction_error_code(message: str) -> str:
    for code in (
        "UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED",
        "UNSUPPORTED_LAYOUT",
    ):
        if message.startswith(code):
            return code
    return "PDF_EXTRACTION_FAILED"


def _artifact_descriptor(
    *,
    key: str,
    filename: str,
    media_type: str,
    content_ref: str,
) -> Dict[str, Any]:
    return {
        "key": key,
        "filename": filename,
        "media_type": media_type,
        "content_ref": content_ref,
    }


def _pipeline_stages(
    observations: Dict[str, Any],
    validation: Dict[str, Any],
    holding: Dict[str, Any],
) -> List[Dict[str, Any]]:
    extraction = observations.get("extraction") or {}
    extraction_status = extraction.get("status", "NOT_REPORTED")
    validation_status = validation.get("status", "NOT_REPORTED")
    return [
        {"id": "intake", "label": "Controlled intake", "status": "COMPLETE"},
        {
            "id": "native_text",
            "label": "All-page native text and vector evidence",
            "status": "COMPLETE",
        },
        {
            "id": "identify",
            "label": "Airport and layout identification",
            "status": extraction_status,
        },
        {
            "id": "holding_candidates",
            "label": "Runway holding candidates",
            "status": holding.get("completeness_status", "NEEDS_REVIEW"),
        },
        {
            "id": "normalize_validate",
            "label": "Normalize and validate",
            "status": validation_status,
        },
        {"id": "search", "label": "GeoJSON search projection", "status": "COMPLETE"},
        {"id": "report", "label": "Summary and report", "status": "COMPLETE"},
        {"id": "artifacts", "label": "Download artifacts", "status": "READY"},
    ]


def _pipeline_status(
    observations: Dict[str, Any],
    validation: Dict[str, Any],
) -> str:
    """Compose one run status without masking failed validation."""
    extraction_status = (observations.get("extraction") or {}).get("status")
    validation_status = validation.get("status")
    if validation_status == "FAIL" or validation.get("failure_count", 0) > 0:
        return "FAIL"
    if extraction_status == "PARTIAL":
        return "PARTIAL"
    if validation_status == "PASS_WITH_EXPECTED_BLOCKERS":
        return "PASS_WITH_EXPECTED_BLOCKERS"
    if extraction_status == "COMPLETE":
        return "COMPLETE"
    return "NOT_REPORTED"


def _document_research(
    observations: Dict[str, Any],
    normalized: Dict[str, Any],
    geojson: Dict[str, Any],
    validation: Dict[str, Any],
    holding: Dict[str, Any],
    package: Dict[str, Any],
) -> Dict[str, Any]:
    airport = package["airport"]
    runway_pairs = [runway["designator_pair"] for runway in package["runways"]]
    first_designator = None
    if package["runways"] and package["runways"][0].get("directions"):
        first_designator = package["runways"][0]["directions"][0].get("designator")

    search_examples: Dict[str, Any] = {
        "airport": search_features(geojson, airport_icao=airport["icao"]),
    }
    if first_designator:
        search_examples["first_runway_designator"] = search_features(
            geojson,
            designator=first_designator,
        )

    return {
        "title": "Document-derived research outline",
        "scope": (
            "Deterministic findings extracted from the uploaded chart; this is not "
            "external research or authoritative aeronautical data."
        ),
        "document_findings": {
            "airport_icao": airport.get("icao"),
            "airport_name": airport.get("name"),
            "runway_pairs": runway_pairs,
            "taxiway_count": package["taxiways"].get("count", 0),
            "holding_candidate_count": holding.get("features")
            and len(holding["features"])
            or 0,
            "extraction_status": (normalized.get("extraction") or {}).get("status"),
            "validation_status": validation.get("status"),
            "validation_failure_count": validation.get("failure_count", 0),
            "validation_expected_blocker_count": validation.get("blocker_count", 0),
        },
        "extraction_diagnostics": observations.get("extraction", {}),
        "search_examples": search_examples,
        "supported_input_boundary": [
            "Native-text AAI/ICAO-style aerodrome charts supported by deterministic adapters.",
            "Scanned or image-only PDFs require a future OCR adapter and stop safely.",
            "Taxiway references and black-line holding clusters remain review candidates.",
            "Declared distances are never substituted for physical runway dimensions.",
        ],
        "limitations": [
            "Source permission is attested by the user and not independently verified.",
            "The upload is not malware-scanned by this application.",
            "The result is provisional, non-operational, and not for navigation.",
            "Optional AI paraphrasing is skipped in the local offline pipeline.",
        ],
    }


def _extract_core(
    payload: bytes,
    filename: str,
    limits: ExtractionLimits,
) -> ExtractionCore:
    """Run shared PDF extraction and deterministic domain assembly in memory."""
    digest = hashlib.sha256(payload).hexdigest()
    run_id = f"{_safe_stem(filename)}-{digest[:8]}"

    try:
        document = pymupdf.open(stream=payload, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise PdfProcessingError("INVALID_PDF", "The uploaded bytes are not a readable PDF.") from exc

    try:
        if document.needs_pass:
            raise PdfProcessingError(
                "ENCRYPTED_PDF_UNSUPPORTED",
                "Password-protected PDFs are not supported.",
            )
        if document.page_count == 0:
            raise PdfProcessingError("EMPTY_PDF", "The PDF does not contain any pages.")
        if document.page_count > limits.max_pages:
            raise PdfProcessingError(
                "PDF_PAGE_LIMIT_EXCEEDED",
                f"The PDF has {document.page_count} pages; the limit is {limits.max_pages}.",
                context={"page_count": document.page_count, "max_pages": limits.max_pages},
            )

        pages: List[Dict[str, Any]] = []
        segments_by_page: List[List[Tuple[float, float, float, float]]] = []
        total_words = 0
        total_segments = 0
        for index, page in enumerate(document):
            words = page.get_text("words")
            total_words += len(words)
            if total_words > limits.max_native_words:
                raise PdfProcessingError(
                    "PDF_WORD_LIMIT_EXCEEDED",
                    "The PDF contains more positioned words than this local service allows.",
                    context={
                        "native_word_count": total_words,
                        "max_native_words": limits.max_native_words,
                    },
                )
            pages.append(
                {
                    "page": index,
                    "size": [page.rect.width, page.rect.height],
                    "words": words,
                }
            )
            page_segments = _black_segments(
                page,
                max_drawings=limits.max_drawings_per_page,
                max_segments=limits.max_vector_segments - total_segments,
            )
            total_segments += len(page_segments)
            segments_by_page.append(page_segments)

        source_metadata = {
            "source_id": f"upload:{digest[:16]}",
            "source_path": filename,
            "source_url": None,
            "sha256": digest,
            "original_bytes_available": True,
            "rights_status": "UNCONFIRMED_PERMISSION_REQUIRED",
            "publisher_context": [],
        }
        observations = extract_from_words(
            pages,
            dataset_id=run_id,
            source_metadata=source_metadata,
            profile="auto",
        )
        normalized, geojson, validation = normalize(observations)
        holding = _holding_collection(pages, segments_by_page, observations)
        package = build_package(normalized, validation, holding_candidates=holding)
        return ExtractionCore(
            filename=filename,
            byte_size=len(payload),
            digest=digest,
            run_id=run_id,
            pages=pages,
            total_words=total_words,
            total_segments=total_segments,
            observations=observations,
            normalized=normalized,
            geojson=geojson,
            validation=validation,
            holding=holding,
            package=package,
        )
    except ExtractionError as exc:
        message = str(exc)
        raise PdfProcessingError(_extraction_error_code(message), message) from exc
    except PipelineError as exc:
        raise PdfProcessingError("NORMALIZATION_FAILED", str(exc)) from exc
    except (pymupdf.FileDataError, RuntimeError) as exc:
        raise PdfProcessingError(
            "INVALID_PDF",
            "The PDF could not be traversed as a readable native-text document.",
        ) from exc
    finally:
        document.close()


def _full_intake(core: ExtractionCore) -> Dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "filename": core.filename,
        "run_id": core.run_id,
        "byte_size": core.byte_size,
        "sha256": core.digest,
        "detected_media_type": "application/pdf",
        "extension_signature_match": True,
        "original_bytes_available": True,
        "permission_attested": True,
        "rights_status": "UNCONFIRMED_PERMISSION_REQUIRED",
        "malware_status": "NOT_SCANNED",
        "intake_status": "ACCEPTED_FOR_LOCAL_RESEARCH_PROCESSING",
        "warnings": [
            "Permission is user-attested and has not been independently verified.",
            "The file has not been malware-scanned by this application.",
            "No source or result is persisted by the application after the request.",
        ],
    }


def _assemble_full(core: ExtractionCore) -> Dict[str, Any]:
    summary_markdown = summarize(core.package)
    report_html = render_html(core.package)
    research = _document_research(
        core.observations,
        core.normalized,
        core.geojson,
        core.validation,
        core.holding,
        core.package,
    )
    intake = _full_intake(core)
    results = {
        "observations": core.observations,
        "holding_candidates": core.holding,
        "normalized": core.normalized,
        "geojson": core.geojson,
        "validation": core.validation,
        "package": core.package,
    }
    summary = {
        "markdown": summary_markdown,
        "report_html": report_html,
        "ai": {
            "status": "SKIPPED_OFFLINE_POLICY",
            "markdown": None,
            "detail": "The local pipeline makes no outbound AI request.",
        },
    }
    run = {
        "run_id": core.run_id,
        "source_filename": core.filename,
        "sha256": core.digest,
        "airport_icao": core.package["airport"].get("icao"),
        "page_count": len(core.pages),
        "native_word_count": core.total_words,
        "black_vector_segment_count": core.total_segments,
    }
    pipeline = {
        "status": _pipeline_status(core.observations, core.validation),
        "flow": "PDF -> Intake -> Extract -> Identify -> Validate -> Structure -> Search -> Report -> Artifacts",
        "stages": _pipeline_stages(
            core.observations,
            core.validation,
            core.holding,
        ),
    }
    evidence = {
        "positioned_words": core.pages,
        "page_count": len(core.pages),
        "native_word_count": core.total_words,
        "black_vector_segment_count": core.total_segments,
        "vector_segments_retained_in_response": False,
    }

    artifact_specs = [
        ("intake", "intake.json", "application/json", "#/intake"),
        ("words", "words.json", "application/json", "#/evidence/positioned_words"),
        (
            "observations",
            "observations.json",
            "application/json",
            "#/results/observations",
        ),
        (
            "holding_candidates",
            "holding-candidates.json",
            "application/json",
            "#/results/holding_candidates",
        ),
        (
            "normalized",
            "normalized.json",
            "application/json",
            "#/results/normalized",
        ),
        (
            "geojson",
            "features.geojson",
            "application/geo+json",
            "#/results/geojson",
        ),
        (
            "validation",
            "validation.json",
            "application/json",
            "#/results/validation",
        ),
        ("package", "package.json", "application/json", "#/results/package"),
        ("summary", "summary.md", "text/markdown", "#/summary/markdown"),
        ("report", "report.html", "text/html", "#/summary/report_html"),
    ]
    artifacts = [
        _artifact_descriptor(
            key=key,
            filename=f"{core.run_id}-{suffix}",
            media_type=media_type,
            content_ref=content_ref,
        )
        for key, suffix, media_type, content_ref in artifact_specs
    ]
    manifest = {
        "run_id": core.run_id,
        "source_filename": core.filename,
        "sha256": core.digest,
        "airport_icao": core.package["airport"].get("icao"),
        "operational_use": False,
        "pipeline_status": pipeline["status"],
        "ai_summary_status": summary["ai"]["status"],
        "artifacts": [artifact["filename"] for artifact in artifacts],
    }
    artifacts.append(
        _artifact_descriptor(
            key="manifest",
            filename=f"{core.run_id}-manifest.json",
            media_type="application/json",
            content_ref="#/manifest",
        )
    )

    return {
        "api_version": "v1",
        "operational_use": False,
        "run": run,
        "intake": intake,
        "pipeline": pipeline,
        "evidence": evidence,
        "results": results,
        "research": research,
        "summary": summary,
        "artifacts": artifacts,
        "manifest": manifest,
    }


def extract_full_pipeline_bytes(
    payload: bytes,
    filename: str,
    limits: ExtractionLimits,
) -> Dict[str, Any]:
    """Run the complete request-scoped PDF-to-artifacts pipeline in memory."""
    return _assemble_full(_extract_core(payload, filename, limits))


def extract_pdf_bytes(
    payload: bytes,
    filename: str,
    limits: ExtractionLimits,
) -> Dict[str, Any]:
    """Return the original compact v1 extraction envelope for compatibility."""
    core = _extract_core(payload, filename, limits)
    return {
        "api_version": "v1",
        "operational_use": False,
        "intake": {
            "filename": core.filename,
            "byte_size": core.byte_size,
            "sha256": core.digest,
            "detected_media_type": "application/pdf",
            "permission_attested": True,
            "rights_status": "UNCONFIRMED_PERMISSION_REQUIRED",
            "malware_status": "NOT_SCANNED",
            "warnings": [
                "Permission is user-attested and has not been independently verified.",
                "The file has not been malware-scanned by this application.",
            ],
        },
        "observations": core.observations,
        "normalized": core.normalized,
        "geojson": core.geojson,
        "validation": core.validation,
        "holding_candidates": core.holding,
        "package": core.package,
        "summary_markdown": summarize(core.package),
    }
