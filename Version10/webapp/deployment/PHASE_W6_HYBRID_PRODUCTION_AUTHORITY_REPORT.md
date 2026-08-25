# PHASE W.6 — Hybrid Production Authority Integration

Saved: 2026-08-25  
Classification: **W6_PASS_WITH_LIMITATIONS**  
Scope: local implementation + local validation only. Lightsail was not modified.

---

## 1. Hybrid architecture investigation

### Existing Hybrid components reused

| Role | Canonical component | Used in W.6 |
|------|---------------------|-------------|
| Vision live call | P2.6.10-E.2 `call_live_beam` via W.5 `live_invoke.call_shadow_beam` | Yes |
| C.5 schema / Claude client | `PhaseP2610C5` + `src/llm/claude_client.py` | Yes |
| D.2 semantic resolver | `resolve_hybrid_beam` via W.5 `semantic.resolve_semantic` | Yes |
| D.1 authority contract | Vision-preferred vs deterministic-engineering fields | Yes (not rewritten) |
| Deterministic groups | P2.6.9 `extract_detected_groups` | Yes (handoff identity) |
| R13 catalog / T1 crop discovery | W.5 `catalog.py`, `visual_sources.py` | Yes, extended |
| Shadow observer | W.5 `run_hybrid_shadow` | Yes (production mode added) |

D.3 / D.4 engineering calculation runners are **not** on the production Excel path. VB.1 remains the Excel/BBS/weight authority.

### Exact production insertion point

```
R13 writes beam_reinforcement_models_production.json
    ↓
HYBRID (new PRODUCTION_STAGES entry)
    T1 crop if present, else T1.5 envelope + M.1 DXF renderer
    → E.2 Claude Vision
    → D.2 resolve_hybrid_beam
    → canonical R13 semantic patch (Vision-preferred fields only)
    → artefacts under PhaseW6_hybrid_semantic_resolution/
    ↓
VB1 reads the same production JSON
    → cut length / DL / stirrup engineering / pieces / weight / BBS / Excel
```

**OPTION A** was chosen: an explicit HYBRID stage between R13 and VB1.  
R13 is the last producer of production reinforcement semantics; VB1 is the first consumer of that JSON for Excel. That is the cleanest authority boundary.

### Authority boundary

**Vision / Hybrid (when successfully resolved):** target, layer, physical groups, bar count, diameter, specification, MAIN/EXTRA, support scope, stirrup identification.

**Deterministic only:** geometry, spacers, cut length, development length, anchorage, hooks/bends, stirrup quantity/engineering, piece generation, steel weight formula, BBS, Excel.

VISION_ONLY groups are recorded as unresolved and **not** materialized (no fabricated cut length).

---

## 2. Implementation summary

### Hybrid integration code (created)

- `Version10/src/PhaseW6_hybrid_production_authority/` — orchestrator, handoff, observability, envelope-crop adapter, unit tests
- `Version10/Run_PY/run_phase_w6_hybrid_production_authority.py`
- `Version10/webapp/tests/test_w6_hybrid_authority.py`
- `Version10/webapp/tests/run_w6_live_smoke.py`
- `Version10/webapp/tests/run_w6_live_e2e.py`

### Hybrid integration code (modified)

- `Version10/src/PhaseW5_production_hybrid_shadow/config.py` — `MODE_PRODUCTION`
- `Version10/src/PhaseW5_production_hybrid_shadow/settings.py` — production defaults (unlimited calls / no extra wall cap), health payload
- `Version10/src/PhaseW5_production_hybrid_shadow/adapter.py` — production live loop; persist `hybrid_semantic`; `max_live_calls=0` / `max_wall_s=0` mean unlimited
- `Version10/src/PhaseW5_production_hybrid_shadow/visual_sources.py` — also discover W.6 envelope crops
- `Version10/webapp/config.py` — `APP_RELEASE=W.6`; HYBRID stage between R13 and VB1
- `Version10/webapp/routes.py` — `/health` phase W.6; `hybrid.production_authority`; `api_key_configured` bool only
- `Version10/webapp/services/hybrid_shadow_service.py` — do not double-call Claude after Excel when HYBRID is a production stage
- `Version10/webapp/services/estimation_service.py` — no post-Excel PENDING shadow when HYBRID is in the stage list
- `Version10/webapp/services/version10_adapter.py` — stub Hybrid artefact; fallback warning
- `Version10/webapp/deployment/steel-beam-estimator-v10.env.example`
- `Version10/webapp/deployment/steel-beam-estimator-v10.service` (comments only; still `HYBRID_MODE=off`)
- `Version10/src/config/run_context.py` — `PHASE_W6` dirname constant
- `Version10/webapp/tests/test_w5_hybrid_shadow.py` — health phase W.6
- `Version10/webapp/tests/test_w2_smoke.py` — isolate `HYBRID_MODE=off` in setUp

### Deterministic engineering (intentionally not modified)

T1, VB.1, R13 engineering bar builder, cut-length / DL / stirrup engines, piece generation, BBS, D.1–D.4 research runners, E.2 live caller internals, benchmark/truth data.

---

## 3. Authority flow (implemented)

```
DXF
  ↓
VROOT1 / R1 geometry + beam registry
  ↓
T1 (evidence; crops only when OpenCV fallback runs)
  ↓
R2A → R21B → R21C → R21D → L22 → R3 → R31 → R12A
  ↓
R13 production JSON (deterministic semantics + engineering lengths)
  ↓
HYBRID
  Claude Vision (E.2) + D.2 resolution
  Canonical handoff patches Vision-preferred fields on R13
  Pre-hybrid snapshot: beam_reinforcement_models_production.pre_hybrid.json
  Ledger: hybrid_handoff_ledger.json
  ↓
VB1 deterministic engineering
  Cut length / DL / stirrup engineering / pieces / weight / BBS
  ↓
Estimation_Output.xlsx
```

Modes:

| `HYBRID_MODE` | Behavior |
|---------------|----------|
| `off` (default) | Skip Hybrid. R13 unchanged. No Claude. |
| `shadow` | Observe only. No R13 patch. |
| `production` | Vision-preferred fields become production authority when resolved. |
| `authoritative` | Still forbidden (W.5 guard). |

---

## 4. Claude API integration status

| Item | Result |
|------|--------|
| Loading path | Process `ANTHROPIC_API_KEY`, then repo-root `.env` via `load_dotenv(override=False)`. Canonical local file: `C:\Users\nishanth.h\SteelBeamEstimator\.env`. Production intended: `/etc/steel-beam-estimator-v10.env` |
| API key configured | **YES** (local). Value never printed. |
| Real Claude invoked locally | **YES** |
| Bounded smoke (TEST-W6-03) | 1 call, success, `claude-sonnet-4-5`, vision ~12.4 s, Hybrid latency 29.1 s |
| First Set production Hybrid | **18 / 18 successful calls**, 0 failed, 0 timeout, Hybrid latency **204.5 s**, model `claude-sonnet-4-5` |
| Secret exposure | None in source, health, observability, or handoff artefacts |

`/health` exposes only `api_key_configured: true/false` (and existing `api_key_status` ABSENT/EMPTY/PRESENT). No costs on the public health payload beyond W.5’s existing estimated-cost fields in internal reports.

---

## 5. Validation matrix

| Test | Result | Evidence |
|------|--------|----------|
| TEST-W6-01 Hybrid off regression | **PASS** | Unit + Flask stub: Excel generated, 0 Claude, no W.6 artefacts |
| TEST-W6-02 API key discovery | **PASS** | Local configured **YES**; missing-key path classifies `HYBRID_UNAVAILABLE` |
| TEST-W6-03 Live Hybrid invocation | **PASS** | Real Claude 1-beam smoke: render → Claude → D.2 → handoff |
| TEST-W6-04 Production authority handoff | **PASS** | Mock: quantity 3→4, dia 16→20 consumed. Live First Set: 18 beams patched, 205 field writes, then VB.1 Excel **1424.397 kg → 1447.565 kg** from the patched R13 |
| TEST-W6-05 Engineering authority | **PASS** | Live ledger: 37/37 patched bars `cut_length_mm` unchanged. Stirrup quantity not overwritten. VB.1 `calculation_method=IS_456_DETERMINISTIC` |
| TEST-W6-06 Hybrid failure | **PASS** | Missing key and mock API failure: no R13 patch, explicit classification, Excel still generated (stub / fallback policy) |
| TEST-W6-07 Output isolation | **PASS** | Artefacts under `data/web_runs/<run_id>/data/output/PhaseW6_hybrid_semantic_resolution/`. Single-flight 409 unchanged |
| TEST-W6-08 Full local E2E | **PASS WITH LIMITATIONS** | First Set 18 beams. Flask one-shot initially had no T1 crops (fallback). After W.6 envelope-crop adapter: 18 live Claude calls + VB.1 Excel downloadable. Steel 1447.565 kg, 92 bars, 110 BBS rows |
| TEST-W6-09 Secret safety | **PASS** | No `sk-ant-` in source/artefacts/health |
| TEST-W6-10 Engineering regression | **PASS** | T1 / VB.1 / R13 builder / D.1–D.4 / E.2 internals unchanged. Only `run_context.py` +1 line among core config |

W.5 unit tests: **12/12 PASS**. W.6 unit tests: **14/14 PASS**. Flask W.2+W.5+W.6: **19/19 PASS**.

---

## 6. Production impact (local)

- **Hybrid off:** deterministic pipeline unchanged. No Claude.
- **Hybrid production:** Vision-preferred semantic fields are patched onto R13 **before** VB.1. Proven: Excel steel weight changed after handoff while bar count stayed 92 and cut lengths stayed deterministic.
- **Hybrid failure:** no fabricated Vision result; deterministic R13 kept; Excel still generated; observability `fallback_used=true`.
- **Concurrency:** Gunicorn workers remain 1. Single-flight unchanged.
- **T1 crop gap:** production T1 only writes `opencv_renders` for OpenCV-fallback residual beams. W.6 reuses T1.5 `geometry_envelopes.json` + existing Phase M.1 `dxf_renderer.render_dxf_region_to_png` into run-isolated `PhaseW6_hybrid_semantic_resolution/crops/`. T1 source is not rewritten.

First Set live Hybrid (run `20260825_155022_fd634c41`):

| Metric | Value |
|--------|--------|
| Beams | 18 |
| Vision calls | 18 success / 0 fail |
| Hybrid latency | 204.5 s |
| Beams patched | 18 |
| Ledger | 37 PATCHED, 9 VISION_ONLY groups unresolved, 18 VISION_ONLY stirrups unresolved |
| Quantity fields changed | 2 |
| Diameter fields changed | 3 |
| Cut length changed | 0 |
| Excel bars | 92 |
| Excel steel | 1447.565 kg (was 1424.397 kg before Hybrid) |
| BBS rows | 110 |

---

## 7. Lightsail deployment plan (do not execute in W.6)

1. **Deploy:** Version10 `src/PhaseW5_production_hybrid_shadow/`, `src/PhaseW6_hybrid_production_authority/`, `Run_PY/run_phase_w6_hybrid_production_authority.py`, `webapp/config.py`, `webapp/routes.py`, `webapp/services/{estimation_service,version10_adapter,hybrid_shadow_service}.py`, `src/config/run_context.py`, updated env example / systemd comments.
2. **Do not deploy:** `.env`, API keys, `webapp/.env` with secrets, research output trees, this workstation’s `data/web_runs` Hybrid artefacts.
3. **Environment:** keep `HYBRID_MODE=off` until a separate go-live. For Hybrid production later: `HYBRID_MODE=production` and `ANTHROPIC_API_KEY` in `/etc/steel-beam-estimator-v10.env` (`chmod 600`).
4. **systemd:** `EnvironmentFile=-/etc/steel-beam-estimator-v10.env`; `Environment=HYBRID_MODE=off` until approved. `--workers 1` unchanged.
5. **Restart:** `systemctl restart steel-beam-estimator-v10` after files + env. Do not change Nginx solely for Hybrid.
6. **Health:** `/health` → `phase=W.6`, `hybrid.mode`, `hybrid.api_key_configured` true/false, `hybrid.production_authority`.
7. **Verify Hybrid later:** one First Set (or equivalent) with `HYBRID_MODE=production`; confirm `PhaseW6_hybrid_semantic_resolution/hybrid_observability.json` `classification=HYBRID_SUCCESS`, `claude_invocation_count>0`, `production_authority_applied=true`, then Excel.
8. **Rollback:** `HYBRID_MODE=off` in `/etc/steel-beam-estimator-v10.env` (or systemd Environment) → restart Version10 service → deterministic pipeline resumes. No Nginx switch required.

---

## 8. Final go / no-go

**W6_PASS_WITH_LIMITATIONS**

Hybrid production authority is implemented and locally proven: a successful Vision/D.2 result is written onto the R13 production JSON and VB.1 consumes it for BBS/Excel (steel 1424.397 → 1447.565 kg with unchanged cut lengths). Limitations: T1 does not always emit crops (W.6 envelope renderer fills that); the first Flask one-shot fell back before that adapter; Lightsail remains on W.5 / `HYBRID_MODE=off` by design.
