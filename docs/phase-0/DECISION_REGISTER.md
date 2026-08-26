# Phase 0 Decision Register

**Status values:** `PROPOSED`, `APPROVED`, `BLOCKED`, `SUPERSEDED`  
**Severity:** `BLOCKER`, `REQUIRED_BEFORE_RELEASE`, `ADVISORY`

| ID | Decision | Provisional outcome | Owner | Severity | Status | Required evidence/action |
|---|---|---|---|---|---|---|
| D-001 | Intended use | Internal research/engineering evaluation only; non-operational | Accountable Data Owner — TBD | BLOCKER | PROPOSED | Name owner and approve or replace classification |
| D-002 | Exact source | AAI/BIAL VOBL ADC, AD 2 VOBL 1-101, 27 NOV 2025, AMDT 06/2025 | Source Steward — TBD | BLOCKER | BLOCKED | Upload or lawfully retrieve original PDF; hash and verify metadata |
| D-003 | Source rights | Do not assume reuse rights; AAI disclaimer appears to require express permission | Rights/Legal Owner — TBD | BLOCKER | BLOCKED | Written permission, applicable license, or signed internal rights determination covering storage, processing, evidence display, derived output, and training |
| D-004 | Authority hierarchy | A0 official digital data; A1 official eAIP text; A2 official chart; then B–E evidence classes | Accountable Data Owner — TBD | REQUIRED_BEFORE_RELEASE | PROPOSED | Owner approval |
| D-005 | Scoped features | Airport, runways, taxiways, runway holding positions, ARP/elevation only | Product Owner — TBD | REQUIRED_BEFORE_RELEASE | PROPOSED | Owner approval |
| D-006 | Initial release label | `RESEARCH_REVIEWED`; never authoritative | Accountable Data Owner — TBD | REQUIRED_BEFORE_RELEASE | PROPOSED | Owner approval |
| D-007 | Review ownership | Two-person review for Q1 fields; aviation adjudicator; separate release approval | Aviation Quality Owner — TBD | BLOCKER | BLOCKED | Name qualified owner, reviewers, and release manager |
| D-008 | VOBL elevation conflict | Preserve chart `3003 ft` and separately indexed eAIP `3001 ft`; reconcile matching effective editions before disposition | Aviation Quality Owner — TBD | REQUIRED_BEFORE_RELEASE | PROPOSED | Obtain current effective AD 2.1 source and record adjudication |
| D-009 | Cloud/managed OCR | Not authorized in Phase 0 | Security/Rights Owners — TBD | REQUIRED_BEFORE_RELEASE | PROPOSED | Data-flow, provider terms, region, retention, and security approval before benchmark |
| D-010 | Gold-corpus training use | Visual evaluation only until training rights are confirmed | Rights/Legal Owner — TBD | BLOCKER | BLOCKED | Separate permission for model training/fine-tuning |
| D-011 | Geometry acceptance | Page-space reviewed geometry only until Phase 1 derives positional thresholds; georeferenced geometry remains candidate | Aviation Quality Owner — TBD | REQUIRED_BEFORE_RELEASE | PROPOSED | Approve benchmark plan and tolerances after source analysis |
| D-012 | Canonical/export formats | PostGIS-aligned internal model; JSON/GeoJSON research view; AIXM mapping later | Product/Data Owners — TBD | ADVISORY | PROPOSED | Confirm consumer requirements in Phase 1 |

## Decision procedure

A decision becomes `APPROVED` only when a named accountable owner, date, rationale, and evidence reference are recorded. Silence or continued project activity is not approval. Blockers prevent Phase 0 exit but do not prevent preparation of governance artifacts.

## Approval record template

```text
Decision ID:
Outcome:
Accountable owner (name and role):
Approval date:
Rationale:
Evidence/link:
Review/expiry date:
Constraints:
```
