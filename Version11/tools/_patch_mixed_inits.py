from pathlib import Path

ROOT = Path(r"C:\Users\nishanth.h\SteelBeamEstimator\Version11\src")
PKGS = [
    "PhaseP2610C5_stratified_vision_semantic_benchmark",
    "PhaseP2610C3_visual_completeness_claude_shadow",
    "PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark",
    "PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark",
    "PhaseP2610B2_render_quality_directional_recovery",
    "PhaseP2610C1C2_evidence_inventory_candidate_selection",
    "PhaseP2610D1_vision_semantic_contract_hybrid_foundation",
    "PhaseP2610D2_shadow_hybrid_semantic_resolver",
    "PhaseP2610D3_hybrid_engineering_binding_compatibility",
    "PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark",
]
TEXT = '''"""V11 package init: do not import experimental orchestrators at import time.

Production code imports named submodules. Loading research orchestrators from
__init__ would pull excluded benchmark packages.
"""
from .config import GATE_VERSION, MODEL_VERSION, PHASE_ID, PHASE_NAME

__all__ = ["GATE_VERSION", "MODEL_VERSION", "PHASE_ID", "PHASE_NAME"]
'''
for pkg in PKGS:
    path = ROOT / pkg / "__init__.py"
    path.write_text(TEXT, encoding="utf-8")
    print("patched", pkg)
