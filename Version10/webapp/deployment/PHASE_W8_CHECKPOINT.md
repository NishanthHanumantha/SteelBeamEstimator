# PHASE W.8 — CHECKPOINT

Saved: 2026-08-25

## Status

**PASS WITH LIMITATIONS**

P2.6.10-proven context/detail evidence selection is integrated into the existing W.7 Hybrid path and verified locally (unit + bounded live Claude + First Set E2E). Lightsail was **not** updated in this session.

## Local proof

| Item | Result |
|---|---|
| Canonical E2E | `20260825_195802_60556880` |
| Claude | 18/18 success, `n_images=2` |
| P2.6.10 primary | 13 beams, distinct context+detail |
| W.6 fallback | 5 beams, explicit in manifests |
| Unexplained | 0 |
| Cut length overwrites | 0 |
| Stirrup quantity overwrites | 0 |
| Excel | download HTTP 200, 1468.732 kg |
| `/health` local | `phase=W.8` |

## Production

**NOT TOUCHED.** Public remains W.7 Hybrid production until the W.8 runtime pack is copied and Gunicorn restarted.

Pack ready: `C:\Users\nishanth.h\AppData\Local\Temp\w8_runtime.tar.gz`

## Reports

- `PHASE_W8_P2610_CROP_PIPELINE_INVENTORY.md`
- `PHASE_W8_CURRENT_VS_TARGET_CROP_PATH.md`
- `PHASE_W8_EVIDENCE_COVERAGE_REPORT.md`
- `PHASE_W8_VALIDATION_REPORT.md`
- `PHASE_W8_PREDEPLOY_CHECKPOINT.md`
- `PHASE_W8_IN_PROGRESS_RESUME.md` (superseded by this checkpoint)

## Next

Deploy the W.8 pack to Lightsail, restart the one Gunicorn worker, keep `HYBRID_MODE=production`, run one controlled First Set drawing, confirm coverage identity.
