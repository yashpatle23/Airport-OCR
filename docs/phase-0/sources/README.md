# Controlled Source Intake

This directory is reserved for source files that pass controlled intake.

## Expected primary file

`VOBL-ADC_AMDT-06-2025.pdf`

Expected identity:

- official URL: <https://aim-india.aai.aero/eaip/eaip-v2-06-2025/eAIP/VOBL-ADC.pdf?amdt=show>
- chart: `AD 2 VOBL 1-101`
- displayed date: `27 NOV 2025`
- amendment: `AMDT 06/2025`
- aeronautical information: `AUG 2025`

## Current status

The URL was located on the official AAI AIM India domain, but direct download attempts from this sandbox returned HTTP 403, and browser network access failed at the sandbox tunnel. No placeholder PDF is stored: an absent source is safer than a mislabeled or incomplete file.

The newly attached chart image is available visually in the conversation but is not mapped to a workspace file and therefore cannot be checksummed here.

## Authorized intake procedure

1. An authorized source steward obtains the exact PDF through AAI AIM India or uploads the original file.
2. Confirm the header identity above before moving it into this directory.
3. Record the delivery URL/channel and retrieval timestamp.
4. MIME-sniff and malware-scan the file.
5. Compute SHA-256 and byte size.
6. Update `../source-register.json`.
7. Store written rights/permission evidence outside the source file and reference it from the register.
8. Set source status to `ACQUIRED_QUARANTINED`, then `VERIFIED` only after metadata and integrity checks.

Do not substitute a screenshot, reprinted chart, third-party copy, or different AIRAC/amendment without registering it as a separate source.
