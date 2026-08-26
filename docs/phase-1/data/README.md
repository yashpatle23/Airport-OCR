# VOBL Phase 1 Bootstrap Dataset

This directory contains a **provisional benchmark fixture**, not an authoritative or adjudicated gold corpus.

## Files

- `vobl-bootstrap-observations.json` — source-preserving observations for airport/ARP/elevation and runway table values; blocked placeholders for taxiways and runway holding positions.
- `corpus-manifest.json` — corpus identity, state, included classes, and gold blockers.
- `rights-manifest.json` — conservative processing controls pending rights approval.
- `split-manifest.json` — development-only split; explicitly not a statistical benchmark.
- `adjudication-log.json` — open elevation conflict and source-dependent extraction items.
- `CHANGELOG.md` — immutable version notes.

## Important semantics

An empty `features` array for taxiways or runway holding positions means **not extracted**, not absent from the airport. Consumers must check `completeness_status` and `empty_array_semantics`.

Coordinates are stored first as source DMS strings. The normalization script generates decimal CRS84 coordinates and preserves source text.

The dataset remains ineligible for gold status until original source bytes/hash, rights approval, two independent reviews, adjudication, evidence coordinates, and complete taxiway/holding inventories exist.
