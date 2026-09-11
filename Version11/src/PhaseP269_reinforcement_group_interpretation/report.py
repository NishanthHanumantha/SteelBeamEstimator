"""P2.6.9 reports. Shadow diagnostic — not production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _group_line(g: Dict[str, Any]) -> str:
    return (
        f"{g.get('group_id')} {g.get('physical_layer')}/{g.get('reinforcement_role')}/"
        f"{g.get('specification')} zone={g.get('zone')} family={g.get('family')}"
    )


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    inventories = out_root / "inventories"
    reports.mkdir(parents=True, exist_ok=True)
    inventories.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, Any]] = result.get("records") or []
    m = result.get("metrics") or {}
    agg = m.get("aggregate") or {}
    rec = result.get("recommendation") or {}
    tests = result.get("unit_tests") or {}
    prod = result.get("production") or {}
    controls = m.get("controls") or {}

    status = [
        "# P2.6.9 — Reinforcement Group Interpretation Benchmark",
        "",
        "Shadow / research only. Observed production routing remains P2.6.4 / P2.6.5.",
        "NEVER PRODUCTION_READY. No recovery. No duplicate/distinct mutation.",
        "",
        "------------------------------------------------------------",
        "IDENTITY",
        "------------------------------------------------------------",
        "",
        f"- **MODEL_VERSION**: {result.get('model_version')}",
        f"- **PHASE**: {result.get('phase_id')} {result.get('phase_name')}",
        f"- **GATE_VERSION**: {result.get('gate_version')}",
        f"- **STATUS**: Shadow / research only. NEVER PRODUCTION_READY.",
        f"- **MODE**: {result.get('mode')}",
        f"- **PASS/FAIL**: {result.get('pass_fail')}",
        f"- **TESTS**: {tests.get('passed')}/{tests.get('total')} ({'PASS' if tests.get('success') else 'FAIL'})",
        "",
        "------------------------------------------------------------",
        "OBJECTIVE",
        "------------------------------------------------------------",
        "",
        "Can the current deterministic system reconstruct each beam's complete",
        "reinforcement-group inventory? Specification equality is not identity.",
        "",
        "------------------------------------------------------------",
        "DATASET",
        "------------------------------------------------------------",
        "",
        "- Fourth: B141, B66, B161",
        "- Fifth: B128, B55, B65",
        "- detected source: R1.3 production models (read-only)",
        "- expected source: R.1 DXF annotations + evaluation-only control overlays",
        "- GT_USED_FOR_RESOLVER = FALSE",
        "",
        "------------------------------------------------------------",
        "CAPABILITY",
        "------------------------------------------------------------",
        "",
        f"- **DETERMINISTIC CAPABILITY**: {result.get('capability')}",
        f"- overall accuracy: {agg.get('overall_group_interpretation_accuracy')}",
        f"- expected groups: {agg.get('total_expected_groups')}",
        f"- detected groups: {agg.get('total_detected_groups')}",
        f"- correct: {agg.get('correctly_interpreted_groups')}",
        f"- missed: {agg.get('missed_groups')}",
        f"- spurious: {agg.get('spurious_groups')}",
        f"- merged distinct: {agg.get('merged_distinct_groups')}",
        f"- split: {agg.get('split_groups')}",
        f"- wrong layer: {agg.get('wrong_layer_count')}",
        "",
        "------------------------------------------------------------",
        "PER-BEAM",
        "------------------------------------------------------------",
        "",
    ]
    for row in records:
        key = f"{row.get('set_key')}/{row.get('beam_id')}"
        cmp = row.get("comparison") or {}
        status.extend(
            [
                f"### {key}",
                f"- expected: {cmp.get('expected_group_count')} detected: {cmp.get('detected_group_count')} correct: {cmp.get('correctly_interpreted_groups')}",
                f"- missing: {cmp.get('missing_groups')}",
                f"- spurious: {cmp.get('spurious_groups')}",
                f"- merged: {cmp.get('merged_groups')}",
                f"- split: {cmp.get('split_groups')}",
                f"- errors: {cmp.get('errors')}",
                "- expected groups:",
            ]
        )
        for g in row.get("expected_groups") or []:
            status.append(f"  - {_group_line(g)}")
        status.append("- detected groups:")
        for g in row.get("detected_groups") or []:
            status.append(f"  - {_group_line(g)}")
        notes = row.get("discrepancy_notes") or []
        if notes:
            status.append("- discrepancy notes:")
            for n in notes:
                status.append(f"  - {n}")
        status.append("")

    status.extend(
        [
            "------------------------------------------------------------",
            "CONTROLS",
            "------------------------------------------------------------",
            "",
            f"- B128: {json.dumps(controls.get('b128') or {}, default=str)}",
            f"- B55: {json.dumps(controls.get('b55') or {}, default=str)}",
            f"- B141: {json.dumps(controls.get('b141') or {}, default=str)}",
            "",
            "------------------------------------------------------------",
            "SAFETY",
            "------------------------------------------------------------",
            "",
            f"- PRODUCTION MUTATION: {prod.get('production_mutation_count')}",
            f"- steel quantity delta: {prod.get('steel_quantity_delta')}",
            f"- BBS delta: {prod.get('bbs_delta')}",
            f"- workbook delta: {prod.get('workbook_delta')}",
            f"- all shadow_only: `{prod.get('all_shadow_only')}`",
            f"- all NO_CHANGE: `{prod.get('all_no_change')}`",
            "",
            "------------------------------------------------------------",
            "DECISION",
            "------------------------------------------------------------",
            "",
            f"- **STRENGTH**: {rec.get('strength')}",
            f"- **DECISION**: {rec.get('decision')}",
            f"- {rec.get('note')}",
            "",
            "Allowed: SAFE_SHADOW_BENCHMARK | BENCHMARK_FAILED | IMPLEMENTATION_FAILED.",
            "NEVER: PRODUCTION_READY.",
            "",
        ]
    )
    (out_root / "P2.6.9_STATUS.md").write_text("\n".join(status) + "\n", encoding="utf-8")
    (reports / "P2.6.9_STATUS.md").write_text("\n".join(status) + "\n", encoding="utf-8")

    safety = [
        "# P2.6.9 — Safety",
        "",
        f"- production mutation = {prod.get('production_mutation_count')}",
        f"- steel quantity delta = {prod.get('steel_quantity_delta')}",
        f"- BBS delta = {prod.get('bbs_delta')}",
        f"- workbook delta = {prod.get('workbook_delta')}",
        f"- all shadow_only = `{prod.get('all_shadow_only')}`",
        f"- all NO_CHANGE = `{prod.get('all_no_change')}`",
        "- no recovery / no production routing change",
        "",
    ]
    (out_root / "P2.6.9_SAFETY.md").write_text("\n".join(safety) + "\n", encoding="utf-8")

    slim_records = []
    for row in records:
        _dump(inventories / f"{row.get('set_key')}_{row.get('beam_id')}.json", row)
        slim_records.append(
            {
                "set_key": row.get("set_key"),
                "beam_id": row.get("beam_id"),
                "expected_groups": row.get("expected_groups"),
                "detected_groups": row.get("detected_groups"),
                "comparison": row.get("comparison"),
                "associations": row.get("associations"),
                "metrics": row.get("metrics"),
                "production_action": row.get("production_action"),
                "shadow_only": row.get("shadow_only"),
            }
        )
    _dump(out_root / "P2.6.9_GROUP_INVENTORIES.json", slim_records)
    _dump(out_root / "P2.6.9_COMPARISON.json", [{k: r.get(k) for k in ("set_key", "beam_id", "comparison")} for r in records])
    _dump(out_root / "P2.6.9_METRICS.json", m)
    _dump(out_root / "P2.6.9_RESULTS.json", {
        "phase_id": result.get("phase_id"),
        "model_version": result.get("model_version"),
        "gate_version": result.get("gate_version"),
        "pass_fail": result.get("pass_fail"),
        "decision": result.get("decision"),
        "capability": result.get("capability"),
        "metrics": m,
        "production_mutation_count": prod.get("production_mutation_count"),
        "recommendation": rec,
    })
    _dump(reports / "metrics.json", m)
    return {
        "status": str(out_root / "P2.6.9_STATUS.md"),
        "results": str(out_root / "P2.6.9_RESULTS.json"),
        "inventories": str(out_root / "P2.6.9_GROUP_INVENTORIES.json"),
    }


__all__ = ["write_reports"]
