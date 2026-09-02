"""Local Uvicorn launcher for the Airport-OCR FastAPI application."""

from __future__ import annotations

import argparse
from typing import List, Optional


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="airport-ocr-api",
        description="Run the local non-operational Airport-OCR FastAPI service.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Development reload mode.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    import uvicorn

    uvicorn.run(
        "airport_ocr.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=1,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
