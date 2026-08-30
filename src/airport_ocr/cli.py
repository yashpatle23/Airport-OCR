"""Command-line interface for the Airport OCR proof of concept.

Subcommands:
- intake:  inspect (and optionally quarantine) an untrusted source file.
- process: normalize/validate a source-preserving observation document.
- search:  query a generated GeoJSON projection.
- serve:   run the non-operational web application (API + browser UI).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__
from .intake import IntakeError, intake_file
from .pipeline import PipelineError, normalize
from .search import SearchError, search_features


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _cmd_intake(args: argparse.Namespace) -> int:
    try:
        result = intake_file(
            args.file,
            quarantine_dir=args.quarantine_dir,
            rights_status=args.rights_status,
            malware_status=args.malware_status,
        )
        manifest = result.manifest()
        if args.manifest:
            _write_json(Path(args.manifest), manifest)
    except (IntakeError, OSError) as exc:
        print(f"intake error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(manifest, indent=2))
    return 0


def _cmd_process(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    try:
        document = _read_json(input_path)
        normalized, geojson, report = normalize(document)
        out_dir = Path(args.output_dir)
        _write_json(out_dir / "normalized.json", normalized)
        _write_json(out_dir / "features.geojson", geojson)
        _write_json(out_dir / "validation-report.json", report)
    except (OSError, PipelineError, ValueError, TypeError, KeyError) as exc:
        print(f"process error: {exc}", file=sys.stderr)
        return 2

    extraction = normalized.get("extraction") or {}
    summary = {
        "status": report["status"],
        "extraction_status": extraction.get("status"),
        "extraction_issue_codes": [
            issue.get("code") for issue in extraction.get("issues", [])
        ],
        "counts": report["counts"],
        "failure_count": report["failure_count"],
        "outputs": [
            str(out_dir / "normalized.json"),
            str(out_dir / "features.geojson"),
            str(out_dir / "validation-report.json"),
        ],
    }
    print(json.dumps(summary, indent=2))

    if report["failure_count"] > 0:
        return 1
    if args.fail_on_blockers and report["blocker_count"] > 0:
        return 3
    return 0


def _cmd_extract_pdf_words(args: argparse.Namespace) -> int:
    from .pdf_words import extract_from_words

    input_path = Path(args.input)
    try:
        dump = _read_json(input_path)
        metadata = _read_json(Path(args.metadata)) if args.metadata else None
        external_claims = None
        if args.external_elevation_claim_ft is not None:
            external_claims = [
                {
                    "claim_id": "claim:elev:cli-external",
                    "source_id": "CLI-DECLARED-EXTERNAL-CLAIM",
                    "source_text": f"{args.external_elevation_claim_ft} FT",
                    "value": args.external_elevation_claim_ft,
                    "unit": "FT",
                    "vertical_datum": None,
                    "effective_alignment": "USER_SUPPLIED_UNVERIFIED",
                }
            ]
        document = extract_from_words(
            dump,
            dataset_id=args.dataset_id,
            source_metadata=metadata,
            airport_name=args.airport_name,
            external_elevation_claims=external_claims,
            profile=args.profile,
        )
        if args.output:
            _write_json(Path(args.output), document)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"extract-pdf-words error: {exc}", file=sys.stderr)
        return 2

    summary = {
        "dataset_id": document["dataset_id"],
        "airport_icao": document["airport_icao"],
        "extraction_status": document.get("extraction", {}).get("status"),
        "runway_pairs": [r["designator_pair"] for r in document["runways"]],
        "taxiway_count": len(document["taxiways"]["features"]),
        "runway_holding_positions": document["runway_holding_positions"]["completeness_status"],
        "output": args.output,
    }
    print(json.dumps(summary, indent=2))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from .pipeline import normalize as _normalize
    from .webapp import serve

    input_path = Path(args.input)
    try:
        document = _read_json(input_path)
        # Fail fast with a clear message if the dataset cannot be normalized.
        _normalize(document)
    except (OSError, PipelineError, KeyError, ValueError, TypeError) as exc:
        print(f"serve error: {exc}", file=sys.stderr)
        return 2

    serve(document, host=args.host, port=args.port)
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    bbox: Optional[List[float]] = None
    if args.bbox is not None:
        try:
            bbox = [float(value) for value in args.bbox.split(",")]
        except ValueError:
            print("search error: bbox must be comma-separated numbers", file=sys.stderr)
            return 2
    try:
        collection = _read_json(Path(args.geojson))
        result = search_features(
            collection,
            feature_type=args.feature_type,
            airport_icao=args.airport,
            designator=args.designator,
            bbox=bbox,
        )
    except (OSError, ValueError, TypeError, KeyError, SearchError) as exc:
        print(f"search error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="airport-ocr",
        description="Non-operational airport-chart observation normalization and search.",
    )
    parser.add_argument("--version", action="version", version=f"airport-ocr {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    intake_parser = sub.add_parser("intake", help="Inspect/quarantine an untrusted source file.")
    intake_parser.add_argument("file", help="Path to the source PDF or image.")
    intake_parser.add_argument("--quarantine-dir", default=None, help="Directory for a content-addressed copy.")
    intake_parser.add_argument("--rights-status", default="UNCONFIRMED_PERMISSION_REQUIRED")
    intake_parser.add_argument("--malware-status", default="NOT_SCANNED")
    intake_parser.add_argument("--manifest", default=None, help="Optional path to write the intake manifest JSON.")
    intake_parser.set_defaults(func=_cmd_intake)

    process_parser = sub.add_parser("process", help="Normalize and validate an observation document.")
    process_parser.add_argument("input", help="Path to a source-preserving observation JSON file.")
    process_parser.add_argument("--output-dir", default="out", help="Directory for outputs.")
    process_parser.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help="Exit non-zero when expected blockers remain (for strict pipelines).",
    )
    process_parser.set_defaults(func=_cmd_process)

    search_parser = sub.add_parser("search", help="Query a generated GeoJSON projection.")
    search_parser.add_argument("geojson", help="Path to a features.geojson file.")
    search_parser.add_argument("--feature-type", default=None)
    search_parser.add_argument("--airport", default=None)
    search_parser.add_argument("--designator", default=None)
    search_parser.add_argument("--bbox", default=None, help="min_lon,min_lat,max_lon,max_lat")
    search_parser.set_defaults(func=_cmd_search)

    extract_parser = sub.add_parser(
        "extract-pdf-words", help="Extract observations from a PyMuPDF words dump (native text)."
    )
    extract_parser.add_argument("input", help="Path to a PyMuPDF words dump JSON file.")
    extract_parser.add_argument("--output", default=None, help="Optional path to write the observation JSON.")
    extract_parser.add_argument("--dataset-id", default=None, help="Dataset identifier (default: derived from ICAO).")
    extract_parser.add_argument(
        "--metadata",
        default=None,
        help="Optional intake/source metadata JSON (path, SHA-256, rights state, etc.).",
    )
    extract_parser.add_argument("--airport-name", default=None, help="Reviewed fallback when the title is not extractable.")
    extract_parser.add_argument(
        "--profile",
        choices=("auto", "vobl-sample"),
        default="auto",
        help="Layout/profile mode; uploads should use auto.",
    )
    extract_parser.add_argument(
        "--external-elevation-claim-ft",
        type=int,
        default=None,
        help="Optional unverified external claim; never inferred from the chart.",
    )
    extract_parser.set_defaults(func=_cmd_extract_pdf_words)

    serve_parser = sub.add_parser("serve", help="Run the non-operational web app (API + UI).")
    serve_parser.add_argument("input", help="Path to a source-preserving observation JSON file.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1).")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000).")
    serve_parser.set_defaults(func=_cmd_serve)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
