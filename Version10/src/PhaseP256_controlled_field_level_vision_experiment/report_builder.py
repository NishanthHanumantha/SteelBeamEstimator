"""P2.5.6 STATUS + evaluation artefacts."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ENGINEERING_CHANGES, FIELDS, MODEL_VERSION, PHASE_ID, PHASE_NAME


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _fmt(v: Any) -> str:
    if v is None:
        return "N/A"
    return str(v)


def _pick(rows: List[Dict[str, Any]], cid: str) -> Dict[str, Any]:
    for r in rows:
        if (r.get("field_result") or {}).get("candidate_id") == cid:
            return r.get("field_result") or {}
    return {}


def _field_lines(fr: Dict[str, Any]) -> List[str]:
    comps = fr.get("field_comparisons") or {}
    lines = []
    for f in FIELDS:
        rec = comps.get(f) or {}
        lines.append(
            f"  - {f}: det={rec.get('deterministic_value')!r} vis={rec.get('vision_value')!r} "
            f"status={rec.get('field_status')} accepted={rec.get('accepted')} reason={rec.get('reason')}"
        )
    return lines


def write_reports(
    *,
    out_root: Path,
    summary: Dict[str, Any],
    rows: List[Dict[str, Any]],
) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    evaluation = out_root / "evaluation"
    evaluation.mkdir(parents=True, exist_ok=True)
    m = summary.get("metrics") or {}
    by = m.get("by_field") or {}

    b46 = _pick(rows, "VC::B46::ANN-a09ab748")
    b58 = _pick(rows, "VC::B58::ANN-a0c82bbe")
    b120 = _pick(rows, "VC::B120::ANN-f4213b73")

    field_metric_lines = []
    for f in FIELDS:
        rec = by.get(f) or {}
        field_metric_lines.append(
            f"- {f}: det_known={rec.get('deterministic_known_count')} "
            f"det_unknown={rec.get('deterministic_unknown_count')} "
            f"vis_known={rec.get('vision_known_count')} vis_unknown={rec.get('vision_unknown_count')} "
            f"BOTH_AGREE={rec.get('BOTH_AGREE')} VISION_ONLY_CANDIDATE={rec.get('VISION_ONLY_CANDIDATE')} "
            f"DET_ONLY={rec.get('DETERMINISTIC_ONLY')} CONFLICT={rec.get('CONFLICT')} "
            f"UNRESOLVED={rec.get('UNRESOLVED')} REJECTED={rec.get('VISION_REJECTED')}"
        )

    lines = [
        "# P2.5.6 STATUS",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"PASS / FAIL: {summary.get('pass_fail')}",
        f"SCOPE: {summary.get('scope')}",
        "MODE: SHADOW FIELD EXPERIMENT ONLY — NO PRODUCTION PROMOTION",
        "CLAUDE: SHADOW OBSERVER (not engineering authority)",
        f"Execution mode: {summary.get('vision_source')}",
        f"Candidate count: {summary.get('candidate_count')}",
        f"Claude calls: {(m.get('claude_calls'))} (live={m.get('claude_calls_live')} replayed={m.get('claude_calls_replayed')})",
        "",
        "## Deterministic status",
        "- Authority: P2.5.1 QuantityIntent (immutable snapshot)",
        f"- P2.5.1 fingerprint unchanged: {(summary.get('regression') or {}).get('p251_unchanged')}",
        "",
        "## Field-level metrics",
        *field_metric_lines,
        "",
        f"- Accepted Vision field candidates: {m.get('accepted_vision_field_candidates')}",
        f"- Rejected Vision fields: {m.get('rejected_vision_fields')}",
        f"- Field conflicts: {m.get('conflicting_vision_fields')}",
        f"- SAFE_FIELD_CANDIDATE_RATE: {_fmt(m.get('SAFE_FIELD_CANDIDATE_RATE'))}",
        f"- FIELD_CONFLICT_RATE: {_fmt(m.get('FIELD_CONFLICT_RATE'))}",
        f"- FIELD_REJECTION_RATE: {_fmt(m.get('FIELD_REJECTION_RATE'))}",
        f"- FIELD_VALIDATION_PASS_RATE: {_fmt(m.get('FIELD_VALIDATION_PASS_RATE'))}",
        "",
        "## B46 result",
        f"- candidate_id: {b46.get('candidate_id')}",
        f"- text: {b46.get('annotation_text')}",
        f"- accepted_shadow_fields: {b46.get('accepted_shadow_fields')}",
        f"- rejected_shadow_fields: {b46.get('rejected_shadow_fields')}",
        f"- conflict_fields: {b46.get('conflict_fields')}",
        f"- decision: {b46.get('final_shadow_decision')}",
        *_field_lines(b46),
        "",
        "## B58 result",
        f"- candidate_id: {b58.get('candidate_id')}",
        f"- text: {b58.get('annotation_text')}",
        f"- accepted_shadow_fields: {b58.get('accepted_shadow_fields')}",
        f"- rejected_shadow_fields: {b58.get('rejected_shadow_fields')}",
        f"- conflict_fields: {b58.get('conflict_fields')}",
        f"- decision: {b58.get('final_shadow_decision')}",
        *_field_lines(b58),
        "",
        "## B120 result",
        f"- candidate_id: {b120.get('candidate_id')}",
        f"- text: {b120.get('annotation_text')}",
        f"- accepted_shadow_fields: {b120.get('accepted_shadow_fields')}",
        f"- rejected_shadow_fields: {b120.get('rejected_shadow_fields')}",
        f"- conflict_fields: {b120.get('conflict_fields')}",
        f"- decision: {b120.get('final_shadow_decision')}",
        *_field_lines(b120),
        "",
        "## Zone status",
        "- zone_promotable = false",
        "- zone_candidate_allowed = false",
        "- Zone remains diagnostic only",
        "",
        "## Safety / production mutation",
        f"- Production mutation: {m.get('production_mutation_count')}",
        f"- Steel difference: {m.get('steel_quantity_differences')}",
        f"- BBS difference: {m.get('bbs_differences')}",
        f"- Excel difference: {m.get('excel_differences')}",
        "",
        "## Regression",
        f"- P2.5.4 regression: {(summary.get('regression') or {}).get('p254_unchanged')}",
        f"- P2.5.5 regression: {(summary.get('regression') or {}).get('p255_unchanged')}",
        f"- P2.5.1 fingerprint: {(summary.get('regression') or {}).get('p251_unchanged')}",
        f"- Changed keys: {(summary.get('regression') or {}).get('changed_keys')}",
        "",
        "## Unit tests",
        f"- P2.5.6: {(summary.get('unit_tests') or {}).get('passed')}/{(summary.get('unit_tests') or {}).get('total')}",
        f"- P2.5.5 nested: {((summary.get('unit_tests') or {}).get('p255_unit_tests') or {}).get('passed')}/{((summary.get('unit_tests') or {}).get('p255_unit_tests') or {}).get('total')}",
        f"- P2.5.4 nested: {((summary.get('unit_tests') or {}).get('p254_unit_tests') or {}).get('passed')}/{((summary.get('unit_tests') or {}).get('p254_unit_tests') or {}).get('total')}",
        "",
        "## Estimated API cost",
        f"- USD: {summary.get('estimated_api_cost_usd')}",
        f"- Note: {summary.get('estimated_cost_note')}",
        "",
        "## Engineering changes",
        f"- {ENGINEERING_CHANGES}",
        "",
        "## Production output changes",
        f"- {summary.get('production_output_changes')}",
        "",
        "## Final decision",
        f"- {summary.get('decision')}",
        "",
        "Claude Vision is a SHADOW OBSERVER. Accepted fields are SHADOW CANDIDATES only.",
        "Do not connect accepted shadow fields to steel / BBS / Excel in this phase.",
        "",
    ]
    status_path = out_root / "P2.5.6_STATUS.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")

    csv_path = reports / "field_level_comparison.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "candidate_id",
                "beam_id",
                "annotation_text",
                "field",
                "deterministic_value",
                "vision_value",
                "field_status",
                "field_decision",
                "accepted",
                "reason",
                "hypothetical_change",
                "production_change",
            ],
        )
        w.writeheader()
        for r in rows:
            fr = r.get("field_result") or {}
            comps = fr.get("field_comparisons") or {}
            for f in FIELDS:
                rec = comps.get(f) or {}
                w.writerow(
                    {
                        "candidate_id": fr.get("candidate_id"),
                        "beam_id": fr.get("beam_id"),
                        "annotation_text": fr.get("annotation_text"),
                        "field": f,
                        "deterministic_value": rec.get("deterministic_value"),
                        "vision_value": rec.get("vision_value"),
                        "field_status": rec.get("field_status"),
                        "field_decision": rec.get("field_decision"),
                        "accepted": rec.get("accepted"),
                        "reason": rec.get("reason"),
                        "hypothetical_change": rec.get("hypothetical_change"),
                        "production_change": rec.get("production_change"),
                    }
                )

    _dump(evaluation / "metrics.json", m)
    _dump(evaluation / "summary.json", summary)
    _dump(reports / "phase_summary.json", summary)
    return {"status": str(status_path), "csv": str(csv_path)}


__all__ = ["write_reports"]
