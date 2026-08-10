"""
B16 causal trace: leader -> ARR/LTGT -> annotation/bars -> R1.3 -> Excel.
MODEL_VERSION: 10.5.6
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import EXPECTED_MIGRATED_ENTITIES, MODEL_VERSION, PHASE_ID, REFERENCE_POSITIVE_KEY


def _load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_b16_trace(
    *,
    baseline_ownership: Dict[str, Any],
    controlled_ownership: Dict[str, Any],
    r13_models_path: Path,
    baseline_wb: Dict[str, Any],
    controlled_wb: Dict[str, Any],
    p23_propagation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    b_base = (baseline_ownership.get("by_beam") or {}).get("B16") or {}
    b_ctrl = (controlled_ownership.get("by_beam") or {}).get("B16") or {}
    base_ids = set(b_base.get("accepted_node_ids") or [])
    ctrl_ids = set(b_ctrl.get("accepted_node_ids") or [])

    stages: List[Dict[str, Any]] = []

    # 1 Leader
    stages.append(
        {
            "stage": "leader",
            "entity_id": "LDR::7A1FFD68",
            "baseline_owned": "LDR::7A1FFD68" in base_ids,
            "controlled_owned": "LDR::7A1FFD68" in ctrl_ids,
            "changed": ("LDR::7A1FFD68" not in base_ids)
            and ("LDR::7A1FFD68" in ctrl_ids),
        }
    )
    # 2 ARR / 3 LTGT
    for eid in ("ARR::4C3D2D29", "LTGT::LDR::7A1FFD68"):
        stages.append(
            {
                "stage": "graph_child",
                "entity_id": eid,
                "baseline_owned": eid in base_ids,
                "controlled_owned": eid in ctrl_ids,
                "changed": (eid not in base_ids) and (eid in ctrl_ids),
            }
        )

    # 4 Annotation / bars (known from P2.3)
    for eid, et in (
        ("ANN-62d4cbc2", "annotation"),
        ("BAR::SYN::B16::1213781", "physical_bar"),
        ("BAR::SYN::B16::11C88F6", "physical_bar"),
    ):
        stages.append(
            {
                "stage": et,
                "entity_id": eid,
                "baseline_owned": eid in base_ids,
                "controlled_owned": eid in ctrl_ids,
                "changed": (eid in base_ids) != (eid in ctrl_ids),
                "note": "Already T18-owned in P2.3 analysis"
                if eid in base_ids
                else None,
            }
        )

    # 5 R1.3 model
    r13 = _load(Path(r13_models_path)) or {}
    b16_model = None
    for m in r13.get("models") or []:
        if m.get("beam_id") == "B16":
            b16_model = m
            break
    model_blob = json.dumps(b16_model or {}, sort_keys=True)
    stages.append(
        {
            "stage": "r13_reinforcement_model",
            "entity_id": "B16",
            "model_present": b16_model is not None,
            "references_recovered_leader": "7A1FFD68" in model_blob,
            "references_ann_62d4": "62d4cbc2" in model_blob or "ANN-62d4" in model_blob,
            "total_classified_bars": (b16_model or {}).get("total_classified_bars"),
            "bar_count_by_role": (b16_model or {}).get("bar_count_by_role"),
            "changed_by_ownership": False,
            "note": (
                "R1.3 models are built before T18 ownership and do not reference "
                "LDR::7A1FFD68; ownership injection cannot alter this artefact."
            ),
        }
    )

    # 6 Excel
    b16_base = baseline_wb.get("b16") or {}
    b16_ctrl = controlled_wb.get("b16") or {}
    excel_changed = (
        b16_base.get("steel_kg") != b16_ctrl.get("steel_kg")
        or b16_base.get("bar_count") != b16_ctrl.get("bar_count")
        or baseline_wb.get("b16_bbs_row_count") != controlled_wb.get("b16_bbs_row_count")
    )
    stages.append(
        {
            "stage": "excel_steel",
            "entity_id": "B16",
            "baseline_steel_kg": b16_base.get("steel_kg"),
            "controlled_steel_kg": b16_ctrl.get("steel_kg"),
            "baseline_bar_count": b16_base.get("bar_count"),
            "controlled_bar_count": b16_ctrl.get("bar_count"),
            "baseline_bbs_rows": baseline_wb.get("b16_bbs_row_count"),
            "controlled_bbs_rows": controlled_wb.get("b16_bbs_row_count"),
            "changed": excel_changed,
        }
    )

    # Classify effect
    ownership_changed = any(
        s.get("changed") for s in stages if s["stage"] in ("leader", "graph_child")
    )
    association_changed = any(
        s.get("changed") for s in stages if s["stage"] in ("annotation", "physical_bar")
    )
    r13_changed = False
    quantity_changed = excel_changed

    if quantity_changed:
        effect = "E_changes_steel_quantity"
    elif association_changed:
        effect = "C_changes_reinforcement_interpretation"
    elif ownership_changed and not quantity_changed:
        effect = "A_changes_nothing_downstream_for_steel"
    else:
        effect = "A_changes_nothing_downstream_for_steel"

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "stable_key": REFERENCE_POSITIVE_KEY,
        "expected_migrated_entities": list(EXPECTED_MIGRATED_ENTITIES),
        "stages": stages,
        "effect_class": effect,
        "effect_meaning": {
            "A_changes_nothing_downstream_for_steel": (
                "Leader/ARR/LTGT ownership recovered, but annotation/bars already owned "
                "and R1.3/Excel unchanged — no steel quantity effect."
            ),
            "B_changes_engineering_association": "Association change detected",
            "C_changes_reinforcement_interpretation": "Reinforcement interpretation change",
            "D_changes_generated_pieces": "Piece generation change",
            "E_changes_steel_quantity": "Steel quantity change",
        }.get(effect),
        "p23_propagation": p23_propagation,
        "architectural_note": (
            "Production pipeline order: R1.3 -> VB1 Excel -> Track1/T18 ownership. "
            "Controlled BeamOwnership cannot feed Excel without a new ownership->R1.3 bridge."
        ),
    }
