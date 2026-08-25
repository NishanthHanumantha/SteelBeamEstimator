# PHASE W.8 — P2.6.10 CROP PIPELINE INVENTORY

Prepared: 2026-08-25  
Scope: source implementation of P2.6.10 C1–C5 (and the B/A generators they consume), not `data/output` artefacts.

## Finding

C1–C5 do **not** generate production crops. They inventory, select, gate, and benchmark **already-rendered** B.1/B.2/B.3 PNGs.

The proven crop **generator** is P2.6.10-A + B + B.1:

1. Title localization (`choose_mark` / `collect_beam_titles`)
2. Adaptive context + detail extents (`build_adaptive_regions`)
3. M.1 `render_dxf_region_to_png` with distinct `max_px` (`render_crop`)
4. Quality (`validate_render`) and C3 visual completeness gate
5. C1C2 preference-preserving selection when a challenger exists

W.8 promotes those **functions** into the existing W.6/W.7 Hybrid path. It does not run Fourth-set research orchestrators and does not write shared `data/output/PhaseP2610*`.

Claude request contract (C.5, already used by E.2): **exactly one context image + one detail image**. Multiple selected detail regions are not in the production Vision payload.

## C1–C5 implementation map

| Phase | Source module | Role | Classification |
|---|---|---|---|
| A | `PhaseP2610A_beam_region_crop_audit/title_localizer.py` | Beam title localization | PRODUCTION_READY |
| A | `PhaseP2610A_beam_region_crop_audit/region_builder.py` | Context envelope | PRODUCTION_READY |
| A | `PhaseP2610A_beam_region_crop_audit/cropper.py` | M.1 region render | PRODUCTION_READY |
| A | `phase_p2610a_orchestrator.py` | Fourth/Fifth audit loop | RESEARCH_ONLY |
| B | `PhaseP2610B_adaptive_beam_detail_crop/envelope.py` | Adaptive detail extent | PRODUCTION_READY |
| B | `completeness.py` | Spatial completeness of extent | REUSABLE_WITH_ADAPTER |
| B | `evidence.py` | DXF text/dimension evidence | PRODUCTION_READY |
| B.1 | `phase_p2610b1_orchestrator.py` | Fourth-set population crop loop | RESEARCH_ONLY |
| B.2 | `quality.py` (`validate_render`) | PNG quality | PRODUCTION_READY |
| B.2 | directional recovery loop | Challenger crops | RESEARCH_ONLY |
| B.3 | target-anchor recovery | Challenger crops | RESEARCH_ONLY |
| C.1+C.2 | `selector.py` | Preference-preserving selection | PRODUCTION_READY |
| C.1+C.2 | `inventory.py` | Candidate scoring; B.1/B.2/B.3 path discovery | REUSABLE_WITH_ADAPTER |
| C.1+C.2 | `phase_p2610c1c2_orchestrator.py` | Fourth-set shadow inventory | RESEARCH_ONLY |
| C.3 | `visual_completeness_gate.py` | Vision-readiness on selected pair | REUSABLE_WITH_ADAPTER |
| C.3 | `evidence_model.py` | SelectedRender | REUSABLE_WITH_ADAPTER |
| C.3 | C.3 orchestrator / six-beam Claude shadow | Benchmark | RESEARCH_ONLY |
| C.4 | `PhaseP2610C4_shadow_truth_reconciliation` | Shadow vs truth calibration | RESEARCH_ONLY |
| C.5 | `claude_call.py`, `vision_contract.py`, `vision_prompt.py` | Claude request (already E.2) | PRODUCTION_READY |
| C.5 | sampler / strata / Fourth-set discovery | Benchmark | RESEARCH_ONLY |
| C1–C5 | `data/output/PhaseP2610C*` | Review PNGs, JSON, reports | OUTPUT_ONLY |

`COMPONENT_INVENTORY` in `PhaseW8_production_vision_evidence/config.py` is the machine-readable copy (TEST-W8-02).

## What W.8 integrated

| Component | Production use |
|---|---|
| A title + region + cropper | PRIMARY generator per web run |
| B adaptive envelope + completeness | PRIMARY generator |
| B.2 `validate_render` | Quality / critical-failure gate |
| C1C2 `select_for_type` | Choose B.1 vs W.6/T1 challenger |
| C.3 completeness gate | Block empty/black/low-info pairs |
| C.5 / E.2 `call_selected_beam` | Unchanged Claude client |
| D.2 resolver, W.6 handoff, VB.1 | Unchanged |

## What remains unused (intentionally)

- B.2/B.3 recovery loops (Fourth-set research, slow, shared `data/output`)
- C1C2/C3/C4/C5 orchestrators, samplers, truth reconciliation
- Population lists from B.1 `validation/*.json` (production beams come from R13)

## Production recommendation

PRIMARY path: P2.6.10-B.1-style context + detail under the run tree.

W.6 T1.5 envelope + M.1 single crop: **FALLBACK** only, never silent.

T1 OpenCV crop: **COMPATIBILITY** only when P2.6.10 primary is unavailable.

W.8 adapter: `Version10/src/PhaseW8_production_vision_evidence/`.
