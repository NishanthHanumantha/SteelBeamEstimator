"""P2.6.10-A reports. Shadow diagnostic — not production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, Any]] = result.get("records") or []
    prod = result.get("production") or {}
    tests = result.get("unit_tests") or {}
    b55 = result.get("b55_diagnostics") or {}
    inv = result.get("discovered_components") or []

    lines = [
        f"# {result.get('phase_id')} — {result.get('phase_name')}",
        "",
        "Shadow / research only. No Claude Vision. No production mutation.",
        "",
        f"STATUS: {result.get('pass_fail')}",
        f"MODEL_VERSION: {result.get('model_version')}",
        f"EXISTING RENDERING CAPABILITY: {result.get('existing_rendering_capability')}",
        f"REUSABILITY CLASS: {result.get('reusability_class')}",
        f"FINAL DECISION: {result.get('decision')}",
        "",
        "## Discovered components",
        "",
    ]
    for c in inv:
        lines.append(
            f"- `{c.get('file')}` / `{c.get('class_function')}` — {c.get('purpose')} "
            f"(method={c.get('rendering_method')}; localization={c.get('localization_method')}; "
            f"independence={c.get('independence')})"
        )
    lines += ["", "## Six-beam results", ""]
    for r in records:
        d = ((r.get("crops") or {}).get("detail") or {})
        c = ((r.get("crops") or {}).get("context") or {})
        q = d.get("quality") or {}
        lines += [
            f"### {r.get('set_key')}/{r.get('beam_id')}",
            f"- context crop: `{c.get('path')}`",
            f"- detail crop: `{d.get('path')}`",
            f"- localization method: {r.get('localization_method')}",
            f"- independent of annotation association: {'YES' if not r.get('annotation_association_dependency') else 'NO'}",
            f"- Vision readiness: {q.get('vision_readiness')}",
            f"- findings: title_in={q.get('beam_title_included')} geometry={q.get('beam_geometry_included')} "
            f"clip={q.get('clipping_detected')} read={q.get('readability_status')} "
            f"neighbors_detail={q.get('neighbor_titles_in_crop')}",
            "",
        ]
    lines += [
        "## B55 detailed diagnosis",
        "",
        f"- title located: {b55.get('B55_title_located')}",
        f"- beam geometry located: {b55.get('B55_beam_geometry_located')}",
        f"- correct detail captured: {b55.get('correct_visual_detail_captured')}",
        f"- neighboring detail visible: {b55.get('neighboring_detail_visible')}",
        f"- target annotations visible: {b55.get('target_reinforcement_visually_present')}",
        f"- unrelated annotations captured: {b55.get('unrelated_reinforcement_captured')}",
        f"- clipping: {b55.get('clipping')}",
        f"- text readability: {b55.get('text_readability')}",
        f"- Vision readiness: {b55.get('Vision_readiness')}",
        "",
        "## Production safety",
        "",
        f"- production mutation count: {prod.get('production_mutation_count')}",
        f"- steel quantity delta: {prod.get('steel_quantity_delta')}",
        f"- BBS delta: {prod.get('bbs_delta')}",
        f"- workbook delta: {prod.get('workbook_delta')}",
        "",
        "## Regression",
        "",
        f"- P2.6.6: {(result.get('prior_regression') or {}).get('p266')}",
        f"- P2.6.7: {(result.get('prior_regression') or {}).get('p267')}",
        f"- P2.6.8: {(result.get('prior_regression') or {}).get('p268')}",
        f"- P2.6.9: {(result.get('prior_regression') or {}).get('p269')}",
        "",
        f"Unit tests: {tests.get('passed')}/{tests.get('total')} success={tests.get('success')}",
        "",
        "## Next step",
        "",
        str(result.get("next_step") or ""),
        "",
    ]
    status_path = out_root / "P2.6.10-A_STATUS.md"
    report_status = reports / "P2.6.10-A_STATUS.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")
    report_status.write_text("\n".join(lines), encoding="utf-8")
    _dump(out_root / "P2.6.10-A_RESULTS.json", {k: v for k, v in result.items() if k != "records"})
    _dump(reports / "metrics.json", result.get("metrics") or {})
    _dump(out_root / "P2.6.10-A_B55_DIAGNOSTICS.json", b55)
    return {
        "status": str(status_path),
        "results": str(out_root / "P2.6.10-A_RESULTS.json"),
        "b55": str(out_root / "P2.6.10-A_B55_DIAGNOSTICS.json"),
    }


__all__ = ["write_reports"]
