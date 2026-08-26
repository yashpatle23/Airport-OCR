import hashlib

import pytest

from airport_ocr.intake import IntakeError, detect_media_type, intake_file

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def test_detect_media_type_pdf():
    assert detect_media_type(b"%PDF-1.7 ...") == "application/pdf"
    assert detect_media_type(b"\x89PNG\r\n\x1a\n") == "image/png"
    assert detect_media_type(b"random") is None


def test_intake_computes_digest_and_manifest(tmp_path):
    pdf = tmp_path / "chart.pdf"
    pdf.write_bytes(MINIMAL_PDF)

    result = intake_file(pdf)
    manifest = result.manifest()

    assert result.detected_media_type == "application/pdf"
    assert result.extension_matches_signature is True
    assert result.sha256 == hashlib.sha256(MINIMAL_PDF).hexdigest()
    assert result.byte_size == len(MINIMAL_PDF)
    assert manifest["operational_use"] is False
    assert manifest["intake_status"] == "INSPECTED_ONLY"
    assert manifest["malware_status"] == "NOT_SCANNED"
    # Intake must never claim to have scanned the file.
    assert any("malware-scanned" in w for w in result.warnings)


def test_intake_flags_extension_mismatch(tmp_path):
    disguised = tmp_path / "chart.png"
    disguised.write_bytes(MINIMAL_PDF)

    result = intake_file(disguised)
    assert result.detected_media_type == "application/pdf"
    assert result.extension_matches_signature is False
    assert any("does not match" in w for w in result.warnings)


def test_intake_quarantine_is_content_addressed(tmp_path):
    pdf = tmp_path / "chart.pdf"
    pdf.write_bytes(MINIMAL_PDF)
    quarantine = tmp_path / "q"

    result = intake_file(pdf, quarantine_dir=quarantine)
    digest = hashlib.sha256(MINIMAL_PDF).hexdigest()
    expected = quarantine / f"{digest}.pdf"

    assert result.quarantine_path == str(expected)
    assert expected.read_bytes() == MINIMAL_PDF
    assert result.manifest()["intake_status"] == "ACQUIRED_QUARANTINED"

    # Re-running is idempotent: identical bytes reuse the same target.
    again = intake_file(pdf, quarantine_dir=quarantine)
    assert again.quarantine_path == str(expected)


def test_intake_missing_file_raises(tmp_path):
    with pytest.raises(IntakeError):
        intake_file(tmp_path / "nope.pdf")
