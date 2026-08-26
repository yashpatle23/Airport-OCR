# Phase 1 Extraction Tool Inventory

**Observed:** 2026-08-19  
**Environment:** Linux sandbox, integrations-only network  
**Method:** executable discovery and Python distribution metadata checks

## 1. Available foundation tools

| Capability | Tool/version observed | Benchmark use |
|---|---|---|
| Scripting | Python `3.9.25` | Deterministic schema generation, DMS conversion, validation, GeoJSON export |
| Python environment/package manager | `uv 0.12.1` | Reproducible future dependency environment |
| Java | OpenJDK `25.0.2` | Can run PDFBox if deliberately added later |
| Node.js | `v22.23.2` | Possible review UI/tooling |
| Rust | `1.92.0` | Optional high-performance parser/services |
| Go | `1.25.1` | Optional service tooling |
| File identification | `file 5.39` | MIME/file signature checks after source upload |
| Integrity | GNU `sha256sum 8.32` | Source checksum after source upload |
| HTTP client | `curl 8.17.0` | Source retrieval where permitted; AAI URL currently returns HTTP 403 |
| Archive utilities | `zip` / `unzip` present | Corpus/export packaging |

The executable Python version above is the value observed from `python3 --version` during this benchmark and is the version used by baseline scripts.

## 2. PDF and rendering tools

The following were **not installed** at inventory time:

- Poppler: `pdfinfo`, `pdftotext`, `pdftoppm`, `pdftocairo`;
- MuPDF CLI: `mutool`;
- `qpdf`;
- Ghostscript: `gs`;
- ExifTool;
- Python PDF libraries: PyMuPDF, pypdf, pdfplumber, pdf2image.

### Consequence

Native text, path, font, image, and page-transform extraction cannot be benchmarked in the current base environment. Once the original PDF is lawfully available, create a pinned `uv` project and compare at least two independent parser paths, recommended:

1. PyMuPDF for text spans, paths, rendering, and fast page inspection;
2. pypdf or pdfplumber for an independent text/object baseline;
3. optionally PDFBox for a cross-runtime parser and malformed-PDF comparison.

Do not install a PDF stack before source intake/rights approval merely to imply progress; tool versions must be pinned as part of the benchmark run manifest.

## 3. OCR and image tools

The following were **not installed**:

- Tesseract and language packs;
- OCRmyPDF;
- ImageMagick (`magick`, `convert`, `identify`);
- FFmpeg;
- Python Pillow;
- OpenCV;
- pytesseract;
- EasyOCR;
- PaddleOCR;
- scikit-image;
- NumPy/SciPy;
- Torch/Transformers.

### Consequence

The attached image can be visually assessed in chat, but it cannot be locally OCR-tested because its bytes are not mapped to the workspace and no OCR/image stack exists. This Phase 1 run therefore benchmarks deterministic normalization, not OCR accuracy.

### Recommended OCR benchmark stack after intake

- render PDF pages/regions at 150, 300, 450, and 600 DPI;
- Tesseract as a self-hosted deterministic baseline;
- one layout-aware managed OCR provider only after rights/security approval;
- optional second managed provider for vendor comparison;
- OpenCV preprocessing for deskew, thresholding, line removal, and rotated label crops;
- exact-token scoring for coordinates, runway/taxiway designators, dimensions, and elevations.

## 4. GIS and spatial tools

The following were **not installed**:

- GDAL/OGR (`gdalinfo`, `ogrinfo`, `ogr2ogr`);
- PROJ CLI (`proj`, `cs2cs`);
- GEOS CLI/development helper;
- SpatiaLite;
- PostgreSQL client/PostGIS utilities;
- Python Shapely, pyproj, Rasterio, GeoPandas, and Fiona.

### Consequence

This benchmark can generate standards-compatible JSON/GeoJSON with Python's standard library, but it cannot yet perform PostGIS loading, topology operations, coordinate transformations beyond explicit WGS 84 DMS conversion, or geometric accuracy measurements.

### Recommended spatial stack after intake

- PostgreSQL/PostGIS as canonical benchmark store;
- GDAL/OGR and PROJ for source inspection, raster/geospatial PDF handling, and transforms;
- Shapely/pyproj for local validation scripts;
- explicit CRS84 output for GeoJSON longitude/latitude order;
- separate elevation attributes rather than an unexplained third coordinate.

## 5. Data, schema, and ML support

`jsonschema`, SQLAlchemy, psycopg, MLflow, and common ML libraries were not installed. Python's standard `json`, `decimal`, `unittest`, and `sqlite3` modules are sufficient for the current controlled-value baseline.

A JSON Schema validator should be added in the pinned benchmark environment when dependency installation is authorized. Until then, the local validation script performs explicit structural and domain checks.

## 6. Managed services

No cloud OCR service was invoked. Phase 0 records cloud/managed OCR as not yet authorized because source rights, region, retention, and provider processing terms remain unresolved.

## 7. Tool readiness decision

| Track | Readiness | Decision |
|---|---|---|
| Controlled transcription normalization | Ready | Execute now with Python standard library |
| JSON/GeoJSON research export | Ready | Execute now |
| PDF native text/vector extraction | Blocked | Original PDF plus pinned parser dependencies required |
| OCR comparison | Blocked | Source bytes, OCR stack, and managed-provider authorization required |
| CV taxiway/holding extraction | Blocked | Source bytes, image/CV stack, and annotated labels required |
| Georeferencing/topology/PostGIS | Blocked | Source bytes, GIS stack, and approved positional tolerances required |

## 8. Recommended pinned environment for the full benchmark

A minimal future environment should pin exact versions of:

```text
Python
PyMuPDF
pypdf or pdfplumber
Pillow
opencv-python-headless
pytesseract + Tesseract executable/language data
numpy
shapely
pyproj
rasterio or GDAL bindings
jsonschema
psycopg
PostgreSQL/PostGIS server version
```

Every benchmark result must record OS/container digest, parser/render version, OCR engine/model version, configuration, source checksum, and elapsed/cost measurements.
