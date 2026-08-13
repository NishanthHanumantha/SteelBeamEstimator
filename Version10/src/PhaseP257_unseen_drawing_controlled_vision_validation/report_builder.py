"""P2.5.7 STATUS + required artefacts."""
from __future__ import annotations

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


def _field_acc_lines(by_field: Dict[str, Any], key: str) -> List[str]:
    lines = []
    for f, rec in (by_field or {}).items():
        lines.append(f"- {f}: {_fmt(rec.get(key))}")
    return lines


def write_reports(*, out_root: Path, summary: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    evaluation = out_root / "evaluation"
    reports.mkdir(parents=True, exist_ok=True)
    evaluation.mkdir(parents=True, exist_ok=True)
    m = summary.get("metrics") or {}
    cost = summary.get("cost") or {}
    by = m.get("by_field") or {}
    ds = summary.get("dataset") or {}
    unit = summary.get("unit_tests") or {}
    reg = summary.get("regression") or {}
    stirrup = m.get("stirrup") or {}
    role = m.get("role") or {}
    ocr = m.get("ocr") or {}

    lines = [
        "# P2.5.7 STATUS",
        "",
        "---------------------------------------------------",
        "IDENTITY",
        "---------------------------------------------------",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"PASS/FAIL: {summary.get('pass_fail')}",
        f"FINAL_DECISION: {summary.get('decision')}",
        "",
        "---------------------------------------------------",
        "DATASET",
        "---------------------------------------------------",
        "",
        f"drawing_set_id: {ds.get('drawing_set_id')}",
        f"unseen_status: {ds.get('unseen_status')}",
        f"UNSEEN_SET_VERIFIED: {ds.get('UNSEEN_SET_VERIFIED')}",
        f"DXF count: {ds.get('dxf_count')}",
        f"beam count: {ds.get('number_of_beams')}",
        f"candidate count: {summary.get('candidate_count')}",
        f"eligible (Claude) count: {summary.get('eligible_count')}",
        f"skipped count: {summary.get('skipped_count')}",
        f"GT coverage: {_fmt(m.get('GT_coverage'))}",
        f"fields with reliable GT: {m.get('fields_with_reliable_GT')}",
        f"fields without reliable GT: {m.get('fields_without_reliable_GT')}",
        "",
        "---------------------------------------------------",
        "EXECUTION",
        "---------------------------------------------------",
        "",
        f"Claude model: {summary.get('claude_model')}",
        f"temperature: {summary.get('temperature')}",
        f"live calls: {cost.get('live_claude_calls')}",
        f"failed calls: {cost.get('failed_calls')}",
        f"prompt version: {summary.get('prompt_version')}",
        f"schema version: {summary.get('schema_version')}",
        f"mode: {summary.get('mode')}",
        f"vision source: {summary.get('vision_source')}",
        "",
        "---------------------------------------------------",
        "BASELINE",
        "---------------------------------------------------",
        "",
        f"DETERMINISTIC_BASELINE_ACCURACY: {_fmt(m.get('DETERMINISTIC_BASELINE_ACCURACY'))}",
        *_field_acc_lines(by, "deterministic_accuracy"),
        "",
        "---------------------------------------------------",
        "VISION",
        "---------------------------------------------------",
        "",
        f"VISION_FIELD_ACCURACY: {_fmt(m.get('VISION_FIELD_ACCURACY'))}",
        *_field_acc_lines(by, "vision_accuracy"),
        "",
        "---------------------------------------------------",
        "INCREMENTAL VALUE",
        "---------------------------------------------------",
        "",
        f"TRUE_VISION_INCREMENTAL_VALUE_RATE: {_fmt(m.get('TRUE_VISION_INCREMENTAL_VALUE_RATE'))}",
        f"VISION_CORRECTION_RATE: {_fmt(m.get('VISION_CORRECTION_RATE'))}",
        f"VISION_CONFIRMATION_RATE: {_fmt(m.get('VISION_CONFIRMATION_RATE'))}",
        f"VISION_CONFLICT_RATE: {_fmt(m.get('VISION_CONFLICT_RATE'))}",
        f"VISION_WRONG_ON_CORRECT_DETERMINISTIC_RATE: {_fmt(m.get('VISION_WRONG_ON_CORRECT_DETERMINISTIC_RATE'))}",
        f"HYPOTHETICAL_COMBINED_ACCURACY: {_fmt(m.get('HYPOTHETICAL_COMBINED_ACCURACY'))}",
        f"DETERMINISTIC_ONLY_ACCURACY: {_fmt(m.get('DETERMINISTIC_ONLY_ACCURACY'))}",
        f"IMPROVEMENT_DELTA: {_fmt(m.get('IMPROVEMENT_DELTA'))}",
        f"true incremental field count: {m.get('true_incremental_field_count')}",
        "",
        "---------------------------------------------------",
        "STIRRUP",
        "---------------------------------------------------",
        "",
        f"candidates: {stirrup.get('candidates')}",
        f"deterministic accuracy: {_fmt(stirrup.get('deterministic_accuracy'))}",
        f"Vision accuracy: {_fmt(stirrup.get('vision_accuracy'))}",
        f"TRUE incremental rate: {_fmt(stirrup.get('TRUE_VISION_INCREMENTAL_VALUE_RATE'))}",
        f"vision-only correct recovery: {stirrup.get('vision_only_correct_recovery')}",
        f"vision wrong recovery: {stirrup.get('vision_wrong_recovery')}",
        "",
        "---------------------------------------------------",
        "ROLE",
        "---------------------------------------------------",
        "",
    ]
    for role_name, rec in role.items():
        lines.append(
            f"- {role_name}: GT={rec.get('ground_truth_count')} "
            f"det_known={rec.get('deterministic_known')} vis_known={rec.get('vision_known')} "
            f"vis_correct={rec.get('vision_correct_recovery')} vis_wrong={rec.get('vision_wrong_recovery')} "
            f"det_ok_vis_wrong={rec.get('deterministic_correct_vision_wrong')} "
            f"det_unk_vis_ok={rec.get('deterministic_unknown_vision_correct')}"
        )
    lines += [
        "",
        "---------------------------------------------------",
        "OCR",
        "---------------------------------------------------",
        "",
        f"candidates: {ocr.get('candidates')}",
        f"deterministic accuracy: {_fmt(ocr.get('deterministic_accuracy'))}",
        f"Vision accuracy: {_fmt(ocr.get('vision_accuracy'))}",
        f"TRUE incremental rate: {_fmt(ocr.get('TRUE_VISION_INCREMENTAL_VALUE_RATE'))}",
        f"vision-only correct recovery: {ocr.get('vision_only_correct_recovery')}",
        f"vision wrong recovery: {ocr.get('vision_wrong_recovery')}",
        "",
        "---------------------------------------------------",
        "SAFETY",
        "---------------------------------------------------",
        "",
        f"production mutation: {m.get('production_mutation_count')}",
        f"steel difference: {m.get('steel_quantity_difference')}",
        f"BBS difference: {m.get('bbs_difference')}",
        f"Excel difference: {m.get('excel_difference')}",
        f"dangerous override count: {m.get('dangerous_vision_override_count')}",
        f"dangerous override rate: {_fmt(m.get('dangerous_vision_override_rate'))}",
        f"accepted shadow fields: {m.get('accepted_shadow_field_count')}",
        f"rejected shadow fields: {m.get('rejected_shadow_field_count')}",
        f"conflict fields: {m.get('conflict_field_count')}",
        f"firewall ok: {(summary.get('firewall') or {}).get('ok')}",
        "",
        "---------------------------------------------------",
        "REGRESSION",
        "---------------------------------------------------",
        "",
        f"P2.5.1 unchanged: {reg.get('p251_unchanged')}",
        f"P2.5.4 unchanged: {reg.get('p254_unchanged')}",
        f"P2.5.5 unchanged: {reg.get('p255_unchanged')}",
        f"P2.5.6 unchanged: {reg.get('p256_unchanged')}",
        f"all fingerprints unchanged: {reg.get('unchanged')}",
        f"changed keys: {reg.get('changed_keys')}",
        "",
        "---------------------------------------------------",
        "COST",
        "---------------------------------------------------",
        "",
        f"input tokens: {cost.get('input_tokens')}",
        f"output tokens: {cost.get('output_tokens')}",
        f"total tokens: {cost.get('total_tokens')}",
        f"estimated cost USD: {cost.get('estimated_cost_usd')}",
        f"cost per candidate: {cost.get('cost_per_candidate')}",
        f"cost per Vision field candidate: {cost.get('cost_per_Vision_field_candidate')}",
        f"cost per TRUE incremental field: {cost.get('cost_per_TRUE_INCREMENTAL_FIELD')}",
        f"note: {cost.get('cost_note')}",
        "",
        "---------------------------------------------------",
        "ENGINEERING CHANGES",
        "---------------------------------------------------",
        "",
        f"{ENGINEERING_CHANGES}",
        "No production changes.",
        "Claude remains SHADOW OBSERVER.",
        "Deterministic P2.5.1 remains PRODUCTION AUTHORITY.",
        "",
        "---------------------------------------------------",
        "TESTS",
        "---------------------------------------------------",
        "",
        f"P2.5.7: {unit.get('passed')}/{unit.get('total')}",
        f"P2.5.6: {(unit.get('p256_unit_tests') or {}).get('passed')}/{(unit.get('p256_unit_tests') or {}).get('total')}",
        f"P2.5.5: {(unit.get('p255_unit_tests') or {}).get('passed')}/{(unit.get('p255_unit_tests') or {}).get('total')}",
        f"P2.5.4: {(unit.get('p254_unit_tests') or {}).get('passed')}/{(unit.get('p254_unit_tests') or {}).get('total')}",
        "",
        "---------------------------------------------------",
        "FINAL DECISION",
        "---------------------------------------------------",
        "",
        f"{summary.get('decision')}",
        "",
        "P2.5.7 does NOT declare production readiness.",
        "Hypothetical combined field result is diagnostic only.",
        "",
    ]
    status_path = out_root / "P2.5.7_STATUS.md"
    status_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (reports / "P2.5.7_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    _dump(evaluation / "incremental_value_metrics.json", m)
    _dump(evaluation / "cost_metrics.json", cost)
    _dump(evaluation / "unit_tests.json", unit)
    _dump(out_root / "incremental_value_metrics.json", m)
    _dump(out_root / "cost_metrics.json", cost)
    return {"status": str(status_path)}


__all__ = ["write_reports"]
