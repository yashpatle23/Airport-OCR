import json
from pathlib import Path

from airport_ocr.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "vobl-bootstrap-observations.json"
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def test_cli_process_writes_outputs(tmp_path, capsys):
    out = tmp_path / "out"
    code = main(["process", str(EXAMPLE), "--output-dir", str(out)])
    assert code == 0

    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "PASS_WITH_EXPECTED_BLOCKERS"
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
