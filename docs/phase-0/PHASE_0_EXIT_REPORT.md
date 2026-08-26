# Phase 0 Exit Report

**Project:** VOBL aerodrome-chart extraction  
**Assessment date:** 2026-08-19  
**Overall result:** **BLOCKED — governance package prepared, Phase 0 not exited**

## 1. Result summary

The first phase has been executed as far as this environment and the supplied material allow. The exact official source URL has been located, the newly attached higher-resolution chart has been incorporated into source identification, and the governance/quality/corpus controls have been written. Phase 0 cannot truthfully be marked complete because the original PDF, rights approval, and named accountable owners are still missing.

This is an intentional safety and governance stop—not a technical extraction failure.

## 2. Deliverables completed

| Deliverable | Status | File |
|---|---|---|
| Governance charter and provisional intended use | Complete, pending owner approval | `PHASE_0_GOVERNANCE_CHARTER.md` |
| Authority hierarchy and release labels | Defined, pending owner approval | `PHASE_0_GOVERNANCE_CHARTER.md` |
| Roles and RACI | Defined by role; names pending | `PHASE_0_GOVERNANCE_CHARTER.md` |
| Measurable research acceptance gates | Defined, pending Quality Owner approval | `QUALITY_ACCEPTANCE_AND_REVIEW_POLICY.md` |
| Gold-corpus policy | Defined, pending rights/reviewer approval | `GOLD_CORPUS_POLICY.md` |
| Decision register | Complete with blockers and proposed decisions | `DECISION_REGISTER.md` |
| Machine-readable source/rights register | Complete for currently known evidence | `source-register.json` |
| Official URL discovery and access-attempt evidence | Complete | `evidence/SOURCE_DISCOVERY_AND_ACCESS_LOG.md` |
| Controlled source-intake procedure | Complete | `sources/README.md` |

## 3. Exit-criterion assessment

| # | Criterion | Result | Evidence / blocker |
|---:|---|---|---|
| 1 | Exact original VOBL PDF stored and SHA-256 hashed | **FAIL — BLOCKER** | Official URL located; direct access returned HTTP 403; attachment is not workspace source bytes |
| 2 | Provenance and effective-publication metadata recorded | **PARTIAL** | Chart ID/date/amendment/publisher/URL recorded; PDF digest, byte size, retrieval channel, and file verification pending |
| 3 | Rights for storage, processing, display, outputs, and training confirmed | **FAIL — BLOCKER** | AAI disclaimer appears restrictive; no written permission or accountable rights determination supplied |
| 4 | Intended use approved by named Accountable Data Owner | **FAIL — BLOCKER** | Research-only classification is provisional; owner name/approval pending |
| 5 | Named Aviation Quality Owner and reviewer pool assigned | **FAIL — BLOCKER** | Roles exist; names and qualifications pending |
| 6 | Scope and release labels approved | **PARTIAL** | Defined but not approved by a named owner |
| 7 | Measurable acceptance criteria approved | **PARTIAL** | Research criteria defined but not approved; operational criteria intentionally absent |
| 8 | Gold-corpus policy approved | **PARTIAL** | Policy prepared; rights and owner approvals pending |
| 9 | No unresolved blocker remains | **FAIL** | D-001, D-002, D-003, D-007, and D-010 remain blocked |

**Exit decision:** `NO-GO` for Phase 1 benchmarking represented as an approved project phase. Preparation may continue, but source parsing, evidence-crop storage, model training, or any release should wait for the applicable blockers.

## 4. Source status

Expected official source:

- AAI AIM India: <https://aim-india.aai.aero/eaip/eaip-v2-06-2025/eAIP/VOBL-ADC.pdf?amdt=show>
- `AD 2 VOBL 1-101`
- `27 NOV 2025`
- `AMDT 06/2025`
- aeronautical information `AUG 2025`
- compiled/published by BIAL

The official URL is established, but source acquisition is incomplete. No fake or empty PDF has been placed in `sources/`.

## 5. Minimum information required to close Phase 0

1. Upload the exact original VOBL PDF or provide an authorized accessible copy.
2. Provide the name/role of the **Accountable Data Owner**.
3. Confirm the intended use: keep `internal research/evaluation only`, or specify another use.
4. Provide the name/role of the **Aviation Quality Owner** and at least two qualified reviewers, or explicitly defer reviewer assignment with an approved date.
5. Provide written source permission/license or the name of the accountable Rights/Legal Owner who approves internal storage, processing, reviewer display, derived output, and any model-training use.
6. Approve or amend the proposed authority hierarchy, scope, release labels, acceptance policy, and gold-corpus policy.

## 6. Immediate completion procedure after PDF upload

Once the PDF is available, the technical custodian will:

1. store it as `sources/VOBL-ADC_AMDT-06-2025.pdf`;
2. MIME-sniff and malware-scan it;
3. calculate SHA-256 and byte size;
4. verify header metadata against the registered edition;
5. update `source-register.json` with local path, checksum, integrity, delivery channel, and rights reference;
6. close D-002 if identity passes;
7. rerun this exit assessment after owner and rights decisions are recorded.

## 7. Approval block

```text
Accountable Data Owner: ____________________  Date: __________
Approved intended use: ______________________________________

Aviation Quality Owner: ___________________  Date: __________
Reviewer A: _______________________________  Reviewer B: _______________________________

Rights/Legal Owner: _______________________  Date: __________
Permission/license reference: _________________________________________________

Phase 0 decision:  APPROVE / APPROVE WITH CONDITIONS / REJECT
Conditions: __________________________________________________________________
```

Content from web sources was rephrased for compliance with licensing restrictions.
