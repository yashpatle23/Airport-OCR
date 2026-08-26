#!/usr/bin/env python3
"""Airport-OCR end-to-end demo (safe for a live walkthrough).

Runs the whole flow and narrates each step:

    PDF/words -> Extract -> Identify -> Structure -> Search -> Summary

By default it uses the bundled real word-sample (examples/vobl-words-sample.json)
so it needs no PDF and no internet — it cannot fail live. Pass ``--pdf PATH`` to
run against a real chart (requires PyMuPDF) including the review-only
runway-holding-position candidate detector.

Usage:
    python scripts/demo.py
    python scripts/demo.py --pdf VOBL-ADC.pdf
    PYTHONPATH=src python scripts/demo.py     # if the package isn't installed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from a source checkout without installing the package.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from airport_ocr import __version__  # noqa: E402
from airport_ocr.holding import holding_candidates  # noqa: E402
from airport_ocr.pdf_words import extract_from_words  # noqa: E402
from airport_ocr.pipeline import normalize  # noqa: E402
from airport_ocr.report import build_package, summarize  # noqa: E402
from airport_ocr.search import search_features  # noqa: E402

SAMPLE = _ROOT / "examples" / "vobl-words-sample.json"


def rule(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def words_from_pdf(pdf_path: str):
    import pymupdf  # noqa: WPS433

    doc = pymupdf.open(pdf_path)
    pages = [
        {"page": i, "size": [p.rect.width, p.rect.height], "words": p.get_text("words")}
        for i, p in enumerate(doc)
    ]
    return pages, doc


def holding_from_pdf(doc, taxiway_designators):
    page0 = doc[0]

    def hexc(c):
        return None if not c else "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in c[:3])

    segs = []
    for d in page0.get_drawings():
        if hexc(d.get("color")) != "#000000" and hexc(d.get("fill")) != "#000000":
            continue
        for it in d["items"]:
            if it[0] == "l":
                p1, p2 = it[1], it[2]
                segs.append((p1.x, p1.y, p2.x, p2.y))
            elif it[0] == "re":
                r = it[1]
                segs += [
                    (r.x0, r.y0, r.x1, r.y0), (r.x1, r.y0, r.x1, r.y1),
                    (r.x1, r.y1, r.x0, r.y1), (r.x0, r.y1, r.x0, r.y0),
                ]
    labels = []
    known = set(taxiway_designators)
    for w in page0.get_text("words"):
        tok = w[4].strip().strip(".,&")
        if tok in known:
            labels.append({"designator": tok, "x": (w[0] + w[2]) / 2, "y": (w[1] + w[3]) / 2})
    return holding_candidates(
        segs, labels, page_size=[page0.rect.width, page0.rect.height],
        cell=14.0, min_segments=6, max_label_distance=80.0,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Airport-OCR end-to-end demo")
    parser.add_argument("--pdf", default=None, help="Optional real chart PDF (needs PyMuPDF).")
    parser.add_argument("--out", default="demo_out", help="Directory for demo artifacts.")
    args = parser.parse_args()

    rule("Airport-OCR demo  |  PDF -> Extract -> Identify -> Structure -> Search")
    print(f"package version : airport_ocr {__version__}")
    print("classification  : NON-OPERATIONAL / research only (not for navigation)")

    doc = None
    holding = None

    # ---- Extract ------------------------------------------------------------
    rule("STEP 1-2  EXTRACT  (airport, runways, taxiways, coordinates/elevation)")
    if args.pdf:
        print(f"source          : native text from {args.pdf}")
        pages, doc = words_from_pdf(args.pdf)
        print(f"pages           : {len(pages)}  | words on page 0: {len(pages[0]['words'])}")
        observations = extract_from_words(pages, dataset_id="vobl-demo-pdf")
    else:
        print(f"source          : bundled real word-sample ({SAMPLE.name})")
        observations = extract_from_words(json.loads(SAMPLE.read_text()), dataset_id="vobl-demo-sample")

    print(f"airport (ICAO)  : {observations['airport_icao']}")
    print(f"runway pairs    : {[r['designator_pair'] for r in observations['runways']]}")
    print(f"taxiways        : {len(observations['taxiways']['features'])} extracted from the legend")
    print(f"holding (text)  : {observations['runway_holding_positions']['completeness_status']}")

    # ---- Identify + validate ------------------------------------------------
    rule("STEP 2    IDENTIFY + VALIDATE  (deterministic checks, DMS -> CRS84)")
    normalized, geojson, report = normalize(observations)
    print(f"validation      : {report['status']}  | failures: {report['failure_count']}")
    print(f"check counts    : {report['counts']}")
    print("sample checks   :")
    for c in report["checks"][:6]:
        print(f"   [{c['status']}] {c['id']}")
    print("   ...")

    # ---- Holding-position candidates (only with a real PDF) -----------------
    rule("STEP 2    RUNWAY HOLDING POSITIONS  (review-only candidates)")
    if doc is not None:
        holding = holding_from_pdf(doc, [f["designator"] for f in observations["taxiways"]["features"]])
        det = holding["detector"]
        print(f"black segments  : {det['input_segment_count']}")
        print(f"marking-sized   : {det['marking_segment_count']}")
        print(f"CANDIDATES      : {det['candidate_count']}  (status NEEDS_REVIEW, false positives expected)")
    else:
        print("skipped         : needs the real PDF vector layer (run with --pdf VOBL-ADC.pdf)")
        print("detector        : airport_ocr.holding  (clusters black marking strokes -> candidates)")

    # ---- Structure ----------------------------------------------------------
    rule("STEP 3    STRUCTURE  (one machine-readable package + GeoJSON)")
    package = build_package(normalized, report, holding_candidates=holding)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "vobl_package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2))
    (out / "vobl_features.geojson").write_text(json.dumps(geojson, ensure_ascii=False, indent=2))
    ce = package["airport"]["coordinates_elevation"]
    print(f"airport         : {package['airport']['icao']} - {package['airport']['name']}")
    print(f"ARP (lon,lat)   : {ce['arp']['coordinates_lonlat']}  ({ce['arp']['crs']})")
    print(f"elevation       : {[ (c['value'], c['unit']) for c in ce['elevation']['claims'] ]} "
          f"-> {ce['elevation']['conflict_status']} (selected: {ce['elevation']['selected_value']})")
    print(f"runways         : {[r['designator_pair'] for r in package['runways']]}")
    print(f"taxiways        : {package['taxiways']['count']}")
    print(f"holding cand.   : {package['runway_holding_positions']['candidate_count']} (review-only)")
    print(f"written         : {out / 'vobl_package.json'} , {out / 'vobl_features.geojson'}")

    # ---- Search -------------------------------------------------------------
    rule("STEP 3    SEARCH  (query the GeoJSON projection)")
    print("feature_type=runway_threshold ->",
          search_features(geojson, feature_type="runway_threshold")["properties"]["match_count"], "matches")
    print("designator=09L                ->",
          search_features(geojson, designator="09L")["properties"]["match_count"], "match")
    bbox = [77.60, 13.10, 77.80, 13.30]
    print(f"bbox={bbox} ->",
          search_features(geojson, bbox=bbox)["properties"]["match_count"], "features")

    # ---- Summary ------------------------------------------------------------
    rule("STEP 3    SUMMARY  (deterministic; optional AI paraphrase in Colab)")
    summary = summarize(package)
    (out / "vobl_summary.md").write_text(summary)
    print(summary)

    rule("DONE  |  outputs in ./" + str(out))
    print("Non-operational research artifact. Holding positions are unverified "
          "candidates. Source rights + reviewer required before any authoritative use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
