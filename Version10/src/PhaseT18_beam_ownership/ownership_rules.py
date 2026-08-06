"""
T1.8 — Explicit ownership rules for graph chains.
MODEL_VERSION: 9.5.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .beam_envelope import (
    bar_in_envelope,
    point_in_y_band,
    tip_in_envelope,
)

MODEL_VERSION = "9.5.0"

RULES = {
    "R1_PHYSICAL_BAR": "PhysicalBar centre inside Beam Envelope",
    "R2_LEADER_TIP": "Leader tip inside Envelope or support extension",
    "R3_ANNOTATION_VIA_CHAIN": "Annotation ownership only via Leader→Bar (or DESCRIBES bar)",
    "R4_SEMANTIC_VIA_ANN": "Semantic inherits only from Annotation",
    "R5_NEIGHBOUR_REJECT": "Reject chain if bar/leader resolves outside envelope",
    "R6_VERTICAL_OWNERSHIP": "PhysicalBar Y in beam reinforcement elevation",
    "R7_LD_SUPPORT_ONLY": "Ld may extend only via support extension",
    "R8_SIDE_FACE_WEB": "Side-face annotation intersects beam web Y",
    "R9_STIRRUP_REGION": "Stirrup annotation intersects stirrup region",
    "R10_CONFIDENCE": "Store ownership_reason / score / accepted_rule",
}


def _ann_attrs(node: Dict[str, Any]) -> Dict[str, Any]:
    return node.get("attributes") or {}


def _semantic_type_of(ann_node: Dict[str, Any], sem_node: Optional[Dict[str, Any]]) -> str:
    if sem_node:
        a = sem_node.get("attributes") or {}
        return str(a.get("semantic_type") or sem_node.get("type") or "Unknown")
    # fallback from text
    text = str(_ann_attrs(ann_node).get("clean_text") or "").upper()
    if "SIDE FACE" in text or "SIDE.FACE" in text:
        return "SideFaceReinforcement"
    if "LD" in text.split() or text.strip() == "LD":
        return "DevelopmentLength"
    if "@" in text and "L" in text.replace(" ", ""):
        return "StirrupNote"
    return "BarCallout"


def score_from_rules(accepted: List[str], rejected: Optional[str] = None) -> float:
    if rejected:
        return 0.0
    base = 0.55 + 0.05 * len(accepted)
    return round(min(1.0, base), 3)


def evaluate_physical_bar(
    bar_node: Dict[str, Any], envelope: Dict[str, Any]
) -> Dict[str, Any]:
    ok, reason = bar_in_envelope(bar_node.get("attributes") or {}, envelope)
    rules = ["R1_PHYSICAL_BAR", "R6_VERTICAL_OWNERSHIP"]
    if ok:
        return {
            "accepted": True,
            "accepted_rules": rules,
            "rejected_rule": None,
            "ownership_reason": reason,
            "ownership_score": score_from_rules(rules),
        }
    return {
        "accepted": False,
        "accepted_rules": [],
        "rejected_rule": "R5_NEIGHBOUR_REJECT" if "outside" in reason else "R1_PHYSICAL_BAR",
        "ownership_reason": reason,
        "ownership_score": 0.0,
    }


def evaluate_leader(
    leader_node: Dict[str, Any],
    envelope: Dict[str, Any],
    pointed_bar_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    a = leader_node.get("attributes") or {}
    try:
        tip_x, tip_y = float(a["tip_x"]), float(a["tip_y"])
    except Exception:
        return {
            "accepted": False,
            "accepted_rules": [],
            "rejected_rule": "R2_LEADER_TIP",
            "ownership_reason": "leader_missing_tip",
            "ownership_score": 0.0,
        }
    ok, reason = tip_in_envelope(tip_x, tip_y, envelope)
    if not ok:
        return {
            "accepted": False,
            "accepted_rules": [],
            "rejected_rule": "R2_LEADER_TIP",
            "ownership_reason": reason,
            "ownership_score": 0.0,
        }
    if pointed_bar_result is not None and not pointed_bar_result.get("accepted"):
        return {
            "accepted": False,
            "accepted_rules": ["R2_LEADER_TIP"],
            "rejected_rule": "R5_NEIGHBOUR_REJECT",
            "ownership_reason": "leader_points_to_non_owned_bar",
            "ownership_score": 0.0,
        }
    rules = ["R2_LEADER_TIP"]
    if pointed_bar_result and pointed_bar_result.get("accepted"):
        rules.append("R5_NEIGHBOUR_REJECT")  # passed neighbour check
    return {
        "accepted": True,
        "accepted_rules": rules,
        "rejected_rule": None,
        "ownership_reason": reason,
        "ownership_score": score_from_rules(rules),
    }


def evaluate_annotation_chain(
    ann_node: Dict[str, Any],
    envelope: Dict[str, Any],
    *,
    leader_result: Optional[Dict[str, Any]],
    bar_result: Optional[Dict[str, Any]],
    describes_owned_bar: bool,
    sem_node: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Rule 3: annotation ownership via Leader→Bar (or DESCRIBES owned bar).
    Rules 7/8/9: special geometric zones for Ld / SideFace / Stirrup.
    """
    attrs = _ann_attrs(ann_node)
    try:
        ax, ay = float(attrs["x"]), float(attrs["y"])
    except Exception:
        return {
            "accepted": False,
            "accepted_rules": [],
            "rejected_rule": "R3_ANNOTATION_VIA_CHAIN",
            "ownership_reason": "annotation_missing_xy",
            "ownership_score": 0.0,
        }

    sem_type = _semantic_type_of(ann_node, sem_node)
    reach = envelope["annotation_reach"]
    in_reach = point_in_y_band(ay, reach["y0"], reach["y1"], pad=40.0)

    # Special zone-based acceptance (still not crop-proximity: uses ownership envelope zones)
    if sem_type == "StirrupNote":
        sr = envelope["stirrup_region"]
        if point_in_y_band(ay, sr["y0"], sr["y1"], pad=80.0) or in_reach:
            # Reject if clearly on neighbour side of mark opposite body
            mark_y = envelope["centreline"]["y"]
            side = envelope["side_of_mark"]
            if side == "ABOVE_MARK" and ay < mark_y - 150:
                return _reject("R9_STIRRUP_REGION", "stirrup_on_neighbour_side_of_mark")
            if side == "BELOW_MARK" and ay > mark_y + 150:
                return _reject("R9_STIRRUP_REGION", "stirrup_on_neighbour_side_of_mark")
            return _accept(["R9_STIRRUP_REGION"], "stirrup_in_stirrup_region")

    if sem_type == "SideFaceReinforcement":
        web = envelope["side_face_web"]
        # Side-face notes often sit above the web; require reach + same side
        mark_y = envelope["centreline"]["y"]
        side = envelope["side_of_mark"]
        same_side = (side == "ABOVE_MARK" and ay >= mark_y - 80) or (
            side == "BELOW_MARK" and ay <= mark_y + 80
        )
        if same_side and in_reach:
            return _accept(
                ["R8_SIDE_FACE_WEB"],
                "side_face_same_side_in_annotation_reach",
            )
        if point_in_y_band(ay, web["y0"], web["y1"], pad=200.0) and same_side:
            return _accept(["R8_SIDE_FACE_WEB"], "side_face_near_web")
        return _reject("R8_SIDE_FACE_WEB", "side_face_no_web_intersection")

    if sem_type == "DevelopmentLength":
        # Ld must be in annotation reach OR support extension; never neighbour side
        mark_y = envelope["centreline"]["y"]
        side = envelope["side_of_mark"]
        if side == "ABOVE_MARK" and ay < mark_y - 100:
            return _reject("R7_LD_SUPPORT_ONLY", "ld_on_neighbour_side")
        if side == "BELOW_MARK" and ay > mark_y + 100:
            return _reject("R7_LD_SUPPORT_ONLY", "ld_on_neighbour_side")
        if in_reach:
            return _accept(["R7_LD_SUPPORT_ONLY"], "ld_in_annotation_reach")
        for z in envelope.get("support_zones") or []:
            if point_in_y_band(ay, z["y0"], z["y1"], pad=100.0):
                return _accept(["R7_LD_SUPPORT_ONLY"], "ld_in_support_extension")
        return _reject("R7_LD_SUPPORT_ONLY", "ld_outside_permitted_extension")

    # Longitudinal / other: require chain
    chain_ok = False
    reasons = []
    if leader_result and leader_result.get("accepted") and bar_result and bar_result.get("accepted"):
        chain_ok = True
        reasons.append("leader_bar_chain_owned")
    elif describes_owned_bar and in_reach:
        chain_ok = True
        reasons.append("describes_owned_bar_in_reach")
    elif (
        leader_result
        and leader_result.get("accepted")
        and in_reach
        and leader_result.get("ownership_reason")
        in ("tip_inside_concrete_envelope", "tip_inside_support_extension")
    ):
        # Tip owned geometrically even when POINTS_TO target lacks bar geom
        chain_ok = True
        reasons.append("leader_tip_owned_in_reach")

    if not chain_ok:
        # Explicit neighbour: annotation below/above mark opposite body
        mark_y = envelope["centreline"]["y"]
        side = envelope["side_of_mark"]
        if side == "ABOVE_MARK" and ay < mark_y - 50:
            return _reject("R5_NEIGHBOUR_REJECT", "annotation_on_neighbour_side_of_mark")
        if side == "BELOW_MARK" and ay > mark_y + 50:
            return _reject("R5_NEIGHBOUR_REJECT", "annotation_on_neighbour_side_of_mark")
        return _reject(
            "R3_ANNOTATION_VIA_CHAIN",
            "no_owned_leader_bar_chain",
        )

    if not in_reach and not (leader_result and leader_result.get("accepted")):
        return _reject("R5_NEIGHBOUR_REJECT", "annotation_outside_reach_without_leader")

    return _accept(
        ["R3_ANNOTATION_VIA_CHAIN", "R5_NEIGHBOUR_REJECT"],
        ";".join(reasons),
    )


def evaluate_semantic(
    sem_node: Dict[str, Any], ann_result: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    if ann_result and ann_result.get("accepted"):
        return _accept(["R4_SEMANTIC_VIA_ANN"], "semantic_inherits_annotation")
    return _reject("R4_SEMANTIC_VIA_ANN", "annotation_not_owned")


def _accept(rules: List[str], reason: str) -> Dict[str, Any]:
    return {
        "accepted": True,
        "accepted_rules": rules,
        "rejected_rule": None,
        "ownership_reason": reason,
        "ownership_score": score_from_rules(rules),
    }


def _reject(rule: str, reason: str) -> Dict[str, Any]:
    return {
        "accepted": False,
        "accepted_rules": [],
        "rejected_rule": rule,
        "ownership_reason": reason,
        "ownership_score": 0.0,
    }
