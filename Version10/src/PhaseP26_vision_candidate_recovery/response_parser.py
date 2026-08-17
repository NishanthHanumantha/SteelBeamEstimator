"""Parse and validate Claude Vision JSON into candidate objects. Never guess."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseP253_claude_vision_interpretation_pilot.response_schema import (
    extract_json_object,
)

from .candidate_schema import normalize_candidate


def parse_vision_response(
    raw_text: Optional[str],
    *,
    beam_id: str,
    region_id: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Return (normalized_candidates, parse_report). Invalid fields become UNKNOWN/null."""
    report: Dict[str, Any] = {
        "ok": False,
        "error": None,
        "raw_candidate_count": 0,
        "normalized_count": 0,
    }
    if not raw_text or not str(raw_text).strip():
        report["error"] = "empty_response"
        return [], report
    obj, err = extract_json_object(str(raw_text))
    if obj is None:
        report["error"] = err or "json_parse_error"
        return [], report
    rows = obj.get("candidates")
    if rows is None:
        # Tolerate a single-object response that is itself a candidate.
        if any(k in obj for k in ("annotation_text", "candidate_type", "role")):
            rows = [obj]
        else:
            rows = []
    if not isinstance(rows, list):
        report["error"] = "candidates_not_list"
        return [], report
    report["raw_candidate_count"] = len(rows)
    out: List[Dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        cand = normalize_candidate(row, beam_id=beam_id, region_id=region_id, index=i)
        out.append(cand)
    report["ok"] = True
    report["normalized_count"] = len(out)
    report["returned_region_id"] = obj.get("region_id")
    report["returned_beam_id"] = obj.get("beam_id")
    return out, report


__all__ = ["extract_json_object", "parse_vision_response"]
