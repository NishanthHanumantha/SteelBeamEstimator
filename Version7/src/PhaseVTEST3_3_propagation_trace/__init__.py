"""
Phase V.TEST.3.3 — Reinforcement Propagation Trace & Root Cause Engine
MODEL_VERSION: 8.1.4

READ-ONLY forensic trace. No production code modified.
"""

MODEL_VERSION = "8.1.4"
PHASE_ID = "V.TEST.3.3"

STAGE_ORDER = [
    "AnnotationDiscovery",
    "SemanticInterpretation",
    "EngineeringFactNormalization",
    "IntentHypothesis",
    "GeometryContext",
    "DrawingRelationship",
    "ReinforcementGroupBuilder",
    "EngineeringBarBuilder",
    "SteelWeightCompletion",
    "BBSCompletionEngine",
    "ExcelWorkbook",
]

FILTER_POINTS = [
    {
        "module": "PhaseR.1_generalized_reinforcement_discovery.annotation_discovery",
        "class": "AnnotationDiscovery",
        "function": "_parse_text",
        "condition": "Text matches beam label regex ^B\\d+ → return []",
        "reason": "Beam mark text skipped as annotation",
    },
    {
        "module": "PhaseR.1_generalized_reinforcement_discovery.annotation_discovery",
        "class": "AnnotationDiscovery",
        "function": "_parse_text",
        "condition": "is_reinforcement=False",
        "reason": "Unrecognized notation stored but excluded from groups",
    },
    {
        "module": "PhaseR.1_generalized_reinforcement_discovery.reinforcement_group_builder",
        "class": "ReinforcementGroupBuilder",
        "function": "build",
        "condition": "if not ann.is_reinforcement: skip role_map",
        "reason": "Non-reinforcement annotations excluded from groups",
    },
    {
        "module": "PhaseR.1_generalized_reinforcement_discovery.beam_detail_segmenter",
        "class": "BeamDetailSegmenter",
        "function": "segment",
        "condition": "Entity outside detail radius",
        "reason": "DXF entity rejected before annotation discovery",
    },
    {
        "module": "PhaseR1.3_pipeline_integration.engineering_bar_builder",
        "class": "EngineeringBarBuilder",
        "function": "_expand_group",
        "condition": "if not diameters or total_qty == 0: return []",
        "reason": "Empty R.1 group produces no EngineeringBarModel bars",
    },
    {
        "module": "PhaseR1.3_pipeline_integration.engineering_bar_builder",
        "class": "EngineeringBarBuilder",
        "function": "build_all",
        "condition": "Beam with zero expanded bars → empty_beam_ids",
        "reason": "Beam recorded as EMPTY_NO_REINFORCEMENT in propagation matrix",
    },
    {
        "module": "PhaseR1.3_pipeline_integration.reinforcement_pipeline_adapter",
        "class": "ReinforcementPipelineAdapter",
        "function": "load_and_convert",
        "condition": "Input is R.1 beam_reinforcement_models.json only",
        "reason": "R.2.1B–R.3.1 interpretation outputs not consumed by production path",
    },
]
