# VERSION9 — DIMENSION-Channel Stirrup Discovery Patch (9.2.0)

**MODEL_VERSION:** 9.2.0  
**Scope:** Discovery-layer only (R.1). No Track 1, association redesign, role-classifier changes, or spacer changes.

---

## Part A — Sets 2 & 3 DIMENSION sweep (read-only)

**Gate:** Same convention as Set 1 → **PROCEEDED to Part B.**

| Set | DIMENSION ents | With override | Stirrup callouts (after strip_mtext) | Callout layer | GT beams with nearby callout |
|-----|---------------:|--------------:|-------------------------------------:|---------------|-----------------------------:|
| First | 88 | 81 | **24** | `-STR-RF-DIM` (24) | **18/18** |
| Second | 306 | 193 | **61** | `-STR-RF-DIM` (60), `S- Structural` (1) | **64/66** |
| Third | 313 | 191 | **52** | `-STR-RF-DIM` (52) | **57/61** |

Artefacts: `part_a_sets23_dimension_sweep.md` / `.json`

---

## Part B — Patch

### Config flag

`Version9/config/generalized_reinforcement_discovery.yaml`:

```yaml
discovery:
  enable_dimension_text_scan: true   # false → pre-patch TEXT/MTEXT-only
```

### Code changes

| File | Change |
|------|--------|
| `dxf_text_utils.py` | `is_dimension_entity`; DIMENSION `entity_raw_text` (skip `<>`); DIMENSION position via `text_midpoint`/`defpoint` (**not** spurious `insert=(0,0)`) |
| `adaptive_association_engine.py` | `_collect_entities` allowlist + flag; same annotation record shape as TEXT/MTEXT |
| `beam_detail_segmenter.py` | Legacy path respects same flag |
| `phase_r1_orchestrator.py` / `__init__.py` | MODEL_VERSION → 9.2.0 |
| `Run_PY/run_phase_r1_generalized_reinforcement_discovery.py` | **Critical:** load Version9 `src`/`config` (was hardcoded to Version8 — patch would never run) |

No layer-name hardcoding. No parallel post-discovery path.

---

## Part C — QA.2A (flag ON) vs M.2 baseline

### 1. Discovery table (R.1 STIRRUP annotations)

| Set | GT stirrup rows | Pre-patch found | Post-patch found | New ratio |
|-----|----------------:|----------------:|-----------------:|----------:|
| 1 | 23 | 0 | **24** | **104.3%** |
| 2 | 90 | 3 | **64** | **71.1%** |
| 3 | 96 | 17 | **69** | **71.9%** |

Beams with ≥1 STIRRUP in R.1: Set1 **18/18**, Set2 **61**, Set3 **60**.

### 2–3. STIRRUP role×status (QA.2A) — before (Day-1/M.2) vs after

| Set | Status | Before (Day-1) | After (9.2.0) |
|-----|--------|----------------:|--------------:|
| 1 | MISSING | 20 | **5** |
| 1 | PARTIAL_MATCH | 3 | 0 |
| 1 | WRONG_QUANTITY | — | **15** |
| 1 | WRONG_DIAMETER | — | 1 |
| 1 | MATCH | — | **2** |
| 2 | MISSING | 81 | **27** |
| 2 | WRONG_QUANTITY | 2 | **45** |
| 2 | MATCH | — | **15** |
| 2 | PARTIAL / WRONG_DIA | 6 / 1 | 2 / 1 |
| 3 | MISSING | 81 | **41** |
| 3 | WRONG_QUANTITY | 9 | **41** |
| 3 | MATCH | 2 | **14** |

**Known limitation (expected):** large shift MISSING → WRONG_QUANTITY. Discovery now surfaces stirrups; zone/spacing/piece-count quality remains a Track 1 / qty-engine residual — not a discovery blocker.

### 4. Overall metrics

| Metric | M.2 baseline (9.1.0) | After DIMENSION patch (9.2.0) | Δ |
|--------|---------------------:|------------------------------:|---|
| Overall accuracy % | 60.79 | **67.97** | **+7.18** |
| Beam detection % | 93.92 | 93.92 | 0 |
| Bar detection % | 48.99 | **61.37** | **+12.38** |
| Bar match % | 25.05 | 25.04 | ≈0 |
| Steel KG accuracy % | 75.2 | **91.57** | **+16.37** |
| Avg pipeline (s) | 36.64 | 57.92 | +21 (R.1 still ~1s; variance elsewhere) |

Per-set overall: First 66.5→**76.45**, Second 64.8→**69.43**, Third 56.22→**63.18**.  
Per-set steel: First 72.4→**99.94**, Second 82.16→**87.16**, Third 71.05→**87.61**.

New runs: `qa2_*_20260801_103357/103505/103630`.

### 5. R4 — Flag-off equivalence

`enable_dimension_text_scan: false` on all 3 sets:

| Set | Result |
|-----|--------|
| First | total_annotations=65, STIRRUP=0 — **identical to Day-1 counts** |
| Second | signature vs pre-patch snapshot — **IDENTICAL** |
| Third | signature vs pre-patch snapshot — **IDENTICAL** |

Artefact: `part_c_r4_flag_off.json`

---

## Risk checks R1–R5

| ID | Check | Result |
|----|-------|--------|
| **R1** | Ordinary DIMENSION noise | Most overrides are non-callout; classifier keeps them UNKNOWN / non-rebar. Part A: Set2 193 overrides → 61 callouts; Set3 191→52. Production STIRRUP groups track callouts, not all dimensions. |
| **R2** | Duplicate annotations | No material double-count of same (beam, text, xy) STIRRUP keys; TEXT/MTEXT + DIMENSION callouts are largely complementary channels. |
| **R3** | Performance | Flag-off R.1 ~3.6–4.5s/set; flag-on R.1 ~0.7–1s on warm cache. Full pipeline avg 58s (acceptable). |
| **R4** | Flag-off ≡ pre-patch | **PASS** all 3 sets |
| **R5** | Non-STIRRUP production roles unchanged | **PASS** — 0 non-STIRRUP group/qty deltas vs M.2 production models on all 3 sets (`part_c_r5_role_deltas.json`) |

---

## Track 1 recommendation (revised)

Day-1 said discovery ≪ GT and Track 1 was the volume lever. **This patch revises that for text-bearing stirrups:**

| Residual class | After 9.2.0 | Owner |
|----------------|-------------|--------|
| Never-discovered text | Largely closed on Set1; Sets 2/3 ~70%+ of GT rows have R.1 STIRRUP text | Discovery done for DIMENSION channel |
| MISSING still | 5+27+41 = **73** GT stirrup rows | Geometry / typical-detail / remaining text gaps → **Track 1** (shrunk) |
| WRONG_QUANTITY / zone | **15+45+41 = 101** rows | Pitch/zone engine + Track 1 geometric evidence |
| Association quality | Mostly working after position fix; residual mis-links possible | Monitor; not primary now |

**Track 1 effort shrinks** from “recover ~182 missing discoveries” to “resolve ~73 residual MISSING + improve qty/zone for ~100 WRONG_QUANTITY.” Optional micro-fix (INSERT explode) remains small.

---

## Files modified

```
Version9/config/generalized_reinforcement_discovery.yaml
Version9/src/PhaseR.1_generalized_reinforcement_discovery/dxf_text_utils.py
Version9/src/PhaseR.1_generalized_reinforcement_discovery/adaptive_association_engine.py
Version9/src/PhaseR.1_generalized_reinforcement_discovery/beam_detail_segmenter.py
Version9/src/PhaseR.1_generalized_reinforcement_discovery/phase_r1_orchestrator.py
Version9/src/PhaseR.1_generalized_reinforcement_discovery/__init__.py
Version9/Run_PY/run_phase_r1_generalized_reinforcement_discovery.py
Version9/Run_PY/run_phase_qa2a_ground_truth_benchmark.py  (header version only)
```

Version8: **untouched**.

---

## Proposed git commit message

```
feat(Version9): 9.2.0 DIMENSION-channel stirrup discovery in R.1

Collect DIMENSION text overrides behind enable_dimension_text_scan,
fix Version9 R.1 runner to load Version9 src, and recover Set1–3
stirrup callouts on -STR-RF-DIM. QA.2A: overall 60.8→68.0, steel 75→92.
```

---

## Integrity

- Spacer engine / M.2: unchanged  
- Association / role classifier logic: unchanged (only discovery inputs widened + correct DIMENSION xy)  
- Version8: untouched  
- Flag-off restores pre-patch R.1 annotations  
