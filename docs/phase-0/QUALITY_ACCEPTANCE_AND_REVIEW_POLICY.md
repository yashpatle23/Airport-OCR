# Quality, Acceptance, and Review Policy

**Version:** 1.0  
**Applies to:** VOBL research/evaluation release  
**Operational use:** not authorized

## 1. Quality principle

The unit of acceptance is not a PDF page or model response. It is an evidence-linked, versioned field or geometry inside a complete airport-edition release. Unknown or unreadable data must remain unknown; fabrication is a release-blocking defect.

## 2. Feature criticality

| Class | Features | Minimum review |
|---|---|---|
| Q1 — safety-significant | ICAO, ARP, aerodrome elevation, runway designator pair, direction, dimensions, threshold coordinates/elevations, taxiway identity/connectivity, runway-holding identity/association/marking | Two-person adjudicated gold label; human approval of every extracted item |
| Q2 — supporting geometry | Runway/taxiway page-space geometry and georeferenced geometry | GIS reviewer plus aviation reviewer for semantic association |
| Q3 — provenance/metadata | source ID, page, bounding box, method, model/parser version, dates, rights, review state | Automated schema validation plus release-manager check |

All five requested feature groups include Q1 data. No requested class is eligible for unreviewed automatic release in the initial project.

## 3. Lifecycle states

`RAW_OBSERVATION → CANDIDATE → NEEDS_REVIEW → RESEARCH_REVIEWED`

Alternate terminal states are `REJECTED`, `BLOCKED`, and `SUPERSEDED`. Every transition is audited. Promotion requires the gates below; confidence alone cannot promote a record.

## 4. Research-release acceptance gates

The following gates are measurable and mandatory for a `RESEARCH_REVIEWED` VOBL release.

### 4.1 Source and provenance

- 100% of released fields and geometries link to source document, page, and page-space bounding geometry.
- 100% identify extractor/manual method and version.
- Source SHA-256, effective date, retrieval date, and rights status are present.
- Release is blocked if original source bytes are unavailable or rights prohibit the intended internal processing.

### 4.2 Completeness

- Exactly one airport record for VOBL.
- Exactly two reciprocal runway-pair records and four direction/threshold records, subject to confirmation from the original PDF.
- Taxiway and runway-holding inventories equal the adjudicated gold corpus: 100% recall by identity and no extra invented identifiers.
- Every one of the five requested feature groups has `complete`, `not_present`, or `blocked` status with a reason. Only `complete` is allowed in a final complete research release.

### 4.3 Text and numeric correctness

For ICAO, names, designators, directions, dimensions, source coordinate strings, and source elevations:

- 100% exact match to the adjudicated gold value after only documented whitespace/Unicode normalization.
- 100% correct unit association.
- 0 digit substitutions in accepted coordinates/elevations.
- 0 invented identifiers or values.
- Decimal coordinate conversion reproduces the source DMS value within `5e-8` degrees or the precision implied by the source, whichever is less strict.
- GeoJSON output order is verified as longitude, latitude.

### 4.4 Geometry and association correctness

Until Phase 1 establishes evidence-based positional thresholds, geometry acceptance is split:

- Page-space runway/taxiway/holding geometry must be independently reviewed against the source at a fixed render setting and must pass 100% semantic association checks.
- Every runway-holding marking must reference the correct taxiway/element and runway direction or be explicitly unresolved.
- Taxiway graph connectivity must have zero unexplained connections across merely visual crossings and zero unexplained dangling endpoints in the accepted area.
- All polygons must pass OGC validity checks; automated repair cannot be silently accepted.
- Georeferenced output remains `CANDIDATE` until a documented transform, independent holdout points, source-accuracy metadata, and a Quality Owner-approved tolerance exist.

Phase 1 must replace this temporary page-space gate with numeric point/line/polygon tolerances derived from chart scale, source quality, and intended use. That change cannot relax semantic or provenance gates.

### 4.5 Conflict handling

- 100% of differing effective-aligned source claims produce a conflict record.
- 0 conflicts are resolved by averaging.
- A conflict may remain visible in a research release only with named reviewer disposition and an explicit warning.
- The chart `3003 ft` versus the separately indexed AAI eAIP textual `3001 ft` aerodrome-elevation claims must remain a tracked conflict until effective-edition reconciliation.

### 4.6 Validation and reproducibility

- 100% schema validation pass.
- 100% reciprocal-runway rules pass.
- 100% CRS, axis-order, and unit fields present.
- 100% mandatory reviewer decisions present.
- Re-running identical source digest, code, model, and configuration reproduces normalized observations or records a documented nondeterministic component and equivalent checked result.
- 0 blocker-severity validation failures.

## 5. Review process

1. **Reviewer A** creates or checks an annotation without seeing model confidence where practical.
2. **Reviewer B** independently reviews every Q1 value/association.
3. Disagreements enter an adjudication queue; no majority-by-software rule is allowed.
4. The **Aviation Quality Owner** or delegated qualified adjudicator records the final gold decision and rationale.
5. The **Release Manager** verifies completeness, rights, source digest, validation report, and required approvals.
6. The **Accountable Data Owner** approves the permitted audience/use.

Reviewers must be identified by organization-controlled identities. Decisions are append-only; corrections create a new decision/version.

## 6. Mandatory reviewer evidence

The review interface or packet must show:

- original page and exact evidence crop;
- source and page coordinates;
- candidate and alternatives;
- normalized value and original token;
- previous edition where available;
- source conflicts;
- rule failures;
- geometry overlay at a known render scale;
- extraction method/version;
- intended release label.

## 7. Failure severity

| Severity | Example | Release effect |
|---|---|---|
| BLOCKER | missing original PDF/hash; rights unknown for intended release; wrong airport/edition; no accountable owner | no Phase 0 exit or release |
| CRITICAL | wrong threshold coordinate, runway designator, holding association, or axis order | reject affected release; investigate systemic impact |
| MAJOR | missing taxiway, broken topology, wrong evidence link | block completeness and release |
| MINOR | non-semantic formatting issue with preserved value | fix or record accepted exception |

## 8. Quality reporting

Each release manifest reports counts by feature/state, exact-match results, false additions/omissions, conflicts, validation failures, reviewer disagreement, corrections, geometry metrics, source digest, pipeline versions, and release limitations.

## 9. Policy ownership

- Accountable Data Owner: **TBD**
- Aviation Quality Owner: **TBD**
- Technical Custodian: **TBD**
- Next review: before Phase 1 benchmark begins

This policy is intentionally limited to non-operational research. Operational acceptance criteria require a separate safety/regulatory quality process and responsible-authority requirements.
