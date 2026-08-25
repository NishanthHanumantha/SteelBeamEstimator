# PHASE W.7 — HYBRID PRODUCTION GO-LIVE REPORT

Saved: 2026-08-25  
Classification: **W7_PASS_WITH_LIMITATIONS**

Public application: http://13.127.104.99/

## 1. Final classification

**W7_PASS_WITH_LIMITATIONS**

Hybrid production authority is live on the existing 2 GB Lightsail Version10 service. Controlled First Set E2E invoked real Claude Vision, reconciled every eligible beam, applied Vision-preferred semantics to canonical R13, and produced a downloadable Excel workbook. Deterministic engineering remained the authority for cut length, stirrup quantity, and steel-weight formulas.

Limitations (non-blocking, documented below): native T1 OpenCV crops were not present on this drawing set; `anthropic` must stay pinned below 1.x.

**GO for estimator testing** on http://13.127.104.99/ with `HYBRID_MODE=production`.

## 2. Production architecture (inspected, then updated)

```
Public :80
  Nginx  →  127.0.0.1:8001  (Version10 Gunicorn, 1 worker, timeout 3600s)
Rollback :8000 remains 8.9.x / Version8 (not public)
```

Instance: 1907 MB RAM, 0 swap, not resized.

## 3. Deployed Hybrid stage order

`VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D → L22 → R3 → R31 → R12A → R13 → HYBRID → VB1`

`HYBRID_MODE=authoritative` remains forbidden.

## 4. Authority boundary (unchanged)

Vision / Hybrid, when successfully resolved: Target, Layer, Physical Groups, Bar Count, Diameter, Specification, MAIN/EXTRA, Support Scope, Visual Stirrup Identification.

Deterministic only: Geometry, Spacers, Cut Length, DL, Anchorage, Hooks/Bends, Stirrup quantity/engineering, Piece generation, Steel weight, BBS, Excel.

VISION_ONLY groups are not materialized into bars.

## 5. Lightsail deployment changes

- Copied W.6 Hybrid runtime (PhaseW5 adapter updates, PhaseW6 package, W.6 runner, web wiring, `run_context.py`).
- `/health` `phase=W.7`, `app_release=W.7`.
- systemd unit comments updated; workers still 1; Nginx unchanged.
- `/etc/steel-beam-estimator-v10.env` `chmod 600` `root:root` with `ANTHROPIC_API_KEY` present (value never printed).
- Pinned and installed `anthropic==0.125.0` (`>=0.49.0,<1`). W.3 venv had `anthropic==1.0.0`, which is incompatible with the existing C.5 client.

Not deployed: local `.env`, venv, `__pycache__`, web_runs, research trees.

## 6. API key security

| Check | Result |
|------|--------|
| Key in git | no |
| Workstation `.env` copied | no |
| `/health` contains `sk-ant-` | no (E2E `SECRET_LEAK False`) |
| Health field | `api_key_configured=true`, `api_key_status=PRESENT` |
| `/etc/steel-beam-estimator-v10.env` | mode 600, key line count 1 |
| Temp env file on instance | removed after install |

## 7. HYBRID_MODE before and after

| Moment | Mode |
|------|------|
| Pre-deploy | off (W.5, no HYBRID stage, key absent) |
| After code deploy | off (key present, no Claude) |
| Controlled E2E | production |
| Rollback test | off |
| **Final** | **production** |

## 8. Controlled live production run

Preferred set: First Set Galera OHT&STP (already on `/home/ubuntu/w3_smoke`).

Canonical go-live run: **`20260825_113725_9a8d6014`**

| Metric | Value |
|--------|--------|
| Status | success |
| Duration | ~220 s wall (Hybrid 176.5 s) |
| Model | `claude-sonnet-4-5` |
| Classification | `HYBRID_SUCCESS` |
| Claude calls | 18 / 18 success, 0 fail |
| Handoff | `production_authority_applied=true`, 18 beams, 218 fields |
| Excel | 18 beams, 92 bars, **1432.237 kg**, `IS_456_DETERMINISTIC` |
| Download | HTTP 200, ZIP/`PK` workbook, 19515 bytes |
| Single-flight | concurrent POST → HTTP 409 |

Prior diagnostic run `20260825_112725_777a29d8` (anthropic 1.0.0): 18 API_FAILED attempts, 0 tokens, Excel **1424.397 kg** deterministic fallback, no R13 patch. Used as TEST-W7-16 evidence. Not the go-live result.

Local W.6 First Set was 1447.565 kg. Production 1432.237 kg is a live Vision difference, not a formula change.

## 9. Beam coverage reconciliation (go-live run)

```
total_beams                    18
hybrid_eligible                18
native_t1_crop                  0
generated_fallback_crop        18
visual_context_unavailable      0
claude_invocations             18
claude_success                 18
claude_failure                  0
deterministic_fallback          0
unresolved                      0
unexplained                     0
identity_ok                  true
```

Identities:

`18 = 0 native + 18 fallback + 0 unavailable`  
`18 = 18 success + 0 failure + 0 det_fallback`

`unexplained_count = 0`. Artefact: `data/web_runs/20260825_113725_9a8d6014/data/output/PhaseW6_hybrid_semantic_resolution/hybrid_coverage.json`.

## 10. Crop-path evidence

Production T1 wrote **0** `opencv_renders/*_crop.png` for this set. W.6 fallback rendered **18** run-isolated crops (`T1.5 envelope + M.1 renderer`), 34–62 KB each. `visual_prep.source = T1_ENVELOPE_PLUS_M1_RENDERER`.

Native T1 crop path was **not** exercised by First Set. Fifth Set was not used (bounded, as specified).

## 11. Claude live invocation evidence

Connectivity after SDK pin: `SMOKE_OK True`, model `claude-sonnet-4-5`, no secret text.

Go-live: 18 invocations, 176.5 s Hybrid latency, `claude_success=18`.

## 12. Production authority handoff

`handoff_reason=HYBRID_SEMANTIC_HANDOFF_APPLIED`  
`pre_hybrid` JSON written. VB.1 consumed patched `beam_reinforcement_models_production.json`. Steel changed vs deterministic 1424.397 kg.

## 13. Deterministic engineering protection

Same-bar_id `cut_length_mm` overwrite count: **0**. Stirrup `quantity` overwrite count: **0**. `calculation_method=IS_456_DETERMINISTIC`.

12 bar records appear in a different bucket after semantic role/layer moves; they are relocated existing bars, not VISION_ONLY fabrications. VISION_ONLY remains `UNRESOLVED_VISION_ONLY`.

## 14. VB.1 / Excel

Workbook generated and downloaded from `/api/download/<run_id>`. Public UI HTTP 200.

## 15. Resource observations

| Point | Mem used / available (MB) | Version10 worker RSS |
|------|---------------------------|----------------------|
| Before E2E | 598 / 1308 | ~68 MB |
| During Hybrid (~60–180 s) | ~704–707 / ~1200 | ~68 MB |
| After | 593 / 1314 | ~68 MB |

No swap, no OOM, no instance resize. Peak ~707 MB used on 1907 MB.

## 16. Rollback test

`HYBRID_MODE=off` → restart → `/health` `mode=off`, `production_may_invoke_claude=false`, site 200, 1 worker. Then restored `production`. Nginx not switched.

## 17. Final production mode

**`HYBRID_MODE=production`**  
`phase=W.7`, key configured, Hybrid stage between R13 and VB1, Gunicorn 1 worker on `:8001`.

## 18. Known limitations

1. First Set never emits T1 OpenCV crops; Hybrid depends on the W.6 envelope renderer for this set.
2. Lightsail must keep `anthropic>=0.49,<1`. Unpinned `anthropic==1.0.0` fails immediately (`ClaudeAPIError`, 0.000 s).
3. Live Vision totals can differ from the local W.6 First Set (1432.237 vs 1447.565 kg).

## 19. GO / NO-GO for estimator testing

**GO.** Use http://13.127.104.99/. Hybrid is the semantic authority when Claude succeeds; Excel remains deterministic engineering. Immediate disable: set `HYBRID_MODE=off` in `/etc/steel-beam-estimator-v10.env` and restart `steel-beam-estimator-v10`.

## TEST matrix

| Test | Result | Evidence |
|------|--------|----------|
| TEST-W7-01 Pre-deploy checkpoint | PASS | `PHASE_W7_PREDEPLOY_CHECKPOINT.md` |
| TEST-W7-02 Deploy integrity | PASS | W.6 modules present, `APP_RELEASE=W.7`, HYBRID in stages |
| TEST-W7-03 Secure API key | PASS | env 600, health boolean only |
| TEST-W7-04 Hybrid off regression | PASS | health after deploy; rollback health |
| TEST-W7-05 Public health W.7 | PASS | `phase=W.7`, Hybrid capability |
| TEST-W7-06 One worker | PASS | `--workers 1` throughout |
| TEST-W7-07 Native T1 crop | LIMITED | 0 native crops on First Set |
| TEST-W7-08 W.6 fallback crop | PASS | 18 generated crops |
| TEST-W7-09 Coverage reconcile | PASS | unexplained=0, identity_ok |
| TEST-W7-10 Live Claude | PASS | 18/18 after SDK pin |
| TEST-W7-11 Semantic resolution | PASS | 18 OBSERVED |
| TEST-W7-12 Production handoff | PASS | applied=true, 218 fields |
| TEST-W7-13 Engineering protection | PASS | cut_length overwrite 0; stirrup qty 0 |
| TEST-W7-14 VB.1 Excel | PASS | 1432.237 kg |
| TEST-W7-15 Public download | PASS | 200 / PK |
| TEST-W7-16 Failure / fallback | PASS | run `...777a29d8` API_FAILED → 1424.397 kg, no patch |
| TEST-W7-17 Resources | PASS | no OOM, 2 GB kept |
| TEST-W7-18 Off rollback | PASS | health mode=off |
| TEST-W7-19 Re-enable | PASS | final mode=production |

Local tests this phase: W.5+W.6 unit 27/27; Flask W.2+W.5+W.6 19/19.
