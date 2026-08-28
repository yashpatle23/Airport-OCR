"""Airport OCR proof-of-concept package.

Non-operational tooling for turning source-preserving airport-chart observations
into validated, normalized JSON/GeoJSON research projections.

This package must not be used to produce authoritative or operational
aeronautical data. See docs/architecture/POC_DESIGN.md for scope and limits.
"""

__version__ = "0.2.0"

OPERATIONAL_USE = False
"""Hard-coded reminder that outputs are research-only, never navigation data."""

__all__ = ["__version__", "OPERATIONAL_USE"]
