import json
from pathlib import Path

from airport_ocr.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "vobl-bootstrap-observations.json"
VOMM_WORDS = Path(__file__).resolve().parents[1] / "examples" / "vomm-synthetic-words.json"
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def test_cli_process_writes_outputs(tmp_path, capsys):
    out = tmp_path / "out"
    code = main(["process", str(EXAMPLE), "--output-dir", str(out)])
    assert code == 0

    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "PASS_WITH_EXPECTED_BLOCKERS"
    assert summary["extraction_status"] == "NOT_REPORTED_LEGACY_OBSERVATION"
    assert summary["extraction_issue_codes"] == ["EXTRACTION_DIAGNOSTICS_NOT_REPORTED"]
    assert (out / "normalized.json").is_file()
    assert (out / "features.geojson").is_file()
    assert (out / "validation-report.json").is_file()


def test_cli_process_fail_on_blockers_exit_code(tmp_path):
    out = tmp_path / "out"
    code = main(["process", str(EXAMPLE), "--output-dir", str(out), "--fail-on-blockers"])
    assert code == 3


def test_cli_intake_and_search(tmp_path, capsys):
    pdf = tmp_path / "chart.pdf"
    pdf.write_bytes(MINIMAL_PDF)
    manifest_path = tmp_path / "manifest.json"

    code = main(["intake", str(pdf), "--manifest", str(manifest_path)])
    assert code == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["detected_media_type"] == "application/pdf"
    assert manifest_path.is_file()

    out = tmp_path / "out"
    assert main(["process", str(EXAMPLE), "--output-dir", str(out)]) == 0
    capsys.readouterr()  # drain

    code = main(["search", str(out / "features.geojson"), "--feature-type", "runway_threshold"])
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["properties"]["match_count"] == 4



def test_cli_extract_pdf_words_auto_is_multi_airport(tmp_path, capsys):
    output = tmp_path / "vomm-observations.json"
    code = main([
        "extract-pdf-words",
        str(VOMM_WORDS),
        "--profile",
        "auto",
        "--output",
        str(output),
    ])
    assert code == 0
    summary = json.loads(capsys.readouterr().out)
    document = json.loads(output.read_text(encoding="utf-8"))
    assert summary["airport_icao"] == "VOMM"
    assert summary["runway_pairs"] == ["07/25", "12/30"]
    assert document["extraction"]["status"] == "PARTIAL"
    assert "Bengaluru" not in output.read_text(encoding="utf-8")

    process_out = tmp_path / "vomm-processed"
    assert main(["process", str(output), "--output-dir", str(process_out)]) == 0
    process_summary = json.loads(capsys.readouterr().out)
    assert process_summary["extraction_status"] == "PARTIAL"
    assert set(process_summary["extraction_issue_codes"]) == {
        "TDZ_ELEVATIONS_NOT_EXTRACTED",
        "TAXIWAY_INVENTORY_PARTIAL",
        "RUNWAY_HOLDING_POSITIONS_NOT_EXTRACTED",
    }



def test_cli_process_non_numeric_dimensions_is_controlled(tmp_path, capsys):
    document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    document["runways"][0]["length"]["value"] = "4000"
    source = tmp_path / "invalid-dimensions.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    out = tmp_path / "out"

    code = main(["process", str(source), "--output-dir", str(out)])
    assert code == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "FAIL"
    report = json.loads((out / "validation-report.json").read_text(encoding="utf-8"))
    assert any(
        check["id"] == "runway.09L-27R.dimensions" and check["status"] == "FAIL"
        for check in report["checks"]
    )


def test_cli_missing_metadata_file_is_controlled(tmp_path, capsys):
    missing = tmp_path / "missing-metadata.json"
    code = main([
        "extract-pdf-words",
        str(VOMM_WORDS),
        "--metadata",
        str(missing),
    ])
    captured = capsys.readouterr()
    assert code == 2
    assert "extract-pdf-words error:" in captured.err
    assert str(missing) in captured.err
