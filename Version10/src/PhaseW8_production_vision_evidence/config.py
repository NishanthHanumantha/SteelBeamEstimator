"""
P W.8 — P2.6.10 vision evidence adapter for production Hybrid.

Promotes proven B.1 context/detail rendering and C1–C2 selection into the
existing W.6/W.7 Hybrid path. Does not rebuild E.2, D.2, VB.1, BBS, or Excel.
"""
from __future__ import annotations

MODEL_VERSION = "10.0.0"
PHASE_ID = "W.8"
PHASE_NAME = "P2.6.10 Vision Crop Pipeline Production Integration"
GATE_VERSION = "W8_P2610_VISION_EVIDENCE_V1"

OUTPUT_DIRNAME = "PhaseW6_hybrid_semantic_resolution"
EVIDENCE_REL = f"data/output/{OUTPUT_DIRNAME}/hybrid_evidence"

SOURCE_P2610_PRIMARY = "P2610B1_ADAPTIVE_CONTEXT_DETAIL"
SOURCE_W6_COMPAT = "W6_ENVELOPE_RENDER"
SOURCE_T1_COMPAT = "T1_OPENCV_CROP"
SOURCE_MIXED = "W8_SELECTED_MIXED"

CLASS_PRIMARY = "PRIMARY"
CLASS_COMPATIBILITY = "COMPATIBILITY"
CLASS_FALLBACK = "FALLBACK"
CLASS_UNAVAILABLE = "UNAVAILABLE"

STATUS_EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"

MIN_RENDER_BYTES = 200

# C.5 / E.2 Claude request contract: exactly one context + one detail image.
CLAUDE_CONTEXT_IMAGES = 1
CLAUDE_DETAIL_IMAGES = 1
MULTIPLE_DETAIL_IN_CLAUDE_REQUEST = False

# W.6 envelope renderer role after W.8.
W6_ADAPTER_ROLE = "FALLBACK"
T1_ADAPTER_ROLE = "COMPATIBILITY"

# TEST-W8-02 inventory. Source modules, not data/output trees.
COMPONENT_INVENTORY = [
    {
        "phase": "P2.6.10-A",
        "module": "PhaseP2610A_beam_region_crop_audit/title_localizer.py",
        "role": "Beam title localization (choose_mark, collect_beam_titles)",
        "classification": "PRODUCTION_READY",
    },
    {
        "phase": "P2.6.10-A",
        "module": "PhaseP2610A_beam_region_crop_audit/region_builder.py",
        "role": "Context envelope from title + outline",
        "classification": "PRODUCTION_READY",
    },
    {
        "phase": "P2.6.10-A",
        "module": "PhaseP2610A_beam_region_crop_audit/cropper.py",
        "role": "M.1 region render with context/detail max_px",
        "classification": "PRODUCTION_READY",
    },
    {
        "phase": "P2.6.10-A",
        "module": "PhaseP2610A_beam_region_crop_audit/phase_p2610a_orchestrator.py",
        "role": "Fourth/Fifth audit orchestrator",
        "classification": "RESEARCH_ONLY",
    },
    {
        "phase": "P2.6.10-B",
        "module": "PhaseP2610B_adaptive_beam_detail_crop/envelope.py",
        "role": "Adaptive detail extent (build_adaptive_regions)",
        "classification": "PRODUCTION_READY",
    },
    {
        "phase": "P2.6.10-B",
        "module": "PhaseP2610B_adaptive_beam_detail_crop/completeness.py",
        "role": "Spatial completeness of adaptive extent",
        "classification": "REUSABLE_WITH_ADAPTER",
    },
    {
        "phase": "P2.6.10-B",
        "module": "PhaseP2610B_adaptive_beam_detail_crop/evidence.py",
        "role": "DXF text/dimension spatial evidence",
        "classification": "PRODUCTION_READY",
    },
    {
        "phase": "P2.6.10-B.1",
        "module": "PhaseP2610B1_population_generalization/phase_p2610b1_orchestrator.py",
        "role": "Fourth-set population crop loop (shared data/output)",
        "classification": "RESEARCH_ONLY",
    },
    {
        "phase": "P2.6.10-B.2",
        "module": "PhaseP2610B2_render_quality_directional_recovery/quality.py",
        "role": "validate_render PNG quality",
        "classification": "PRODUCTION_READY",
    },
    {
        "phase": "P2.6.10-B.2",
        "module": "PhaseP2610B2_render_quality_directional_recovery/recovery.py",
        "role": "Directional challenger crop recovery loop",
        "classification": "RESEARCH_ONLY",
    },
    {
        "phase": "P2.6.10-B.3",
        "module": "PhaseP2610B3_target_anchor_geometry_context_recovery",
        "role": "Target-anchor recovery challengers",
        "classification": "RESEARCH_ONLY",
    },
    {
        "phase": "P2.6.10-C.1+C.2",
        "module": "PhaseP2610C1C2_evidence_inventory_candidate_selection/selector.py",
        "role": "Preference-preserving context/detail selection",
        "classification": "PRODUCTION_READY",
    },
    {
        "phase": "P2.6.10-C.1+C.2",
        "module": "PhaseP2610C1C2_evidence_inventory_candidate_selection/inventory.py",
        "role": "Candidate scoring via validate_render; B.1/B.2/B.3 path discovery is research",
        "classification": "REUSABLE_WITH_ADAPTER",
    },
    {
        "phase": "P2.6.10-C.1+C.2",
        "module": "PhaseP2610C1C2_evidence_inventory_candidate_selection/phase_p2610c1c2_orchestrator.py",
        "role": "Fourth-set shadow inventory over shared data/output",
        "classification": "RESEARCH_ONLY",
    },
    {
        "phase": "P2.6.10-C.3",
        "module": "PhaseP2610C3_visual_completeness_claude_shadow/visual_completeness_gate.py",
        "role": "Vision-readiness gate on selected context+detail",
        "classification": "REUSABLE_WITH_ADAPTER",
    },
    {
        "phase": "P2.6.10-C.3",
        "module": "PhaseP2610C3_visual_completeness_claude_shadow/evidence_model.py",
        "role": "SelectedRender typed objects",
        "classification": "REUSABLE_WITH_ADAPTER",
    },
    {
        "phase": "P2.6.10-C.3",
        "module": "PhaseP2610C3_visual_completeness_claude_shadow/phase_p2610c3_orchestrator.py",
        "role": "Six-beam Claude shadow benchmark",
        "classification": "RESEARCH_ONLY",
    },
    {
        "phase": "P2.6.10-C.4",
        "module": "PhaseP2610C4_shadow_truth_reconciliation",
        "role": "Shadow vs truth calibration",
        "classification": "RESEARCH_ONLY",
    },
    {
        "phase": "P2.6.10-C.5",
        "module": "PhaseP2610C5_stratified_vision_semantic_benchmark/claude_call.py",
        "role": "Claude request: 1 context + 1 detail (already used by E.2)",
        "classification": "PRODUCTION_READY",
    },
    {
        "phase": "P2.6.10-C.5",
        "module": "PhaseP2610C5_stratified_vision_semantic_benchmark/vision_contract.py",
        "role": "Vision JSON contract (already used by E.2)",
        "classification": "PRODUCTION_READY",
    },
    {
        "phase": "P2.6.10-C.5",
        "module": "PhaseP2610C5_stratified_vision_semantic_benchmark/sampler.py",
        "role": "Fourth-set stratified sampler",
        "classification": "RESEARCH_ONLY",
    },
    {
        "phase": "P2.6.10-C.1–C.5",
        "module": "data/output/PhaseP2610C*",
        "role": "Benchmark artefacts (review PNGs, JSON, reports)",
        "classification": "OUTPUT_ONLY",
    },
    {
        "phase": "W.6",
        "module": "PhaseW6_hybrid_production_authority/visuals.py",
        "role": "T1.5 envelope + M.1 single-crop renderer",
        "classification": "REUSABLE_WITH_ADAPTER",
        "production_role": W6_ADAPTER_ROLE,
    },
]
