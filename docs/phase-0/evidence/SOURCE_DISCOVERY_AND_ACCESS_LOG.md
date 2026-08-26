# Source Discovery and Access Log

**Date:** 2026-08-19  
**Target:** VOBL Aerodrome Chart, `AD 2 VOBL 1-101`, 27 NOV 2025, `AMDT 06/2025`

## Located official source

- Publisher domain: AAI AIM India
- URL: <https://aim-india.aai.aero/eaip/eaip-v2-06-2025/eAIP/VOBL-ADC.pdf?amdt=show>
- Search-result title identifies an aerodrome chart for Kempegowda International Airport Bengaluru with ARP `13°11′56″N 077°42′20″E` and displayed aerodrome elevation `3003 ft`.
- The attached higher-resolution chart visually matches the airport, chart identifier, date, amendment, and publisher context.

## Access attempts

| Method | Result |
|---|---|
| Official-domain web search | Success: exact URL and indexed chart metadata located |
| HTTPS `curl` with redirects and browser user-agent | Failed: HTTP 403 Forbidden |
| Web content fetch | Failed: HTTP 403 Forbidden |
| Sandboxed headless browser | Failed before page retrieval: network tunnel connection error |

No partial, synthetic, cached, or third-party PDF was retained. The controlled source directory contains intake instructions only.

## Rights evidence

AAI AIM India's indexed [site disclaimer](https://aim-india.aai.aero/sites/default/files/menu_item_files/disclaimer_clause.pdf) describes restrictive intellectual-property conditions and indicates that permission is required. The disclaimer itself also returned HTTP 403 to direct fetch from this environment, so the source register records only the indexed policy result and does not claim a complete legal determination.

Required rights decision must explicitly cover:

- storing original PDF bytes;
- internal parsing/OCR/CV;
- displaying pages/crops to reviewers;
- storing annotations and derived geometries;
- internal or external derived-data publication;
- redistribution of source or crops;
- use for model training/fine-tuning;
- retention/deletion requirements.

## Acquisition blocker and resolution

**Blocker:** the official PDF is located but original bytes are not available to this workspace. Therefore no SHA-256, media verification, malware scan, or exact PDF identity check can be completed.

**Resolution:** an authorized source steward should upload the exact original PDF or provide an accessible authorized delivery channel. Expected filename after verification: `sources/VOBL-ADC_AMDT-06-2025.pdf`.

Content from web sources was rephrased for compliance with licensing restrictions.
