# VOBL Gold-Corpus Policy

**Version:** 1.0  
**Corpus purpose:** benchmark extraction of the five approved feature groups without treating derived data as authoritative

## 1. Corpus unit and identity

The primary unit is an immutable airport-chart edition:

```text
publisher + airport ICAO + chart type + chart/page identifier + effective date + source SHA-256
```

For the first item, the expected identity is:

```text
AAI/BIAL + VOBL + Aerodrome Chart (ADC) + AD 2 VOBL 1-101 + 2025-11-27 + <pending PDF SHA-256>
```

No annotation starts as gold until the exact source bytes have been stored and hashed.

## 2. Approved labels

Only these labels are included:

- `airport`;
- `aerodrome_reference_point`;
- `aerodrome_elevation`;
- `runway`;
- `runway_direction`;
- `runway_threshold`;
- `taxiway`;
- `taxiway_element`;
- `runway_holding_position`;
- `runway_holding_marking`.

Buildings, aprons, stands, roads, frequencies, navigation aids, lighting objects, and airport boundaries are ignored or marked contextual, not negative examples, unless needed to distinguish an approved label.

## 3. Annotation layers

Every gold item contains:

1. **Source layer:** document, page, edition, effective date, digest, page dimensions.
2. **Evidence layer:** exact source token, bounding box/polygon, vector-object references where available.
3. **Semantic layer:** feature identity, type, designator, relationships, and original value/unit.
4. **Normalized layer:** normalized identifiers, decimal coordinates, units, and geometry with documented conversion.
5. **Quality layer:** reviewer decisions, disagreement/adjudication, ambiguity, and source conflicts.
6. **Temporal layer:** valid/effective interval and supersession link.

## 4. Annotation rules

- Transcribe before normalizing.
- Preserve capitalization, punctuation, degree/minute/second marks, leading zeros, and units in source fields.
- Never infer an unreadable character from expectation; label it `unreadable` and explain.
- A reciprocal runway pair is one runway feature with two direction features.
- Separate threshold points from the runway surface/centreline.
- Separate taxiway identity from individual taxiway elements.
- Separate the conceptual runway holding position from its painted marking line.
- Do not infer connectivity solely from lines crossing on the page.
- Do not use a marking-aid or lighting inset as if it were georeferenced main-map geometry.
- Record source conflicts rather than choosing a value during transcription.
- Derived decimal coordinates retain a link to the exact source DMS text and conversion version.

## 5. Annotation workflow

1. Intake steward verifies source identity/digest and creates a read-only annotation package.
2. Reviewer A annotates all approved labels.
3. Reviewer B independently annotates Q1 textual fields and associations and reviews all geometries.
4. A comparison report identifies differences.
5. A qualified adjudicator resolves differences or marks them unresolved.
6. Automated checks validate schema, coordinate conversion, units, reciprocal runways, geometry validity, and completeness.
7. Gold version is frozen with a version, manifest, reviewer IDs, and change log.

A model-generated result may be shown after independent annotation, but cannot become gold merely through self-confirmation.

## 6. Dataset splitting and leakage control

For expansion beyond VOBL:

- split by complete airport and publisher/template, never random crops from the same chart across train/test;
- keep at least one publisher/template or chart family as an out-of-distribution test slice;
- preserve separate vector-native, raster, multilingual, low-quality, and complex-topology slices;
- do not place adjacent editions of one airport into different train/test sets without a documented leakage assessment;
- record every source and annotation license before training use.

The first VOBL edition is a development/acceptance case, not by itself a statistically meaningful model test set.

## 7. Corpus versioning

A corpus release contains:

```text
corpus_version
schema_version
source_manifest.json
annotation files
adjudication log
validation report
split manifest
rights manifest
change log
```

Changes require a new corpus version. Corrections never overwrite the prior frozen release.

## 8. Quality checks

A frozen gold item requires:

- exact PDF SHA-256;
- 100% label evidence links;
- two-person review for all Q1 values and associations;
- zero unresolved annotation disagreements presented as facts;
- exact coordinate-conversion tests;
- explicit CRS/axis order and units;
- valid geometries or documented non-georeferenced page-space geometry;
- all five feature groups assigned a completeness status;
- source-rights state permitting corpus storage and the intended evaluation/training use.

## 9. Rights and access

The gold corpus must not redistribute source charts or evidence crops outside the permissions granted by AAI/BIAL or the accountable rights owner. Access is least-privilege. Exports may contain derived facts only if the rights decision explicitly permits them. Training use is a separate permission from internal visual review and must be recorded separately.

## 10. VOBL bootstrap status

| Item | Status |
|---|---|
| Higher-resolution user-supplied chart image reviewed | available in conversation; not exported as source bytes |
| Matching official URL located | complete |
| Exact original PDF stored and hashed | blocked by direct-access HTTP 403; user upload or authorized access needed |
| Annotation schema/policy | defined |
| Named reviewers/adjudicator | TBD |
| Rights for corpus/training | unconfirmed |
| Gold annotation | not started; correctly deferred until source/hash/rights gates pass |
