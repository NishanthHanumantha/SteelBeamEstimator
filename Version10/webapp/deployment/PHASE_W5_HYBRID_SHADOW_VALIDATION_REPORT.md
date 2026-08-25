# PHASE W.5 — HYBRID SHADOW VALIDATION REPORT

**Phase:** W.5  
**Type:** Integration + shadow validation  
**MODEL_VERSION (engineering label):** 10.0.0  
**App release:** W.5  
**Date:** 2026-08-25  
**PRIMARY_CLASSIFICATION:** `W5_PASS_SHADOW_READY`

Deterministic production Excel remains authoritative. Hybrid is integrated as a post-Excel shadow observer. Public traffic is running with `HYBRID_MODE=off` and no Anthropic key in the systemd environment.

---

## 1. Architecture before W.5

Public Version10 (W.3 / W.4) executed only:

```
Browser → Nginx → Gunicorn :8001 → Flask → PRODUCTION_STAGES
  VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D
  → L22 → R3 → R31 → R12A → R13 → VB1 → Estimation_Output.xlsx
```

W.4 confirmed this path never called Claude. Hybrid D.1–D.4 / E.2 lived in research runners only (`PRODUCTION_WRITE=false`).

---

## 2. Existing Hybrid components reused

| Component | Role in W.5 |
|-----------|-------------|
| P2.6.10-D.1 `vision_normalizer` / authority contract | Semantic field ownership (Vision vs deterministic engineering) |
| P2.6.10-D.2 `resolve_hybrid_beam` | Canonical hybrid semantic object |
| P2.6.10-E.1 `build_deterministic_payload` / `build_vision_payload` | R1.3 → groups; Vision payload normalize |
| P2.6.10-E.2 `call_live_beam` | Bounded live Claude Vision (reuses C.5 schema + P253 client) |
| P2.6.9 `extract_detected_groups` | Read-only R1.3 group extraction |
| T1 `opencv_renders/{beam_id}_crop.png` | Production visual evidence (no new crop pipeline) |
| `src/llm/claude_client.py` | Anthropic `messages.create` (env-first key load added) |

**Not reused on the production shadow path:** D.3 binding and D.4 `calculate_beam`. Those compute engineering quantities. W.5 compares semantics only so Hybrid cannot contaminate weight / BBS / Excel.

---

## 3. Exact integration boundary

```
Web request
    |
    v
Deterministic PRODUCTION_STAGES (unchanged)
    |
    v
Authoritative Excel copy  ----------------------+
    |                                           |
    |  HYBRID_MODE=off → stop (zero Claude)     |
    |  HYBRID_MODE=shadow → Hybrid Shadow Adapter
    |         |
    |         +--> T1 crop discovery
    |         +--> R1.3 catalog (read-only)
    |         +--> E.2 call_live_beam (budgeted)
    |         +--> D.2 resolve_hybrid_beam
    |         +--> semantic comparison
    |         v
    |     data/output/PhaseW5_production_hybrid_shadow/
    |         hybrid_shadow_report.json
    |
    v
Download Estimation_Output_<run_id>.xlsx  (bytes unchanged by shadow)
```

Flask does not contain Claude HTTP logic. The adapter lives in `Version10/src/PhaseW5_production_hybrid_shadow/`. The web wrapper is `webapp/services/hybrid_shadow_service.py`.

Shadow runs **after** Excel exists and **after** job status is `success`, so download is not blocked by Claude. The single-flight lock is still held until shadow finishes (2 GB RAM safety). Guardrails cap live calls and wall clock.

---

## 4. Hybrid vs deterministic responsibility

Unchanged from D.1 `hybrid_authority_contract.py`:

**Hybrid / Vision may observe:** target, layer, physical groups, bar count, diameter, specification, MAIN/EXTRA, support scope, visual stirrup identification.

**Deterministic remains authoritative for:** geometry, spacers, cut length, development, anchorage, hooks/bends, stirrup engineering quantities, pieces, weight, BBS, Excel.

W.5 does not promote Hybrid values into production models.

---

## 5. Shadow mode design

| `HYBRID_MODE` | Behaviour |
|---------------|-----------|
| `off` (default, production now) | No adapter artefacts. Zero Claude requests. |
| `shadow` | Observe + compare. Excel untouched. Failures recorded, estimation stays successful. |
| `authoritative` | Defined, **forbidden** in W.5 (`AUTHORITATIVE_FORBIDDEN`). |

Missing key in shadow: status `KEY_ABSENT`, `request_count=0`, explicit unavailable — not a fake success.

---

## 6. Configuration / secret handling

Preferred systemd file: `/etc/steel-beam-estimator-v10.env` (`chmod 600`, root-owned).

Template: `Version10/webapp/deployment/steel-beam-estimator-v10.env.example`

Variables: `HYBRID_MODE`, `ANTHROPIC_API_KEY`, `HYBRID_CLAUDE_MODEL`, `HYBRID_MAX_LIVE_CALLS` (default 6), `HYBRID_MAX_WALL_S` (default 90), `HYBRID_PER_CALL_TIMEOUT_S` (default 120).

`load_api_key()` now prefers the **process environment** (systemd EnvironmentFile), then dotenv files. It no longer requires the Windows-only `ClaudeConfig.DOTENV_PATH`.

**Secrets:** not committed. Not copied to Lightsail in this phase. Production `api_key_status=ABSENT`. Local workstation `.env` has a key; it was not transferred.

---

## 7. Failure isolation

- Adapter exceptions are caught; estimation status remains `success` if Excel already exists.
- Live call exceptions → per-beam `HYBRID_ERROR` or Vision unusable → `HYBRID_UNAVAILABLE`.
- Timeout / API failure mocks: Excel bytes unchanged (TEST 4).
- Authoritative mode refused.

---

## 8. Test matrix and results

| Test | Setup | Result |
|------|--------|--------|
| TEST 1 Hybrid Off | `HYBRID_MODE=off`, Flask stub + adapter | PASS. Excel generated. `request_count=0`. No PhaseW5 output dir. |
| TEST 2 Shadow available | Adapter + planted R1.3 + T1 crop + **mock** Claude client | PASS. Observation + comparison persisted. `cost_basis=ESTIMATED`. Excel unchanged. |
| TEST 3 Missing key | Adapter shadow, no key; Flask stub shadow | PASS. Adapter: `KEY_ABSENT`. Flask stub: `NO_ENGINEERING_CONTEXT` (stub R1.3). Excel succeeds. Zero requests. |
| TEST 4 Timeout / API failure | Mock `TimeoutError` and failed API | PASS. Excel unchanged. Failure recorded. |
| TEST 5 Output isolation | Same planted Excel/steel JSON before vs after shadow | PASS. Bytes identical. |
| W.2 smoke (regression) | Stub pipeline | PASS (15 tests with TEST 1–3 Flask). |
| Live Claude smoke_api | Existing C.5 connectivity check | **NOT RUN** this phase (no uncontrolled live API usage). |

TEST 2 used a structured mock returning the C.5 JSON contract through E.2 `call_live_beam`. That proves the integration boundary. It does **not** prove billed Anthropic usage.

---

## 9. Production validation runs

**STEP B — deployed with `HYBRID_MODE=off` (CONFIRMED)**

| Check | Result |
|-------|--------|
| Public `http://13.127.104.99/health` | `status=ok`, `phase=W.5`, `app_release=W.5` |
| `hybrid.mode` | `off` |
| `hybrid.api_key_status` | `ABSENT` |
| `production_excel_invokes_claude` | `false` |
| `shadow_may_invoke_claude` | `false` |
| `steel-beam-estimator-v10` | active + enabled |
| Old 8.9.x on `:8000` | still active |
| W.3 rollback copies | present |
| `/etc/steel-beam-estimator-v10.env` | present, `HYBRID_MODE=off`, **0** `ANTHROPIC_API_KEY` lines |

**STEP C — credentials on systemd:** not installed (intentional).  
**STEP D — `HYBRID_MODE=shadow` on public traffic:** not enabled.  
**STEP E — sample live drawings on production:** not run (would be uncontrolled API use without a key anyway).

No new public drawing set was processed for W.5. Deterministic Excel behaviour is therefore unchanged from W.3/W.4 for live traffic.

---

## 10. Agreement / disagreement summary

From TEST 2 (mock Vision matching planted 3-Y16 TOP MAIN): comparison machinery executed. Classification set is:

`AGREE` | `BENIGN_DIFFERENCE` | `SEMANTIC_DISAGREEMENT` | `MATERIAL_DISAGREEMENT` | `HYBRID_UNAVAILABLE` | `HYBRID_ERROR`

**Production disagreement vs real drawings:** none collected yet (shadow not live). Earlier Hybrid benefit evidence remains the E.1–E.3 research benchmarks; W.5 does not repeat those.

---

## 11. Latency summary

| Context | Hybrid latency |
|---------|----------------|
| Mode off | ~0 s (skip) |
| TEST 2 mock | sub-second plus E.2 import |
| Production public | N/A (off) |
| Shadow when enabled | bounded by `HYBRID_MAX_WALL_S=90` and `HYBRID_MAX_LIVE_CALLS=6`; does not change `duration_s` of the deterministic pipeline |

---

## 12. API usage / cost summary

| Context | Requests | Tokens | Cost |
|---------|----------|--------|------|
| Production public (now) | 0 CONFIRMED | 0 | 0 |
| TEST 2 mock | 1 mock | mock 120/40 | **ESTIMATED** from list prices, not billed |
| Live Anthropic this phase | 0 CONFIRMED | — | — |

Cost fields are always labelled `cost_basis=ESTIMATED` (Sonnet list-price constants in `config.py`). Never treat as invoice exact.

---

## 13. Reliability observations

- Mode off starts without a key (production `/health` CONFIRMED).
- Shadow without key is explicit `KEY_ABSENT` / engineering-context unavailable.
- Settings are snapshotted at pipeline start so concurrent tests cannot flip mode mid-run.
- Duplicate live calls in one run are cached by beam+crop size.

---

## 14. Limitations

1. Visual evidence is T1 OpenCV crops. Beams without a crop are `HYBRID_UNAVAILABLE` (no new renderer).
2. At most 6 live Vision calls per run (guardrail), then remaining beams skip.
3. T1 crops are not the same as QA.30 / B.1 research crops; live disagreement rates may differ from E.2/E.3.
4. D.3/D.4 engineering recalculation is intentionally not on this path.
5. Authoritative Hybrid is not implemented for production writes.
6. No live Anthropic call was executed from this workstation during W.5.
7. Brief Gunicorn restart occurred to load W.5 code; Nginx routing was not changed.

---

## 15. Deterministic production output changed?

**NO.** CONFIRMED for automated isolation tests. STRONGLY_INDICATED for production: `HYBRID_MODE=off`, shadow cannot write Excel, production stages list unchanged.

---

## 16. Recommendation for the next phase

**A. Continue Shadow Validation**

Do not promote Hybrid decisions. Next safe operator steps (separate from this report):

1. Place `ANTHROPIC_API_KEY` only in `/etc/steel-beam-estimator-v10.env` (`chmod 600`). Keep `HYBRID_MODE=off` for public Gunicorn.
2. Run a **post-hoc** bounded shadow on an existing `data/web_runs/<run_id>` (Excel already generated):

```bash
cd /opt/steel-beam-estimation/SteelBeamEstimator/Version10
set -a
# shellcheck disable=SC1091
. /etc/steel-beam-estimator-v10.env
set +a
export HYBRID_MODE=shadow
export HYBRID_MAX_LIVE_CALLS=3
export HYBRID_MAX_WALL_S=60
PYTHONPATH=src /opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp/.venv/bin/python \
  -m PhaseW5_production_hybrid_shadow --run-root data/web_runs/<run_id>
```

`/etc/steel-beam-estimator-v10.env` is root `chmod 600`; sourcing it requires a privileged read (for example `sudo cat` into a root-only temp env, or `sudo -E`). Keep Gunicorn `HYBRID_MODE=off` while doing this.

3. Review `hybrid_shadow_report.json` disagreement classes before considering any later promotion phase.

**Not recommended now:** B (UI recommendations) or C (promote a decision type).

---

## Success criteria checklist

- [x] Existing Hybrid/Claude architecture investigated before duplication
- [x] Clean production adapter boundary
- [x] Hybrid restricted to semantic/visual interpretation
- [x] Deterministic engineering remains authoritative
- [x] `HYBRID_MODE=off` works without an API key (local + production)
- [x] `HYBRID_MODE=shadow` can execute safely (local tests; production not switched on)
- [x] Hybrid failures cannot fail deterministic estimation
- [x] Structured observations captured
- [x] Deterministic vs Hybrid comparison captured
- [x] Agreement/disagreement classified
- [x] Latency observable
- [x] API usage/cost observable where available (`ESTIMATED`)
- [x] Secrets not committed or exposed
- [x] Production Excel unchanged by shadow mode
- [x] W.3 rollback capability intact
- [x] Report and checkpoint written
