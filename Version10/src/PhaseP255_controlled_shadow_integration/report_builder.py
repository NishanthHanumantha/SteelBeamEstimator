"""P2.5.5 STATUS + evaluation artefacts."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ENGINEERING_CHANGES, MODEL_VERSION, PHASE_ID, PHASE_NAME


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _fmt(v: Any) -> str:
    if v is None:
        return "N/A"
    return str(v)


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

    b58 = next(
        (
            r
            for r in rows
            if (r.get("shadow") or {}).get("candidate_id") == "VC::B58::ANN-a0c82bbe"
        ),
        None,
    )
    b58_shadow = (b58 or {}).get("shadow") or {}

    lines = [
        "# P2.5.5 STATUS",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"PASS / FAIL: {summary.get('pass_fail')}",
        f"SCOPE: {summary.get('scope')}",
        "MODE: SHADOW INTEGRATION ONLY — NO PRODUCTION PROMOTION",
        "CLAUDE: SHADOW OBSERVER (not engineering authority)",
        "",
        "## Scope",
        "- Fourth Set frozen P2.5.4 41-candidate semantic benchmark",
        "- Real P2.5.1 QuantityIntent deterministic snapshot (immutable)",
        "- Claude Vision compared in shadow only",
        f"- Execution mode: {summary.get('vision_source')}",
        f"- Benchmark/input set: P2.5.4 frozen Fourth Set ({summary.get('candidate_count')} candidates)",
        "",
        "## Pipeline metrics",
        f"- Deterministic candidate count: {m.get('total_candidates')}",
        f"- Deterministic resolved: {m.get('deterministic_resolved')}",
        f"- Deterministic partial: {m.get('deterministic_partial')}",
        f"- Deterministic unresolved: {m.get('deterministic_unresolved')}",
        f"- Claude call count: {m.get('claude_calls')}",
        f"- Claude calls live: {m.get('claude_calls_live')}",
        f"- Claude calls replayed: {m.get('claude_calls_replayed')}",
        f"- Claude success rate: {_fmt(m.get('claude_success_rate'))}%",
        f"- Claude valid response rate: {_fmt(m.get('claude_valid_response_rate'))}%",
        "",
        "## Comparison metrics",
        f"- BOTH_AGREE: {m.get('BOTH_AGREE')} ({_fmt(m.get('BOTH_AGREE_RATE'))}%)",
        f"- VISION_ONLY_RESOLVED: {m.get('VISION_ONLY_RESOLVED')} ({_fmt(m.get('VISION_ONLY_RESOLVED_RATE'))}%)",
        f"- DETERMINISTIC_ONLY_RESOLVED: {m.get('DETERMINISTIC_ONLY_RESOLVED')} ({_fmt(m.get('DETERMINISTIC_ONLY_RESOLVED_RATE'))}%)",
        f"- VISION_CONFLICT: {m.get('VISION_CONFLICT')} ({_fmt(m.get('VISION_CONFLICT_RATE'))}%)",
        f"- BOTH_UNRESOLVED: {m.get('BOTH_UNRESOLVED')} ({_fmt(m.get('BOTH_UNRESOLVED_RATE'))}%)",
        f"- VISION_WRONG (GT evaluation overlay): {m.get('VISION_WRONG')}",
        "",
        "## Vision quality (hidden GT; zone not scored)",
        f"- SEMANTIC_INTERPRETATION_ACCURACY: {_fmt(m.get('SEMANTIC_INTERPRETATION_ACCURACY'))}",
        f"- TYPE_ACCURACY: {_fmt(m.get('TYPE_ACCURACY'))}",
        f"- ROLE_ACCURACY: {_fmt(m.get('ROLE_ACCURACY'))}",
        f"- DIAMETER_ACCURACY: {_fmt(m.get('DIAMETER_ACCURACY'))}",
        f"- QUANTITY_ACCURACY: {_fmt(m.get('QUANTITY_ACCURACY'))}",
        f"- SPACING_ACCURACY: {_fmt(m.get('SPACING_ACCURACY'))}",
        f"- BEAM_ASSOCIATION_ACCURACY: {_fmt(m.get('BEAM_ASSOCIATION_ACCURACY'))}",
        f"- ZONE_ACCURACY: {_fmt(m.get('ZONE_ACCURACY'))}",
        f"- HALLUCINATION_RATE: {_fmt(m.get('HALLUCINATION_RATE'))}",
        f"- ABSTENTION_RATE: {_fmt(m.get('ABSTENTION_RATE'))}",
        "",
        "## Incremental value",
        f"- Useful Vision-only resolutions: {m.get('useful_vision_only_resolutions')}",
        f"- Rejected Vision resolutions: {m.get('rejected_vision_resolutions')}",
        f"- Conflicts prevented from reaching production: {m.get('conflicts_prevented_from_production')}",
        f"- Potential production corrections if Vision were hypothetically promoted: {m.get('potential_production_corrections_if_promoted')}",
        f"- Dangerous Vision overrides prevented: {m.get('dangerous_vision_overrides_prevented')}",
        "",
        "## Hypothetical impact (diagnostic only; not applied)",
        f"- Candidates where naive promotion WOULD_CHANGE production: {m.get('potential_production_corrections_if_promoted')}",
        "- actual_production_impact = NONE for every candidate",
        "",
        "## Safety / production mutation",
        f"- Production mutation count: {m.get('production_mutation_count')}",
        f"- Steel quantity differences: {m.get('steel_quantity_differences')}",
        f"- BBS differences: {m.get('bbs_differences')}",
        f"- Excel differences: {m.get('excel_differences')}",
        "",
        "## Regression",
        f"- Status: {summary.get('regression_status')}",
        f"- P2.5.4 artefacts unchanged: {(summary.get('regression') or {}).get('p254_unchanged')}",
        f"- Deterministic matrix unchanged: {(summary.get('regression') or {}).get('p251_unchanged')}",
        f"- Changed keys: {(summary.get('regression') or {}).get('changed_keys')}",
        "",
        "## Firewall",
        f"- Status: {(summary.get('firewall') or {}).get('ok')}",
        f"- shadow_writes_production: {(summary.get('firewall') or {}).get('shadow_writes_production')}",
        f"- Offenders: {(summary.get('firewall') or {}).get('offenders')}",
        "",
        "## Unit tests",
        f"- P2.5.5: {(summary.get('unit_tests') or {}).get('passed')}/{(summary.get('unit_tests') or {}).get('total')}",
        f"- P2.5.4 nested: {((summary.get('unit_tests') or {}).get('p254_unit_tests') or {}).get('passed')}/{((summary.get('unit_tests') or {}).get('p254_unit_tests') or {}).get('total')}",
        "",
        "## Comparison note vs P2.5.4",
        "- P2.5.4 counted OCR-unparsed stirrups as VISION_ONLY_RESOLVED when quantity_status was UNRESOLVED.",
        "- P2.5.5 treats type/role agreement as BOTH_AGREE even if numeric parse is unresolved (B58 STIRRUP-vs-STIRRUP rule).",
        "- Genuine VISION_ONLY_RESOLVED here is side-face cases where deterministic type is UNKNOWN.",
        "- Operational VISION_CONFLICT now includes field-level disagreements (e.g. B120 spacing) even when GT evaluation is Exact.",
        "",
        "## Known conflicts",
        *(summary.get("known_conflicts") or ["- none"]),
        "",
        "## B58 result",
        f"- candidate_id: {b58_shadow.get('candidate_id')}",
        f"- annotation_text: {b58_shadow.get('annotation_text')}",
        f"- deterministic_type/role: {b58_shadow.get('deterministic_type')}/{b58_shadow.get('deterministic_role')}",
        f"- vision_type/role: {b58_shadow.get('vision_type')}/{b58_shadow.get('vision_role')}",
        f"- operational_class: {b58_shadow.get('operational_class')}",
        f"- comparison_class: {b58_shadow.get('comparison_class')}",
        f"- arbitration_action: {b58_shadow.get('arbitration_action')}",
        f"- production_write: {b58_shadow.get('production_write')}",
        "",
        "## Engineering changes",
        f"- {ENGINEERING_CHANGES}",
        "",
        "## Production output changes",
        f"- {summary.get('production_output_changes')}",
        "",
        "## Estimated API cost",
        f"- USD (replayed P2.5.4 usage and/or live): {summary.get('estimated_api_cost_usd')}",
        f"- Note: {summary.get('estimated_cost_note')}",
        "",
        "## Final decision",
        f"- {summary.get('decision')}",
        "",
        "Claude Vision is a SHADOW OBSERVER. Deterministic interpretation remains the production authority.",
        "Do not promote Claude to production from this phase.",
        "",
    ]
    status_path = out_root / "P2.5.5_STATUS.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")

    csv_path = reports / "shadow_comparison.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "candidate_id",
                "beam_id",
                "annotation_text",
                "deterministic_type",
                "deterministic_role",
                "deterministic_status",
                "vision_type",
                "vision_role",
                "vision_status",
                "operational_class",
                "comparison_class",
                "arbitration_action",
                "conflict_fields",
                "promotion_eligible",
                "shadow_trigger_reason",
                "hypothetical_change",
                "actual_production_impact",
            ],
        )
        w.writeheader()
        for r in rows:
            s = r.get("shadow") or {}
            w.writerow(
                {
                    "candidate_id": s.get("candidate_id"),
                    "beam_id": s.get("beam_id"),
                    "annotation_text": s.get("annotation_text"),
                    "deterministic_type": s.get("deterministic_type"),
                    "deterministic_role": s.get("deterministic_role"),
                    "deterministic_status": s.get("deterministic_status"),
                    "vision_type": s.get("vision_type"),
                    "vision_role": s.get("vision_role"),
                    "vision_status": s.get("vision_status"),
                    "operational_class": s.get("operational_class"),
                    "comparison_class": s.get("comparison_class"),
                    "arbitration_action": s.get("arbitration_action"),
                    "conflict_fields": "|".join((s.get("conflict_flags") or {}).get("fields") or []),
                    "promotion_eligible": s.get("promotion_eligible"),
                    "shadow_trigger_reason": "|".join(s.get("shadow_trigger_reason") or []),
                    "hypothetical_change": "|".join(
                        ((s.get("hypothetical_impact") or {}).get("hypothetical_change") or [])
                    ),
                    "actual_production_impact": (s.get("hypothetical_impact") or {}).get(
                        "actual_production_impact"
                    ),
                }
            )

    _dump(evaluation / "metrics.json", m)
    _dump(evaluation / "summary.json", summary)
    _dump(reports / "phase_summary.json", summary)
    return {
        "status": str(status_path),
        "csv": str(csv_path),
        "metrics": str(evaluation / "metrics.json"),
    }


__all__ = ["write_reports"]
