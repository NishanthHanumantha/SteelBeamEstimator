# PHASE W.11 — STUCK-RUN FORENSIC REPORT

Saved: 2026-08-26  
Affected run: **`20260826_084708_f74912b8`**  
Public UI symptom: spinner stayed on **"Resolving reinforcement semantics..."** for ~45+ minutes.

---

## Timeline (UTC)

| Time | Event |
|------|--------|
| 08:47:08 | Public estimate started (`run_id` timestamp). Single-flight busy. |
| 08:47:12–08:51:12 | Deterministic stages VROOT1 → R13 completed (~4 minutes). |
| 08:52:54 | Hybrid/W.6 directory created. W.8 `prepare_production_evidence` started. |
| 08:50 (approx.) | `/health` already showed `busy=true`, `active_run_id=20260826_084708_f74912b8`. |
| 09:47 | Forensic snapshot: Hybrid subprocess PID 168565 **56 minutes**, **99.9% CPU**, state `R` (running, not sleeping on network). |
| 09:49:50 | Evidence still being written; newest beam **B92**. **137** evidence dirs so far. |
| ~09:54 | Evidence generation completed (143 packages). Duration **3707.455 s** (~61.8 min). |
| then | Sequential Claude Vision for 143 beams, **1542.647 s** (~25.7 min), avg **10.788 s**/beam. |
| ~10:19 | Excel present. Hybrid observability `HYBRID_SUCCESS`. Worker idle. |

Total wall from upload to Excel: about **92 minutes**. Hybrid stage alone ≈ evidence 3707 s + Vision 1548 s ≈ **87.6 minutes**.

Drawing: `479_SE-228_TYPICAL_FLOOR_BEAM_REINFORCEMENT_DETAILS11-18_R0_SH-01_TO_SH-03.dxf` (**143 beams**, 25.7 t steel). Not the 18-beam First Set.

---

## Root cause

**Classification: E — sequential P2.6.10 evidence generation on a large population, with a static Hybrid-stage UI label.**

This was **not** a hung Claude API call, not an SDK retry storm, and not a deadlock.

The Hybrid production stage (`run_phase_w6_hybrid_production_authority.py`) does two things under one UI label:

1. W.8 P2.6.10-B.1 context+detail crop generation (CPU-bound DXF render, ~25 s/beam on this drawing)
2. Then sequential Claude Vision (~11 s/beam)

The Flask job message is set once when the HYBRID stage starts (`"Resolving reinforcement semantics..."`) and is not updated per beam. The estimator therefore saw an unchanged spinner for the entire evidence+Vision period.

At 45 minutes the process was still healthy: rendering PNGs, 100% CPU, files advancing (B89 → B9 → B90 → B91 → B92). Claude had **not** been invoked yet (`hybrid_shadow_report.json` absent at 09:49).

The run **did complete** without being killed: Claude 143/143, 0 timeouts, 0 unavailable, Excel generated, `calculation_method=IS_456_DETERMINISTIC`.

---

## Why it looked unbounded

| Mechanism | Observed value | Effect |
|-----------|----------------|--------|
| Production `HYBRID_MAX_WALL_S` | **0** (unlimited Claude loop) | No Hybrid wall budget after evidence |
| `HYBRID_PER_CALL_TIMEOUT_S` | 120, **not wired** into Anthropic `messages.create` | Settings existed but did not bound the live client |
| Anthropic SDK `max_retries` | default **2**, plus ClaudeClient **MAX_RETRIES=3**, plus E.2 **MAX_API_ATTEMPTS=2** | Latent retry amplification if a call actually hung |
| HYBRID subprocess timeout | **7200 s** | Would not fire for this ~90 min run |
| Gunicorn `--timeout 3600` | Does not apply to the background estimate thread | Worker was not killed |
| UI | Stage label only; poll errors aborted the spinner | Looked stuck even while working |

---

## Ruling out other hypotheses

| Hypothesis | Verdict | Evidence |
|------------|---------|----------|
| A. Claude never returned | **No** | Claude not started at 45 min; later 143/143 success, avg 10.8 s |
| B. SDK retry loop | **No** for this incident | CPU 99.9% on PNG writes, not idle HTTP wait |
| C. Network/read hang | **No** | Process state `R`, wchan 0, newest files every ~18–25 s |
| D. One beam stall | **No** | Beams completing in order; no stuck file |
| E. Evidence generation | **Yes** | 3707 s W.8 render of 143 beams |
| F. D.2 hung | **No** | Shadow report written after Vision completed |
| G. File lock | **No** | Continuous writes |
| H. Gunicorn request timeout | **No** | POST returned immediately; polls 200 |
| I. Flask stuck after worker done | **No** | Worker still in Hybrid subprocess |
| J. Exception hidden from UI | **No** | No error; job remained `running` correctly |
| K. Worker blocked | **Partially** | Worker thread blocked on Hybrid subprocess, which was making progress |

---

## Reproduction

Reproduced **behaviourally**, not as an infinite hang:

- Controlled First Set (18 beams) after W.11: evidence ~97 s, Vision ~222 s, UI showed `Processing beam X of Y`.
- The original 143-beam drawing is expected to take ~1 hour of evidence + ~25 min Vision **even after W.11**. W.11 does not make crops faster.

Hanging-client timeout was reproduced in **local** TEST-W11-03 (bounded < 3 s), not by hanging production.

---

## Before / after

**Before:** 143-beam public run sat on one Hybrid label for ~45 minutes while W.8 rendered; estimators could not tell which beam was in progress; a true Claude hang could wait until the 7200 s subprocess cap.

**After:** Live `hybrid_progress.json` + status overlay (`Preparing visual evidence... Processing beam B16 (8 of 18)`). Per-call Anthropic timeout 120 s, SDK `max_retries=0`, app retries 1, per-beam budget 250 s, evidence budget 120 s/beam. Failed/timed-out beams fall back deterministically and the run continues.

---

## Blocking component

`PhaseW8_production_vision_evidence.package.prepare_production_evidence` → `build_beam_evidence` → P2.6.10-B.1 `render_crop`, invoked from W.6 `ensure_visuals` at the start of the Hybrid stage, **before** Claude.
