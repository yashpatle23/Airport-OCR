"""Command-line interface for the Airport OCR proof of concept.

Subcommands:
- intake:  inspect (and optionally quarantine) an untrusted source file.
- process: normalize/validate a source-preserving observation document.
- search:  query a generated GeoJSON projection.
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
    except IntakeError as exc:
        print(f"intake error: {exc}", file=sys.stderr)
        return 2

    manifest = result.manifest()
    if args.manifest:
        _write_json(Path(args.manifest), manifest)
    print(json.dumps(manifest, indent=2))
    return 0


def _cmd_process(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    try:
        document = _read_json(input_path)
        normalized, geojson, report = normalize(document)
    except (PipelineError, KeyError) as exc:
        print(f"process error: {exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir)
    _write_json(out_dir / "normalized.json", normalized)
    _write_json(out_dir / "features.geojson", geojson)
    _write_json(out_dir / "validation-report.json", report)

    summary = {
        "status": report["status"],
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
    except SearchError as exc:
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

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
