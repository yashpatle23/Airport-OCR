"""Synchronous PDF application service.

PyMuPDF is isolated in this adapter. The FastAPI controller offloads this
CPU/native-library work with ``asyncio.to_thread`` so it never blocks the ASGI
event loop directly.
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
from airport_ocr.report import build_package, summarize


@dataclass(frozen=True)
class ExtractionLimits:
    max_pages: int
    max_native_words: int
    max_drawings_per_page: int
    max_vector_segments: int


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


def extract_pdf_bytes(
    payload: bytes,
    filename: str,
    limits: ExtractionLimits,
) -> Dict[str, Any]:
    """Extract, normalize, validate, and package one in-memory PDF."""
    digest = hashlib.sha256(payload).hexdigest()
    dataset_id = f"{_safe_stem(filename)}-{digest[:8]}"

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
            dataset_id=dataset_id,
            source_metadata=source_metadata,
            profile="auto",
        )
        normalized, geojson, validation = normalize(observations)
        # Validation failures remain visible in the returned research JSON. The
        # service never promotes them to operational data, but reviewers need
        # the extracted evidence and report together rather than a discarded
        # partial result.
        holding = _holding_collection(pages, segments_by_page, observations)
        package = build_package(normalized, validation, holding_candidates=holding)
        return {
            "api_version": "v1",
            "operational_use": False,
            "intake": {
                "filename": filename,
                "byte_size": len(payload),
                "sha256": digest,
                "detected_media_type": "application/pdf",
                "permission_attested": True,
                "rights_status": "UNCONFIRMED_PERMISSION_REQUIRED",
                "malware_status": "NOT_SCANNED",
                "warnings": [
                    "Permission is user-attested and has not been independently verified.",
                    "The file has not been malware-scanned by this application.",
                ],
            },
            "observations": observations,
            "normalized": normalized,
            "geojson": geojson,
            "validation": validation,
            "holding_candidates": holding,
            "package": package,
            "summary_markdown": summarize(package),
        }
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
