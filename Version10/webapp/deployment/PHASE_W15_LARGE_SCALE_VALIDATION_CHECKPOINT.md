# Phase W.15 Checkpoint (paused 2026-08-27)

W.14 remains frozen at `b90d08c95c4563dbbc0871609484f3cbe0c2df13`.  
No production logic was changed. This file records the live large-scale run so validation can resume.

## Run identity

- Origin: **manual browser upload** on `http://13.127.104.99/` (Release W.14)
- Run ID: `20260827_110320_4e330c37`
- Result: [http://13.127.104.99/?run=20260827_110320_4e330c37](http://13.127.104.99/?run=20260827_110320_4e330c37)
- Download: [http://13.127.104.99/api/download/20260827_110320_4e330c37](http://13.127.104.99/api/download/20260827_110320_4e330c37)
- Workbook: `Estimation_Output_20260827_110320_4e330c37.xlsx`
- Status: `success`, `DOWNLOAD_READY`
- Backup (non-disruptive): `/opt/steel-beam-estimation/backups/w15_prevalidate_20260827T163512Z`

## Uploaded files (browser names → stored names)

| Slot | Browser filename | Stored name | Bytes |
| --- | --- | --- | ---: |
| General Notes | `SE-100_GENERAL NOTE_(SH-01 & SH-02)_R01.dxf` | `SE-100_GENRAL_NOTE_SH-01_SH-02_R0_1.dxf` | 8,129,155 |
| Framing | `11-18TH FLOOR.dxf FRAMING.dxf` | `11-18TH_FLOOR.dxf_FRAMINIG.dxf` | 2,223,169 |
| Reinforcement | `479_SE-228_TYPICAL FLOOR BEAM REINFORCEMENT DETAILS(11-18)_R0_(SH-01 TO SH-03).dxf` | `479_SE-228_TYPICAL_FLOOR_BEAM_REINFORCEMENT_DETAILS11-18_R0_SH-01_TO_SH-03.dxf` | 11,408,702 |

Measured beam count: **143** (large-scale / Sixth Set 11–18F class).

## Hybrid snapshot from production status

| Metric | Count |
| --- | ---: |
| Total / eligible | 143 |
| Evidence generated | 143 |
| Evidence unavailable | 0 |
| Claude attempted | 143 |
| Claude API success | 143 |
| Claude API failure | 0 |
| D.2 resolved | 143 |
| R13 patches applied | 140 |
| Deterministic fallback | 0 |
| Unexplained | 0 |

`PREVIOUS_26_CALL_CLIFF_NOT_REPRODUCED` (success continued through 143/143).

P2.6.10 primary evidence: 127. W.6 compatibility path: 16.

## Timing snapshot

- Total wall: **5527.75 s** (~92 min)
- Hybrid/Vision: **1541.821 s** (~10.8 s per successful call)
- Evidence: started ~247 s elapsed; last evidence beam ~3952 s elapsed (~3705 s evidence window)

## Manual download

The human user reported a successful browser Download Excel before pausing. Automated durability / openpyxl / overwrite / token-cost dump remain to finish on resume.

## Resume next

1. Forensic dump (lifecycle, tokens, cost ESTIMATED, overwrites).
2. Automated download + openpyxl + refresh/`?run=` checks.
3. Worker-restart durability only if the server is idle.
4. Final W.15 classification report. Do not start another large run automatically.
