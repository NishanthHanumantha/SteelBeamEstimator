"""Unit / golden tests for P2.5.1 Quantity Intent Schema."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    GOLDEN_B97A,
    ROLE_STIRRUP,
    ROLE_TOP_BAR,
    SEM_LONGITUDINAL_BAR,
    SEM_STIRRUP,
    STATUS_COMPOSITE,
    STATUS_EXPLICIT,
    STATUS_SPACING_BASED,
    STATUS_UNRESOLVED,
    VALIDATION_PASS,
)
from .intent_builder import build_intent_for_annotation, build_intents_for_beam
from .parser import parse_quantity_expression

MODEL_VERSION = "10.6.4"


def run_unit_tests() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        results.append({"name": name, "pass": bool(cond), "detail": detail})

    # Explicit longitudinal cases
    for text, qty, dia in [
        ("4-Y25", 4, 25),
        ("4-Y20", 4, 20),
        ("7-Y20", 7, 20),
        ("2-Y16", 2, 16),
        ("6-Y25", 6, 25),
        ("3-Y20", 3, 20),
    ]:
        r = parse_quantity_expression(text, chain_semantic_type="BarCallout")
        check(
            f"parse_{text}",
            r.quantity_status == STATUS_EXPLICIT
            and r.quantity_value == qty
            and r.diameter_value_mm == float(dia),
            str(r),
        )

    # Stirrup — not longitudinal quantity
    s = parse_quantity_expression("4L-Y8@100C/C", chain_semantic_type="StirrupNote")
    check(
        "stirrup_4L_Y8",
        s.quantity_status == STATUS_SPACING_BASED
        and s.leg_count == 4
        and s.diameter_value_mm == 8.0
        and s.spacing_value_mm == 100.0
        and s.quantity_value is None
        and s.semantic_hint == SEM_STIRRUP,
        str(s),
    )
    s2 = parse_quantity_expression(
        "4L-Y10@100/150/100C/C", chain_semantic_type="StirrupNote"
    )
    check(
        "stirrup_variable",
        s2.quantity_status == STATUS_SPACING_BASED
        and s2.leg_count == 4
        and s2.diameter_value_mm == 10.0
        and s2.spacing_values_mm == [100.0, 150.0, 100.0]
        and s2.quantity_value is None,
        str(s2),
    )

    # Composite
    c = parse_quantity_expression("4-Y20 + 2-Y16", chain_semantic_type="BarCallout")
    check(
        "composite",
        c.quantity_status == STATUS_COMPOSITE
        and c.quantity_value is None
        and len(c.components) == 2
        and c.components[0].quantity_value == 4
        and c.components[1].quantity_value == 2,
        str(c),
    )

    # Ambiguous
    a = parse_quantity_expression("4/6-Y20", chain_semantic_type="BarCallout")
    check(
        "ambiguous",
        a.quantity_status == STATUS_UNRESOLVED
        and a.ambiguous
        and a.quantity_value is None,
        str(a),
    )

    # Missing / empty
    e = parse_quantity_expression("", chain_semantic_type="BarCallout")
    check("missing_quantity", e.quantity_status == STATUS_UNRESOLVED)

    # Rejected annotation → no intent
    evidence_rej = {
        "beam_id": "BX",
        "annotations": [],
        "leader_chains": {
            "accepted": [],
            "rejected": [{"annotation_id": "ANN-rej", "text": "4-Y20"}],
        },
        "owned_geometry": [],
        "excluded_rejected_evidence": {"bars": ["BAR::X"], "leaders": []},
    }
    rej = build_intent_for_annotation(
        beam_id="BX",
        annotation={"annotation_id": "ANN-rej", "raw_text": "4-Y20"},
        evidence=evidence_rej,
    )
    check("rejected_annotation_excluded", rej is None)

    # Accepted without OWN — still valid intent, role UNKNOWN
    evidence_plain = {
        "beam_id": "B1",
        "annotations": [{"annotation_id": "ANN-1", "raw_text": "3-Y20"}],
        "leader_chains": {
            "accepted": [
                {
                    "annotation_id": "ANN-1",
                    "text": "3-Y20",
                    "semantic_type": "BarCallout",
                    "leaders": ["LDR::1"],
                    "describes": [],
                }
            ],
            "rejected": [],
        },
        "owned_geometry": [],
    }
    plain = build_intent_for_annotation(
        beam_id="B1",
        annotation={"annotation_id": "ANN-1", "raw_text": "3-Y20"},
        evidence=evidence_plain,
    )
    check(
        "accepted_without_own",
        plain is not None
        and plain.quantity_value == 3
        and plain.reinforcement_role != ROLE_TOP_BAR
        and plain.validation_status in (VALIDATION_PASS, "PARTIAL"),
        str(plain.to_dict() if plain else None),
    )

    # B97A golden with OWN
    evidence_b97 = {
        "beam_id": "B97A",
        "phase_id": "P2.5.0",
        "annotations": [
            {"annotation_id": GOLDEN_B97A["annotation_id"], "raw_text": "4-Y25"},
            {"annotation_id": "ANN-d86396b9", "raw_text": "4L-Y8@100C/C"},
        ],
        "leader_chains": {
            "accepted": [
                {
                    "annotation_id": GOLDEN_B97A["annotation_id"],
                    "text": "4-Y25",
                    "semantic_type": "BarCallout",
                    "leaders": [GOLDEN_B97A["leader_id"]],
                    "describes": [GOLDEN_B97A["ownership_id"]],
                },
                {
                    "annotation_id": "ANN-d86396b9",
                    "text": "4L-Y8@100C/C",
                    "semantic_type": "StirrupNote",
                    "leaders": [GOLDEN_B97A["leader_id"]],
                    "describes": [],
                },
            ],
            "rejected": [],
        },
        "owned_geometry": [
            {
                "evidence_id": "OWNGEO::B97A::1247FFF",
                "ownership_id": GOLDEN_B97A["ownership_id"],
                "source_handle": "1247FFF",
                "annotation_id": GOLDEN_B97A["annotation_id"],
                "leader_id": GOLDEN_B97A["leader_id"],
                "annotation_text": "4-Y25",
                "semantic_role": "TOP_BAR",
                "evidence_type": "OWN_TOP_BAR",
                "accepted": True,
            }
        ],
        "excluded_rejected_evidence": {
            "bars": ["BAR::2B7B3233", "BAR::5B1BFCC2"],
            "leaders": [],
        },
    }
    intents = build_intents_for_beam(evidence_b97)
    b97 = next(
        (i for i in intents if i.annotation_id == GOLDEN_B97A["annotation_id"]), None
    )
    check(
        "b97a_4y25",
        b97 is not None
        and b97.quantity_value == 4
        and b97.diameter_value_mm == 25.0
        and b97.semantic_type == SEM_LONGITUDINAL_BAR
        and b97.reinforcement_role == ROLE_TOP_BAR
        and b97.quantity_status == STATUS_EXPLICIT
        and b97.evidence_links is not None
        and b97.evidence_links.leader_id == GOLDEN_B97A["leader_id"]
        and b97.evidence_links.ownership_id == GOLDEN_B97A["ownership_id"]
        and b97.validation_status == VALIDATION_PASS,
        str(b97.to_dict() if b97 else None),
    )
    stirrup_i = next((i for i in intents if i.annotation_id == "ANN-d86396b9"), None)
    check(
        "b97a_stirrup_not_longitudinal",
        stirrup_i is not None
        and stirrup_i.semantic_type == SEM_STIRRUP
        and stirrup_i.reinforcement_role == ROLE_STIRRUP
        and stirrup_i.leg_count == 4
        and stirrup_i.quantity_value is None,
        str(stirrup_i.to_dict() if stirrup_i else None),
    )

    # Deterministic IDs
    intents2 = build_intents_for_beam(evidence_b97)
    check(
        "deterministic_ids",
        [i.intent_id for i in intents] == [i.intent_id for i in intents2],
    )

    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "model_version": MODEL_VERSION,
    }
