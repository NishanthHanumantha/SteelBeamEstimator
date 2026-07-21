"""
Deterministic engineering recommendations per issue.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from typing import Dict, Tuple

MODEL_VERSION = "8.7.0"

_RECOMMENDATIONS: Dict[str, Tuple[str, str]] = {
    # category -> (fix template, root cause)
    "Beam Discovery": (
        "Improve beam-mark discovery coverage so every official beam mark is emitted from annotation discovery.",
        "Official beam marks are not fully discovered or propagated into the production beam set.",
    ),
    "Annotation Association": (
        "Tighten beam-ID filtering to suppress spurious / unmatched production beam identifiers.",
        "Production emits beam IDs not present in the official engineering model.",
    ),
    "Role Classification": (
        "Strengthen intent role resolution for main/extra bar families against official terminology.",
        "Official reinforcement roles are missing or misclassified in the intent/detail path.",
    ),
    "Diameter Interpretation": (
        "Trace and correct diameter resolution from annotation labels through intent and detail.",
        "Diameter assignment disagrees with official diameter-wise steel buckets.",
    ),
    "Quantity Interpretation": (
        "Validate bar counts and spacing interpretation against official breakup quantities.",
        "Quantity interpretation diverges from official No./Dia. and spacing fields.",
    ),
    "Development Length": (
        "Recalibrate development-length rules against official D/Dvlp values.",
        "Development length detailing differs from official estimator values.",
    ),
    "Cut Length": (
        "Improve piece cut-length formulas and support/zone length allocation.",
        "Manufacturing cut lengths diverge from official cutting lengths.",
    ),
    "Support Zone Interpretation": (
        "Improve support-zone interpretation for extras and curtailment extents.",
        "Support-zone extents are incomplete or incorrect relative to official extras.",
    ),
    "Curtailment": (
        "Align curtailment logic with official extra-bar extents.",
        "Curtailment decisions do not match official extra reinforcement extents.",
    ),
    "Continuity": (
        "Review continuity flags for continuous main bars versus curtailed extras.",
        "Continuity classification diverges from official continuous/curtailed intent.",
    ),
    "Stirrup Interpretation": (
        "Improve stirrup / multi-zone stirrup interpretation and spacing-pattern capture.",
        "Official stirrup rows are missing or under-represented in production.",
    ),
    "Hook Interpretation": (
        "Improve C-Hook / stirrup-hook detailing and pairing with stirrup zones.",
        "Official hook rows are missing or incorrectly paired with stirrups.",
    ),
    "Spacer Interpretation": (
        "Ensure spacer-bar intents are retained through detail and piece generation.",
        "Official spacer bars are dropped or under-counted in production.",
    ),
    "Side Face Reinforcement": (
        "Improve SFR / side-face detection thresholds and depth triggers.",
        "Official side-face reinforcement is missing for deep beams.",
    ),
    "Piece Generation": (
        "Align piece-type expansion with official reinforcement families.",
        "Piece generation produces incorrect or incomplete manufacturing members.",
    ),
    "Steel Aggregation": (
        "Audit steel aggregation so all EngineeringBars reach diameter and project totals.",
        "Project steel totals diverge materially from the official steel summary.",
    ),
    "Weight Calculation": (
        "Reconcile unit weights and length×quantity aggregation with official kg totals.",
        "Weight calculation does not reproduce official steel weight.",
    ),
    "Workbook Export": (
        "Confirm workbook export completeness for beams, BBS rows, and steel totals.",
        "Production workbook output is incomplete or missing.",
    ),
    "Unknown": (
        "Inspect full pipeline trace for unclassified benchmark findings.",
        "Findings could not be mapped to a specific engineering category.",
    ),
}


class RecommendationEngine:
    def recommend(
        self,
        category: str,
        subcategory: str,
        originating_phase: str,
        production_accuracy_loss: float,
        priority: str,
        confidence: float,
        finding_fix_hints: Tuple[str, ...] = (),
    ) -> Dict[str, object]:
        fix, root = _RECOMMENDATIONS.get(category, _RECOMMENDATIONS["Unknown"])
        if subcategory and subcategory not in ("Missing Beam", "Extra Beam") and category in (
            "Stirrup Interpretation", "Hook Interpretation", "Spacer Interpretation",
            "Side Face Reinforcement", "Role Classification",
        ):
            fix = f"{fix} Focus family: {subcategory}."
        # expected gain ≈ attributed accuracy loss (as percent points of overall)
        expected_gain = round(production_accuracy_loss * 100.0, 2)
        if finding_fix_hints:
            # keep deterministic: use first hint as evidence note only
            pass
        return {
            "recommended_fix": fix,
            "root_cause": root,
            "recommended_phase": originating_phase,
            "expected_accuracy_gain": expected_gain,
            "priority": priority,
            "confidence": confidence,
        }
