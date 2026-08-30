"""Controlled source intake.

Treats every input file as untrusted. Computes a content digest, sniffs the
file signature (magic bytes), records extension mismatches, and optionally
stores a content-addressed copy in a quarantine directory.

This module deliberately does NOT:
- parse or render the document;
- execute embedded content;
- claim to malware-scan the file (it only records external scanner state).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

_MAGIC = {
    b"%PDF-": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"II*\x00": "image/tiff",
    b"MM\x00*": "image/tiff",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}

_EXT_FOR_MIME = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tif",
    "image/gif": ".gif",
}

_CHUNK = 1024 * 1024


class IntakeError(Exception):
    """Raised when intake cannot proceed safely."""


@dataclass
class IntakeResult:
    source_path: str
    sha256: str
    byte_size: int
    detected_media_type: Optional[str]
    declared_extension: str
    extension_matches_signature: bool
    quarantine_path: Optional[str] = None
    malware_status: str = "NOT_SCANNED"
    rights_status: str = "UNCONFIRMED_PERMISSION_REQUIRED"
    operational_use: bool = False
    warnings: list = field(default_factory=list)

    def manifest(self) -> Dict[str, object]:
        return {
            "manifest_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "operational_use": self.operational_use,
            "source_path": self.source_path,
            "original_bytes_available": True,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "detected_media_type": self.detected_media_type,
            "declared_extension": self.declared_extension,
            "extension_matches_signature": self.extension_matches_signature,
            "quarantine_path": self.quarantine_path,
            "malware_status": self.malware_status,
            "rights_status": self.rights_status,
            "intake_status": (
                "ACQUIRED_QUARANTINED" if self.quarantine_path else "INSPECTED_ONLY"
            ),
            "warnings": self.warnings,
            "note": (
                "Intake records provenance and integrity only. The file is not "
                "approved for parsing or publication until rights and review "
                "gates are satisfied."
            ),
        }


def detect_media_type(header: bytes) -> Optional[str]:
    for signature, media_type in _MAGIC.items():
        if header.startswith(signature):
            return media_type
    return None


def sha256_and_size(path: Path) -> "tuple[str, int]":
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def intake_file(
    path: str | Path,
    quarantine_dir: Optional[str | Path] = None,
    rights_status: str = "UNCONFIRMED_PERMISSION_REQUIRED",
    malware_status: str = "NOT_SCANNED",
) -> IntakeResult:
    """Inspect and (optionally) quarantine a source file."""
    source = Path(path)
    if not source.is_file():
        raise IntakeError(f"Source file does not exist: {source}")

    with source.open("rb") as handle:
        header = handle.read(16)

    detected = detect_media_type(header)
    declared_ext = source.suffix.lower()
    expected_ext = _EXT_FOR_MIME.get(detected or "")
    # jpeg has two common extensions; treat them as equivalent.
    matches = bool(
        expected_ext
        and (
            declared_ext == expected_ext
            or (detected == "image/jpeg" and declared_ext in (".jpg", ".jpeg"))
            or (detected == "image/tiff" and declared_ext in (".tif", ".tiff"))
        )
    )

    digest, size = sha256_and_size(source)

    result = IntakeResult(
        source_path=str(source),
        sha256=digest,
        byte_size=size,
        detected_media_type=detected,
        declared_extension=declared_ext,
        extension_matches_signature=matches,
        malware_status=malware_status,
        rights_status=rights_status,
    )

    if detected is None:
        result.warnings.append("Unrecognized file signature; media type unknown.")
    elif not matches:
        result.warnings.append(
            f"Declared extension {declared_ext!r} does not match detected type {detected!r}."
        )
    if malware_status == "NOT_SCANNED":
        result.warnings.append("File has not been malware-scanned by an external scanner.")
    if rights_status != "CONFIRMED":
        result.warnings.append("Source rights are not confirmed; do not publish or redistribute.")

    if quarantine_dir is not None:
        result.quarantine_path = _quarantine(source, digest, detected, Path(quarantine_dir))

    return result


def _quarantine(source: Path, digest: str, detected: Optional[str], quarantine_dir: Path) -> str:
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    ext = _EXT_FOR_MIME.get(detected or "", source.suffix.lower() or ".bin")
    target = quarantine_dir / f"{digest}{ext}"

    if target.exists():
        existing_digest, _ = sha256_and_size(target)
        if existing_digest != digest:  # pragma: no cover - hash collision guard
            raise IntakeError(
                f"Content-addressed collision at {target}: refusing to overwrite."
            )
        return str(target)

    # Byte-for-byte copy without shelling out.
    with source.open("rb") as src, target.open("wb") as dst:
        for block in iter(lambda: src.read(_CHUNK), b""):
            dst.write(block)

    verify_digest, _ = sha256_and_size(target)
    if verify_digest != digest:  # pragma: no cover - IO integrity guard
        target.unlink(missing_ok=True)
        raise IntakeError("Quarantine copy failed integrity verification.")
    return str(target)
