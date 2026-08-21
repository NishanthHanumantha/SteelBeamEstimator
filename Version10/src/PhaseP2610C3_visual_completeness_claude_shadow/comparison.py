"""Compare Claude groups to P2.6.9 / R1 / notes. Spec-only matching is forbidden."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import P269_OUTPUT_DIRNAME

_SPEC_RE = re.compile(r"[\s\-]")


def normalize_spec(spec: Any) -> str:
    s = str(spec or "").upper().strip()
    s = s.replace("–", "-").replace("—", "-")
    s = _SPEC_RE.sub("", s)
    return s


def group_identity(g: Dict[str, Any]) -> Tuple[str, str, str]:
    layer = str(g.get("layer") or g.get("physical_layer") or "UNKNOWN").upper()
    role = str(g.get("role") or g.get("reinforcement_role") or "UNKNOWN").upper()
    spec = normalize_spec(g.get("spec") or g.get("specification"))
    return (layer, role, spec)


def match_groups(predicted: List[Dict[str, Any]], expected: List[Dict[str, Any]]) -> Dict[str, Any]:
    exp_keys = [group_identity(g) for g in expected]
    pred_keys = [group_identity(g) for g in predicted]
    exp_set = set(exp_keys)
    pred_set = set(pred_keys)
    matched = sorted(exp_set & pred_set)
    missing = sorted(exp_set - pred_set)
    spurious = sorted(pred_set - exp_set)
    spec_only_collapse = 0
    for spec in {k[2] for k in exp_keys if k[2]}:
        e_n = len({k for k in exp_keys if k[2] == spec})
        p_n = len({k for k in pred_keys if k[2] == spec})
        if e_n > 1 and p_n == 1:
            spec_only_collapse += 1
    return {
        "expected_count": len(expected),
        "predicted_count": len(predicted),
        "matched": [{"layer": a, "role": b, "spec": c} for a, b, c in matched],
        "missing": [{"layer": a, "role": b, "spec": c} for a, b, c in missing],
        "spurious": [{"layer": a, "role": b, "spec": c} for a, b, c in spurious],
        "correctly_matched_count": len(matched),
        "missing_count": len(missing),
        "spurious_count": len(spurious),
        "merged_distinct_groups": spec_only_collapse,
        "identity_rule": "layer+role+specification",
    }


def _p269_inventory(v10: Path, set_key: str, beam_id: str) -> Optional[Dict[str, Any]]:
    path = Path(v10) / "data" / "output" / P269_OUTPUT_DIRNAME / "inventories" / f"{set_key}_{beam_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _reference_notes(v10: Path, set_key: str, beam_id: str) -> List[str]:
    path = Path(v10) / "src" / "PhaseP269_reinforcement_group_interpretation" / "fixtures" / "benchmark_reference.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data.get("beams") or []:
        if row.get("set_key") == set_key and row.get("beam_id") == beam_id:
            return list(row.get("discrepancy_notes") or [])
    return []


def compare_beam(
    *,
    v10: Path,
    set_key: str,
    beam_id: str,
    parsed: Dict[str, Any],
) -> Dict[str, Any]:
    inv = _p269_inventory(v10, set_key, beam_id)
    notes = _reference_notes(v10, set_key, beam_id)
    if inv is None:
        return {
            "taxonomy": "INSUFFICIENT_COMPARISON_EVIDENCE",
            "p269_expected": [],
            "deterministic": [],
            "notes": notes,
        }
    expected = list(inv.get("expected_groups") or [])
    detected = list(inv.get("detected_groups") or [])
    pred = list((parsed or {}).get("reinforcement_groups") or [])
    vs_p269 = match_groups(pred, expected)
    vs_det = match_groups(pred, detected)
    tax = "INSUFFICIENT_COMPARISON_EVIDENCE"
    if not parsed.get("usable"):
        tax = "INSUFFICIENT_COMPARISON_EVIDENCE"
    elif vs_p269["missing_count"] == 0 and vs_p269["spurious_count"] == 0 and vs_p269["expected_count"] > 0:
        tax = "VISION_MATCHES_P269_EXPECTED"
    elif vs_det["missing_count"] == 0 and vs_det["spurious_count"] == 0 and vs_det["expected_count"] > 0:
        tax = "VISION_MATCHES_R1"
    elif notes and vs_p269["correctly_matched_count"] > 0:
        tax = "VISION_DISAGREEMENT"
    elif vs_p269["correctly_matched_count"] == 0:
        tax = "VISION_DISAGREEMENT"
    else:
        tax = "VISION_DISAGREEMENT"
    if notes and tax == "VISION_MATCHES_P269_EXPECTED":
        # Keep provenance: DXF/P269 expected may still disagree with a phase sketch.
        pass
    return {
        "taxonomy": tax,
        "p269_expected": expected,
        "deterministic": detected,
        "manual_notes": notes,
        "vs_p269": vs_p269,
        "vs_deterministic": vs_det,
        "target_identified": bool(parsed.get("target_beam_identified")),
        "neighbor_evidence_detected": bool(parsed.get("neighbor_evidence_detected")),
    }


__all__ = ["compare_beam", "group_identity", "match_groups", "normalize_spec"]
