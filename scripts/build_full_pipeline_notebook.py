#!/usr/bin/env python3
"""Generate notebooks/Airport_OCR_Full_Pipeline.ipynb deterministically.

Uses only the standard library so notebook generation does not change the
package's zero-runtime-dependency policy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "Airport_OCR_Full_Pipeline.ipynb"


def markdown(cell_id: str, source: str) -> Dict[str, Any]:
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code(cell_id: str, source: str) -> Dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def build() -> Dict[str, Any]:
    cells: List[Dict[str, Any]] = [
        markdown(
            "title",
            """# Airport-OCR — upload-first full aerodrome-chart pipeline

**PDF → Extract → Identify → Structure → Search**

Upload a permitted native-text aerodrome-chart PDF (VOBL, VOMM, or another
supported AAI/ICAO-style layout), or explicitly choose the VOBL sample URL.
The notebook extracts only:

1. airport identity;
2. runways;
3. taxiways;
4. runway holding positions (review-only candidates);
5. airport coordinates/elevation.

> **Non-operational / research-only.** Outputs are provisional, not authoritative
> aeronautical data, and must not be used for navigation. Uploading a file does
> not grant source rights. Scanned/textless or unknown layouts stop or remain
> explicitly partial; the pipeline never substitutes VOBL facts.
""",
        ),
        markdown("install-title", "## 0 — Install the deterministic core + optional notebook adapters\n"),
        code(
            "install",
            """%pip -q install pymupdf matplotlib google-generativeai
%pip -q install --force-reinstall "git+https://github.com/yashpatle23/Airport-OCR.git@4f180eca52dcbe1d35314b68e8c31ee14bf35056"

import airport_ocr
print('airport_ocr', airport_ocr.__version__, '| operational_use =', airport_ocr.OPERATIONAL_USE)
""",
        ),
        markdown(
            "source-title",
            """## Step 1 — Select and upload the source PDF

**Upload PDF is the default.** Colab will show a browser upload button. Exactly
one PDF is accepted and its original filename is preserved. The optional VOBL
URL is only a regression/demo source.
""",
        ),
        code(
            "source",
            """#@title Source selection
SOURCE_MODE = "Upload PDF" #@param ["Upload PDF", "Use optional VOBL sample URL"]
I_HAVE_PERMISSION_TO_PROCESS = False #@param {type:"boolean"}
VOBL_SAMPLE_URL = "https://aim-india.aai.aero/eaip/eaip-v2-01-2026/eAIP/VOBL-ADC.pdf" #@param {type:"string"}

from pathlib import Path
import urllib.request

if not I_HAVE_PERMISSION_TO_PROCESS:
    raise RuntimeError('Tick I_HAVE_PERMISSION_TO_PROCESS before continuing.')

if SOURCE_MODE == 'Upload PDF':
    from google.colab import files
    uploaded = files.upload()  # <-- browser upload button
    pdf_names = [name for name in uploaded if name.lower().endswith('.pdf')]
    if len(uploaded) != 1 or len(pdf_names) != 1:
        raise RuntimeError('Upload exactly one .pdf file.')
    SRC = pdf_names[0]
else:
    SRC = 'VOBL-ADC.pdf'
    try:
        request = urllib.request.Request(VOBL_SAMPLE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
        Path(SRC).write_bytes(payload)
    except Exception as exc:
        raise RuntimeError(
            'VOBL sample download failed. Set SOURCE_MODE to Upload PDF and upload your chart.'
        ) from exc

if not Path(SRC).read_bytes()[:5] == b'%PDF-':
    raise RuntimeError('Selected file does not have a PDF signature.')
print('Source:', SRC, '| bytes:', Path(SRC).stat().st_size)
""",
        ),
        markdown("intake-title", "## Step 1b — Controlled intake, provenance, and run identity\n"),
        code(
            "intake",
            """from airport_ocr.intake import intake_file
import json, re

intake = intake_file(SRC).manifest()
stem = re.sub(r'[^A-Za-z0-9._-]+', '-', Path(SRC).stem).strip('-_.').lower() or 'airport-chart'
RUN_ID = f"{stem}-{intake['sha256'][:8]}"

def artifact(suffix):
    return f'{RUN_ID}-{suffix}'

INTAKE_PATH = artifact('intake.json')
Path(INTAKE_PATH).write_text(json.dumps(intake, indent=2) + '\\n', encoding='utf-8')
print('Run ID :', RUN_ID)
print('SHA-256:', intake['sha256'])
print('Rights :', intake['rights_status'])
""",
        ),
        markdown(
            "extract-title",
            """## Step 2 — Native-text extraction and capability gate

The page-aware extractor derives facts from this PDF. It does not OCR. A
textless/scanned PDF stops with `UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED`; an
unsupported optional layout stays visibly partial.
""",
        ),
        code(
            "extract",
            """import pymupdf
from airport_ocr.pdf_words import ExtractionError, extract_from_words

doc = pymupdf.open(SRC)
pages = [
    {'page': index, 'size': [page.rect.width, page.rect.height], 'words': page.get_text('words')}
    for index, page in enumerate(doc)
]
native_word_count = sum(len(page['words']) for page in pages)
if native_word_count == 0:
    raise RuntimeError('UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED: this PDF has no native text.')

WORDS_PATH = artifact('words.json')
Path(WORDS_PATH).write_text(json.dumps(pages, ensure_ascii=False) + '\\n', encoding='utf-8')
source_metadata = {
    'source_path': SRC,
    'source_url': VOBL_SAMPLE_URL if SOURCE_MODE == 'Use optional VOBL sample URL' else None,
    'sha256': intake['sha256'],
    'original_bytes_available': True,
    'rights_status': intake['rights_status'],
    'publisher_context': ['AIP India', 'AAI'] if SOURCE_MODE == 'Use optional VOBL sample URL' else [],
}
profile = 'vobl-sample' if SOURCE_MODE == 'Use optional VOBL sample URL' else 'auto'
observations = extract_from_words(
    pages,
    dataset_id=RUN_ID,
    source_metadata=source_metadata,
    profile=profile,
)
OBSERVATIONS_PATH = artifact('observations.json')
Path(OBSERVATIONS_PATH).write_text(
    json.dumps(observations, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8'
)
print('ICAO       :', observations['airport_icao'])
print('airport    :', observations['airport']['name']['value'])
print('runways    :', [r['designator_pair'] for r in observations['runways']])
print('taxiways   :', len(observations['taxiways']['features']), observations['taxiways']['completeness_status'])
print('extraction :', observations['extraction']['status'])
for issue in observations['extraction']['issues']:
    print('  -', issue['code'], ':', issue['detail'])
""",
        ),
        markdown(
            "holding-title",
            """### Step 2b — Holding-position candidates (all pages, review-only)

Black-linework clusters are deliberately kept outside the accepted feature set.
False positives are expected. Every result is `NEEDS_REVIEW`.
""",
        ),
        code(
            "holding",
            """from airport_ocr.holding import holding_candidates

def hexc(value):
    return None if not value else '#%02x%02x%02x' % tuple(int(round(v * 255)) for v in value[:3])

known = {feature['designator'] for feature in observations['taxiways']['features']}
holding_features, detector_pages = [], []
for page_number, page in enumerate(doc):
    segments = []
    for drawing in page.get_drawings():
        if hexc(drawing.get('color')) != '#000000' and hexc(drawing.get('fill')) != '#000000':
            continue
        for item in drawing['items']:
            if item[0] == 'l':
                first, second = item[1], item[2]
                segments.append((first.x, first.y, second.x, second.y))
            elif item[0] == 're':
                rect = item[1]
                segments += [
                    (rect.x0, rect.y0, rect.x1, rect.y0), (rect.x1, rect.y0, rect.x1, rect.y1),
                    (rect.x1, rect.y1, rect.x0, rect.y1), (rect.x0, rect.y1, rect.x0, rect.y0),
                ]
    labels = []
    for word in page.get_text('words'):
        token = word[4].strip().strip('.,&\"“”')
        if token in known:
            labels.append({'designator': token, 'x': (word[0] + word[2]) / 2, 'y': (word[1] + word[3]) / 2})
    result = holding_candidates(
        segments,
        labels,
        airport_icao=observations['airport_icao'],
        page_number=page_number,
        page_size=[page.rect.width, page.rect.height],
        cell=14.0,
        min_segments=6,
        max_label_distance=80.0,
    )
    holding_features.extend(result['features'])
    detector_pages.append(result['detector'])

holding = {
    'feature_type': 'runway_holding_position_collection',
    'features': holding_features,
    'presence_observed': True,
    'empty_array_semantics': 'CANDIDATES_NOT_ACCEPTED',
    'completeness_status': 'CANDIDATES_PENDING_REVIEW',
    'operational_use': False,
    'detector': {'method': 'per-page black-linework clustering', 'pages': detector_pages},
    'review_required': True,
    'warning': 'UNVERIFIED candidates; false positives expected; never use operationally.',
}
HOLDING_PATH = artifact('holding-candidates.json')
Path(HOLDING_PATH).write_text(json.dumps(holding, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')
print('Holding candidates:', len(holding_features), '(all NEEDS_REVIEW)')
""",
        ),
        markdown("structure-title", "## Step 3 — Identify, validate, and structure\n"),
        code(
            "structure",
            """from airport_ocr.pipeline import normalize
from airport_ocr.report import build_package

normalized, geojson, validation = normalize(observations)
package = build_package(normalized, validation, holding_candidates=holding)

NORMALIZED_PATH = artifact('normalized.json')
GEOJSON_PATH = artifact('features.geojson')
VALIDATION_PATH = artifact('validation.json')
PACKAGE_PATH = artifact('package.json')
for path, value in [
    (NORMALIZED_PATH, normalized), (GEOJSON_PATH, geojson),
    (VALIDATION_PATH, validation), (PACKAGE_PATH, package),
]:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')

print('VALIDATION:', validation['status'], '| failures:', validation['failure_count'])
print('counts    :', validation['counts'])
print('five groups:', package['airport']['icao'], len(package['runways']), package['taxiways']['count'],
      package['runway_holding_positions']['candidate_count'],
      package['airport']['coordinates_elevation']['arp']['coordinates_lonlat'])
""",
        ),
        markdown("search-title", "## Step 3b — Search (dynamic examples from this airport)\n"),
        code(
            "search",
            """from airport_ocr.search import search_features

first_designator = package['runways'][0]['directions'][0]['designator']
points = [feature['geometry']['coordinates'] for feature in geojson['features'] if feature['geometry']['type'] == 'Point']
lons, lats = [p[0] for p in points], [p[1] for p in points]
pad_lon = (max(lons) - min(lons)) * 0.1 or 0.01
pad_lat = (max(lats) - min(lats)) * 0.1 or 0.01
bbox = [min(lons) - pad_lon, min(lats) - pad_lat, max(lons) + pad_lon, max(lats) + pad_lat]
print('thresholds       :', search_features(geojson, feature_type='runway_threshold')['properties']['match_count'])
print(first_designator, 'matches:', search_features(geojson, designator=first_designator)['properties']['match_count'])
print('dynamic bbox     :', search_features(geojson, bbox=bbox)['properties']['match_count'], 'features')
""",
        ),
        markdown("report-title", "## Summary + polished self-contained report (Gemini optional)\n"),
        code(
            "report",
            """from airport_ocr.report import ai_summary_prompt, render_html, summarize
from IPython.display import HTML, Markdown, display

summary_md = summarize(package)
SUMMARY_PATH = artifact('summary.md')
Path(SUMMARY_PATH).write_text(summary_md, encoding='utf-8')
display(Markdown(summary_md))

ai_text = None
try:
    from google.colab import userdata
    gemini_api_key = userdata.get('GEMINI_API_KEY')
except Exception:
    gemini_api_key = None

AI_SUMMARY_PATH = None
if gemini_api_key:
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_api_key)
        prompt = ai_summary_prompt(package)
        model = genai.GenerativeModel('models/gemini-flash-latest', system_instruction=prompt['system'])
        ai_text = model.generate_content(prompt['user'], generation_config={'temperature': 0}).text
        AI_SUMMARY_PATH = artifact('summary-ai.md')
        Path(AI_SUMMARY_PATH).write_text(ai_text, encoding='utf-8')
        print('✓ Gemini paraphrase generated.')
    except Exception as exc:
        print('AI skipped; deterministic report retained:', exc)
else:
    print('No GEMINI_API_KEY; deterministic report retained.')

html = render_html(package, ai_text=ai_text)
REPORT_PATH = artifact('report.html')
Path(REPORT_PATH).write_text(html, encoding='utf-8')
display(HTML(html))
""",
        ),
        markdown("map-title", "## Provisional feature map (threshold connectors are not runway extents)\n"),
        code(
            "map",
            """import matplotlib.pyplot as plt

plt.figure(figsize=(9, 5))
for feature in geojson['features']:
    geometry, properties = feature['geometry'], feature['properties']
    if geometry['type'] == 'Point':
        lon, lat = geometry['coordinates']
        is_arp = properties['feature_type'] == 'aerodrome_reference_point'
        plt.scatter([lon], [lat], s=80 if is_arp else 35,
                    c='tab:blue' if is_arp else 'tab:green', zorder=3)
        plt.annotate('ARP' if is_arp else properties.get('designator', ''), (lon, lat),
                     textcoords='offset points', xytext=(5, 5), fontsize=9)
    elif geometry['type'] == 'LineString':
        plt.plot([p[0] for p in geometry['coordinates']], [p[1] for p in geometry['coordinates']],
                 '--', color='gray', zorder=1)
plt.xlabel('longitude'); plt.ylabel('latitude')
plt.title(f"{package['airport']['icao']} ARP + runway thresholds — provisional, non-operational")
plt.grid(True, alpha=0.3); plt.gca().set_aspect('equal', adjustable='datalim'); plt.show()
""",
        ),
        markdown("download-title", "## Download every artifact as one ZIP\n"),
        code(
            "download",
            """from zipfile import ZIP_DEFLATED, ZipFile
from google.colab import files

artifact_paths = [
    INTAKE_PATH, WORDS_PATH, OBSERVATIONS_PATH, HOLDING_PATH, NORMALIZED_PATH,
    GEOJSON_PATH, VALIDATION_PATH, PACKAGE_PATH, SUMMARY_PATH, REPORT_PATH,
]
if AI_SUMMARY_PATH:
    artifact_paths.append(AI_SUMMARY_PATH)
run_manifest = {
    'run_id': RUN_ID,
    'source_filename': SRC,
    'sha256': intake['sha256'],
    'airport_icao': package['airport']['icao'],
    'operational_use': False,
    'artifacts': artifact_paths,
}
MANIFEST_PATH = artifact('manifest.json')
Path(MANIFEST_PATH).write_text(json.dumps(run_manifest, indent=2) + '\\n', encoding='utf-8')
artifact_paths.append(MANIFEST_PATH)
ZIP_PATH = artifact('airport-ocr-results.zip')
with ZipFile(ZIP_PATH, 'w', ZIP_DEFLATED) as bundle:
    for path in artifact_paths:
        bundle.write(path, arcname=Path(path).name)
print('Bundle:', ZIP_PATH, '| files:', len(artifact_paths))
files.download(ZIP_PATH)
""",
        ),
        markdown(
            "limits",
            """## Supported-input boundary

- Native-text AAI/ICAO-style aerodrome charts are supported through deterministic
  layout adapters; unknown optional layouts remain partial.
- Scanned PDFs need a future OCR adapter and stop before misleading output.
- Explicit `TWY X` references are taxiway candidates, not necessarily a complete
  inventory; bare map letters are not guessed.
- Holding clusters are unverified review candidates, not accepted positions.
- Declared distances are never substituted for physical runway dimensions.
- Every artifact remains non-operational and not for navigation.
""",
        ),
    ]
    return {
        "cells": cells,
        "metadata": {
            "colab": {"name": "Airport_OCR_Full_Pipeline.ipynb", "provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.x"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
