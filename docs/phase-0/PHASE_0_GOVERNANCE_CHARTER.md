# Phase 0 Governance Charter — VOBL Aerodrome Chart Extraction

**Project:** VOBL PDF → Extract → Identify → Structure → Validate → Search  
**Charter version:** 1.0  
**Prepared:** 2026-08-19  
**Status:** conditionally approved for research/evaluation setup; not approved for operational use

## 1. Purpose

This charter establishes the governance controls required before technical benchmarking begins. It covers source authority, intended use, permitted releases, ownership, scope, quality gates, review responsibilities, change control, and Phase 0 exit criteria.

The newly supplied higher-resolution chart image was reviewed and is consistent with:

- AIP India chart `AD 2 VOBL 1-101`;
- Kempegowda International Airport Bengaluru (`VOBL`);
- chart date/effective publication display `27 NOV 2025`;
- aeronautical-information date `AUG 2025`;
- amendment `AMDT 06/2025`;
- compiled and published by BIAL within AIP India.

The image improves visual review but is not a substitute for obtaining and hashing the original PDF.

## 2. Provisional intended-use decision

Until a named accountable owner approves another use, the project is classified as:

> **Research and engineering evaluation only — non-operational, non-navigation, internal access.**

The following are prohibited under this provisional classification:

- operational flight, vehicle, routing, safety, or navigation decisions;
- describing extracted data as authoritative;
- external redistribution of source charts or derived chart imagery;
- unattended publication of extracted fields;
- commercial use or production integration without rights and governance approval.

Changing intended use to planning, commercial, operational, or safety-related use requires a recorded decision, rights review, aviation safety/data-quality review, and revised acceptance criteria.

## 3. In-scope product

Only these five feature groups are approved for the initial corpus and extraction product:

1. Airport identity.
2. Runways, reciprocal directions, dimensions, thresholds, and relevant elevations.
3. Taxiways: identifiers and centreline and/or surface geometry.
4. Runway holding positions: operational association and marking-line geometry where available.
5. Aerodrome Reference Point coordinates and aerodrome elevation.

Contextual objects may be detected to interpret the chart but are excluded from released structured output unless a scope-change decision is approved.

## 4. Authority hierarchy

Authority rank guides reconciliation but never deletes conflicting evidence.

| Rank | Source class | Permitted use |
|---:|---|---|
| A0 | Current official digital aeronautical data from the responsible AIS/aerodrome, such as licensed AIXM/AMDB | Preferred canonical candidate after validation and rights review |
| A1 | Current effective AAI eAIP structured text/tables | Preferred textual-attribute candidate |
| A2 | Current effective official AAI/BIAL chart PDF | Primary chart evidence and geometry candidate |
| B | Official BIAL technical data for the same effective period | Cross-check or candidate, subject to authority and rights |
| C | Licensed, reputable third-party aviation/GIS data | Cross-check only unless explicitly designated |
| D | Software-derived observation from PDF/image | Never authoritative by itself; requires evidence and approval |
| E | Unverified web/image/user transcription | Discovery only; cannot be accepted without corroboration |

Rules:

- Preserve every source claim, source date, and conflict.
- Never average conflicting coordinates or elevations.
- A higher-ranked source does not silently erase lower-ranked evidence.
- Effective-date alignment is mandatory before comparison.
- Only the responsible authority can make a source authoritative for operational use.

## 5. Release labels

Every record and export must carry one label:

| Label | Meaning | External/operational use |
|---|---|---|
| `RAW_OBSERVATION` | Unreviewed parser/OCR/CV or manual observation | Prohibited |
| `CANDIDATE` | Normalized but not fully validated | Prohibited |
| `RESEARCH_REVIEWED` | Passed the non-operational acceptance policy and human review | Internal research only |
| `VALIDATED_DERIVED` | Passed an approved production policy but remains derived | Only for the explicitly approved audience/use |
| `AUTHORITATIVE_SOURCE` | Delivered by and represented as authoritative by the responsible provider | According to provider terms; never assigned to our extraction |
| `REJECTED` | Known incorrect/inapplicable candidate retained for audit | Prohibited |
| `SUPERSEDED` | Previously applicable version replaced by a newer effective version | Historical/audit only |

The system must never promote derived data to `AUTHORITATIVE_SOURCE`.

## 6. Roles and RACI

People are not invented in this charter. The organization must assign names before full Phase 0 exit.

| Activity | Accountable | Responsible | Consulted | Informed |
|---|---|---|---|---|
| Intended use and release approval | **Accountable Data Owner — TBD** | Product owner — TBD | Aviation SME, legal/rights owner | Engineering and reviewers |
| Source rights and redistribution | **Rights/Legal Owner — TBD** | Source steward — TBD | AAI/BIAL as needed | Data owner |
| Aviation semantics and conflict adjudication | **Aviation Quality Owner — TBD** | Qualified aviation reviewers — TBD | GIS/geodesy engineer | Data owner |
| Source intake/checksum/provenance | Technical custodian | Data engineer | Security, source steward | Quality owner |
| Gold-corpus annotation | Aviation Quality Owner | Two independent reviewers | GIS/ML engineers | Product owner |
| Extraction pipeline | Engineering owner — TBD | PDF/OCR/CV/data engineers | Aviation and GIS SMEs | Data owner |
| Security and platform controls | Security owner — TBD | Platform/SRE | Engineering, legal | Data owner |
| Release operation | Accountable Data Owner | Release manager — TBD | Quality and rights owners | Consumers |

No person may be the sole extractor, sole reviewer, and sole approver for an operational or safety-related release.

## 7. Decision and change control

A recorded decision is required for:

- intended-use change;
- new country, publisher, chart type, or feature class;
- a new source authority or change in source precedence;
- externally visible data or imagery;
- use of managed/cloud OCR or multimodal models;
- automatic acceptance of a feature class;
- quality-threshold reduction;
- unresolved source-conflict disposition;
- retention or deletion policy change.

Each decision record must include owner, date, rationale, alternatives, impact, review date, and status. Open decisions are maintained in `DECISION_REGISTER.md`.

## 8. Phase 0 deliverables

- This governance charter.
- Machine-readable source and rights register.
- Quality, acceptance, and review policy.
- Gold-corpus policy.
- Source-acquisition evidence and checksum status.
- Decision register.
- Exit report with pass/conditional/block status.

## 9. Phase 0 exit criteria

Phase 0 exits only when all are true:

1. The exact original VOBL PDF is stored and SHA-256 hashed.
2. Source provenance and effective-publication metadata are recorded.
3. Rights for intended storage, processing, display, and derived output are confirmed in writing or by an accountable rights owner.
4. Intended use is approved by a named Accountable Data Owner.
5. A named Aviation Quality Owner and reviewer pool are assigned.
6. Scope and release labels are approved.
7. Measurable non-operational acceptance criteria are approved.
8. Gold-corpus policy is approved.
9. No unresolved `BLOCKER` remains in the decision register.

Current status is documented in `PHASE_0_EXIT_REPORT.md`. Technical benchmarking may not be represented as having passed Phase 0 while any blocker remains.

## 10. Source citations and licensing note

The matching official chart was located at [AAI AIM India VOBL ADC, AMDT 06/2025](https://aim-india.aai.aero/eaip/eaip-v2-06-2025/eAIP/VOBL-ADC.pdf?amdt=show). AAI's published [site disclaimer](https://aim-india.aai.aero/sites/default/files/menu_item_files/disclaimer_clause.pdf) indicates restrictive intellectual-property terms and the need for express permission. This project therefore records rights as unconfirmed rather than assuming that public access permits reuse.

Content from web sources was rephrased for compliance with licensing restrictions.
