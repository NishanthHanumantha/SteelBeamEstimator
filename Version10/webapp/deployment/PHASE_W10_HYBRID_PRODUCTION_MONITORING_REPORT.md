# PHASE W.10 — HYBRID PRODUCTION MONITORING REPORT

Saved: 2026-08-26  
Classification: **W10_PASS_MONITORING_ACTIVE**

Public: http://13.127.104.99/  
`/health`: `status=ok`, `phase=W.10`, `app_release=W.10`, `hybrid.mode=production`, `api_key_status=PRESENT`

No new Claude calls were made for this phase. Monitoring was applied offline to existing production run trees, then deployed so future Hybrid stages write the same artefacts automatically.

---

## A. Phase classification

**W10_PASS_MONITORING_ACTIVE**

Crop generation was **not** changed. Production evidence does not justify a targeted crop rewrite: zero unexplained beams, zero unavailable, explicit fallbacks, and duplicate-image cases still resolved by Hybrid.

---

## B. Production architecture

Unchanged.

Vision decides what reinforcement exists (target, layer, groups, count, diameter, specification, MAIN/EXTRA, support scope, visual stirrup identity).

Deterministic VB.1 decides how it is engineered (geometry, spacers, cut length, DL, anchorage, hooks, stirrup quantity, pieces, weight, BBS, Excel).

---

## C. Production baseline

Inspected Lightsail before change: W.9, `HYBRID_MODE=production`, 1 Gunicorn worker, `anthropic==0.125.0`, key PRESENT.

Recent Hybrid-capable runs:

| Run | Phase / notes | Beams | Primary | Native T1 | Compatibility | Unavailable | Claude success | Semantic changes | Notes |
|-----|---------------|------:|--------:|----------:|--------------:|------------:|---------------:|-----------------:|-------|
| `20260826_065256_4ba41266` | W.9 go-live | 18 | 13 | 0 | 5 | 0 | 18 | 14 correction + 4 material | Full W.8 manifests |
| `20260825_113725_9a8d6014` | W.7 go-live | 18 | HISTORICAL_OBSERVABILITY_LIMITED | 0 | 18 | 0 | 18 | 15 correction + 3 material | No `hybrid_evidence/` tree |
| `20260825_112725_777a29d8` | W.7 anthropic 1.x diagnostic | 18 | HISTORICAL_OBSERVABILITY_LIMITED | 0 | 18 | 0 | 0 | 18 unavailable/fallback | Excel still generated; 0 tokens |

Earlier W.3/W.5 runs on the instance (`20260824_*`, `20260825_053226_*`, `20260825_054727_*`) predate Hybrid production authority and are not treated as Hybrid monitoring baselines.

---

## D. Evidence coverage (canonical W.9 run)

`20260826_065256_4ba41266`

| Metric | Value |
|--------|------:|
| Hybrid eligible | 18 |
| P2.6.10 primary | 13 |
| Native T1 | 0 |
| Compatibility / W.6 fallback | 5 |
| Deterministic fallback | 0 |
| Unavailable | 0 |
| Unexplained | **0** |
| Identity | `18 = 13 + 0 + 5 + 0 + 0` |

Every eligible beam has an explicit classification in `beam_evidence_reviews.json`.

---

## E. Duplicate evidence analysis (W.9)

| SHA relation | Count |
|--------------|------:|
| Distinct context/detail | 14 |
| Same SHA | 4 |
| Unknown | 0 |

Same-SHA beams: **B11, B15, B16, B17**.

- Reason: **COMPATIBILITY_FALLBACK** (W.6 envelope used as both images; logged `C1C2_SELECTED_NON_PRIMARY` or `P2610_PRIMARY_NOT_USABLE`).
- Outcome: **RELIABLE_RESOLUTION** (all `hybrid_status=OBSERVED`, Claude success).

B18 is mixed (W.6 context + B.1 detail), distinct SHAs, not a duplicate.

Duplicate images are **not** treated as production failures. They did not cause Vision failure on this run.

W.7 runs: duplicate SHA **HISTORICAL_OBSERVABILITY_LIMITED** (no W.8 selected.png pair). W.7 behaviour was known envelope duplication; not re-invented here.

---

## F. Hybrid semantic behaviour (W.9)

Mapped from existing W.5 `comparison.agreement_classification`. Labels describe **change vs deterministic**, not “improvement”.

| W.10 label | Count | W.5 source |
|------------|------:|------------|
| DETERMINISTIC_AGREEMENT | 0 | AGREE |
| SEMANTIC_REINFORCEMENT | 0 | BENIGN_DIFFERENCE |
| SEMANTIC_CORRECTION | 14 | SEMANTIC_DISAGREEMENT |
| MATERIAL_DISAGREEMENT | 4 | MATERIAL_DISAGREEMENT (count/diameter) |
| UNAVAILABLE_OR_FALLBACK | 0 | HYBRID_UNAVAILABLE / HYBRID_ERROR |

Hybrid changed semantic interpretation on all 18 resolved beams relative to deterministic R13. That is an operational fact to track over future runs, not a claim that every patch is better.

W.7 go-live: 15 correction + 3 material, 0 unavailable.  
W.7 1.x failure: 18 unavailable/fallback, Excel still produced (1424.397 kg).

---

## G. Operational metrics

### W.9 canonical (`20260826_065256_4ba41266`)

| Metric | Value | Source |
|--------|--------|--------|
| Claude attempted / success / fail | 18 / 18 / 0 | coverage + observability |
| Success rate | 100% | derived |
| Hybrid duration | 200.924 s | W.6/W.5 `hybrid_latency_s` |
| Vision duration (sum of per-beam latencies) | 199.349 s | W.5 per-beam `usage.latency_s` |
| Average Vision / beam | 11.075 s | derived |
| Evidence generation duration | NOT_RECORDED | not stored on this historical run; future live Hybrid stages record it |
| Pipeline duration in monitor JSON | NOT_RECORDED | not persisted on the run tree |
| Pipeline duration (W.9 journal) | 321.05 s | gunicorn `Pipeline complete` log from go-live — labelled separately, not copied into cost |
| Tokens | 68980 in / 12515 out | W.5 shadow report |
| Cost | **ESTIMATED** **$0.394665** | W.5 `estimate_cost_usd`; public list rates; **not billed exact** |

### W.7 go-live

Hybrid 176.499 s; ESTIMATED $0.359595 (67360 / 10501 tokens); 18/18 Claude.

### W.7 1.x diagnostic

Hybrid 110.359 s; 0 tokens; ESTIMATED $0.00; 0/18 Claude; deterministic Excel completed.

---

## H. Targeted crop improvement

**NO CHANGE REQUIRED**

Priority scan:

1. Unexplained gaps: **0**
2. Unavailable beams: **0**
3. Repeated compatibility fallback: B11, B15–B18 — explicit, same pattern as local W.8
4. Duplicated images: 4 beams, all RELIABLE_RESOLUTION
5. C3 VISION_NOT_READY: converted to explicit W.6 fallback, then Claude succeeded
6. Weak evidence causing Hybrid failure: **none on this run**

A crop rewrite of C3/B.1 for those five beams would be a research program, not a production bugfix.

---

## I. Deterministic protection (W.9 monitor)

| Check | Value |
|------|------:|
| cut_length_overwrites | **0** |
| geometry_overwrites | **0** |
| stirrup_quantity_overwrites | **0** |
| deterministic_engineering_overwrite_count | **0** |
| Excel present | true |
| calculation_method | IS_456_DETERMINISTIC |
| steel | 1425.732 kg / 92 bars |

---

## J. Production deployment

Backup: `/opt/steel-beam-estimation/backups/w10_predeploy_20260826T072800Z`

Files deployed:

- `src/PhaseW10_hybrid_production_monitoring/*` (runtime; not `unit_tests.py`)
- `src/PhaseW6_hybrid_production_authority/orchestrator.py` (fail-safe monitor hook + evidence timing)
- `webapp/config.py`, `webapp/routes.py`, systemd comment

Service: `systemctl restart steel-beam-estimator-v10`  
Workers: 1  
Anthropic: 0.125.0  
HYBRID_MODE: production (after rollback probe)

Offline monitor written onto the three Hybrid run trees (no Claude). Future estimates persist `PhaseW10_hybrid_monitoring/` during the Hybrid stage; if that write fails, Hybrid and Excel continue.

Rollback: `HYBRID_MODE=off` + restart still works (tested, then restored to production). File rollback from `w10_predeploy_*`. W.9 evidence-pack backup remains `w9_predeploy_*`.

---

## K. Remaining limitations

1. Five First Set beams still use explicit W.6/compatibility evidence; four duplicate the envelope image. Logged, Hybrid still resolved them.
2. W.7 runs cannot reconstruct P2.6.10 primary vs SHA-distinct pairs (`HISTORICAL_OBSERVABILITY_LIMITED`).
3. Historical pipeline duration and evidence-generation duration are NOT_RECORDED in W.10 JSON; live runs after this deploy will record evidence-generation duration.
4. Cost is ESTIMATED, never ACTUAL billed.
5. Semantic “correction” means disagreement with deterministic semantics, not proven accuracy gain.

---

## L. Recommended operational state

**Hybrid production should remain enabled.**

No follow-up deployment phase is required for monitoring. Review fallback beams and material-disagreement cases over accumulated production runs; improve crops only if later runs show unexplained gaps, unavailable evidence, or duplicate images that actually fail Vision.

---

## Tests

Local: 27 tests OK (W.10 unit tests + W.6 authority tests).

| ID | Result |
|----|--------|
| TEST-W10-01 W.9 architecture still runs | PASS |
| TEST-W10-02 monitor artefact | PASS |
| TEST-W10-03 coverage identity | PASS |
| TEST-W10-04 explicit classification | PASS |
| TEST-W10-05 no silent gap | PASS |
| TEST-W10-06 provenance | PASS |
| TEST-W10-07 duplicate analysis | PASS |
| TEST-W10-08 semantic classifications | PASS |
| TEST-W10-09 monitor cannot fail Excel | PASS |
| TEST-W10-10 Claude failure Excel-safe | PASS |
| TEST-W10-11 engineering protection | PASS |
| TEST-W10-12 no secrets | PASS (`sk-ant-` absent in health and monitor JSON) |
| TEST-W10-13 production drawing analysed | PASS (W.9 First Set run, no extra Claude) |
| TEST-W10-14 crop before/after | N/A — no crop change |

---

## Modified files (this phase; not auto-committed)

Runtime:

- `Version10/src/PhaseW10_hybrid_production_monitoring/` (`__init__.py`, `__main__.py`, `config.py`, `monitor.py`, `sanitize.py`, `writer.py`, `unit_tests.py`)
- `Version10/src/PhaseW6_hybrid_production_authority/orchestrator.py`
- `Version10/webapp/config.py`
- `Version10/webapp/routes.py`
- `Version10/webapp/deployment/steel-beam-estimator-v10.service`
- `Version10/webapp/tests/test_w5_hybrid_shadow.py`
- `Version10/webapp/tests/test_w6_hybrid_authority.py`

Deployment helpers / reports:

- `Version10/webapp/deployment/pack_w10.py`
- `Version10/webapp/deployment/_w10_deploy.sh`
- `Version10/webapp/deployment/_w10_analyze_runs.sh`
- `Version10/webapp/deployment/_w10_inspect_runs.sh`
- `Version10/webapp/deployment/PHASE_W10_RUNTIME_DEPLOYMENT_INVENTORY.md`
- `Version10/webapp/deployment/PHASE_W10_HYBRID_PRODUCTION_MONITORING_REPORT.md`
