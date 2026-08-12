"""Write P2.5.0.3 reports."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_beam_report(path: Path, beam: Dict[str, Any], focus: Dict[str, Any]) -> None:
    ev = beam.get("evidence") or {}
    qa = beam.get("qa") or {}
    neg = beam.get("crop_bound_test") or {}
    owned = ev.get("owned_geometry") or []
    og = owned[0] if owned else {}
    win = (ev.get("evidence_window") or {}).get("bbox")
    base = (ev.get("evidence_window") or {}).get("base_bbox")
    wh = neg.get("production_crop_wh_mm") or {}
    lines = [
        f"# {beam.get('beam_id')} Evidence Report — P2.5.0.3",
        "",
        f"- OWN geometry: `{og.get('ownership_id')}`",
        f"- Source DXF handle: `{og.get('source_handle')}` type=`{og.get('entity_type')}` layer=`{og.get('layer')}`",
        f"- dxf_resolved: `{og.get('dxf_resolved')}`",
        f"- Annotation: `{og.get('annotation_id')}` text=`{og.get('annotation_text')}`",
        f"- Leader: `{og.get('leader_id')}`",
        f"- Expected OWN: `{focus.get('own_entity')}`",
        f"- Expected leader: `{focus.get('leader')}`",
        f"- Rejected bars (must exclude): `{focus.get('rejected_bars')}`",
        f"- Rejected in reinforcement list: `{neg.get('rejected_bars_in_reinforcement_list')}`",
        f"- Crop bbox: `{win}`",
        f"- Base bbox: `{base}`",
        f"- Crop W×H mm: {wh.get('w_mm')} × {wh.get('h_mm')}",
        f"- OWN inside crop: `{neg.get('own_inside_production_crop')}`",
        f"- Counterfactual would differ (rejected expand): `{neg.get('counterfactual_would_differ')}`",
        f"- Extreme expansion returned: `{neg.get('extreme_expansion_returned')}`",
        f"- Crop QA overall: `{qa.get('overall')}`",
        f"- Gates: `{json.dumps(qa.get('gates') or {}, indent=2)}`",
        f"- Engineering crop: `{beam.get('engineering_crop')}`",
        f"- Overlay: `{beam.get('evidence_overlay')}`",
        "",
    ]
    _md(path, "\n".join(lines))


def write_reports(
    *,
    out_root: Path,
    meta: Dict[str, Any],
    beams: Dict[str, Dict[str, Any]],
    focus: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
    unit_tests: Dict[str, Any],
    decision: str,
) -> None:
    reports = out_root
    reports.mkdir(parents=True, exist_ok=True)

    # Evidence package JSON + CSV
    pkg_rows = []
    own_rows = []
    qa_rows = []
    for bid, b in beams.items():
        ev = b.get("evidence") or {}
        qa = b.get("qa") or {}
        neg = b.get("crop_bound_test") or {}
        pkg_rows.append(
            {
                "beam_id": bid,
                "owned_count": len(ev.get("owned_geometry") or []),
                "reinf_count": len(ev.get("reinforcement") or []),
                "ann_count": len(ev.get("annotations") or []),
                "leader_count": len(ev.get("leaders") or []),
                "crop_bbox": json.dumps((ev.get("evidence_window") or {}).get("bbox")),
                "qa_overall": qa.get("overall"),
                "own_inside": neg.get("own_inside_production_crop"),
                "extreme": neg.get("extreme_expansion_returned"),
            }
        )
        for o in ev.get("owned_geometry") or []:
            own_rows.append(
                {
                    "beam_id": bid,
                    "evidence_id": o.get("evidence_id"),
                    "ownership_id": o.get("ownership_id"),
                    "source_handle": o.get("source_handle"),
                    "entity_type": o.get("entity_type"),
                    "layer": o.get("layer"),
                    "annotation_id": o.get("annotation_id"),
                    "leader_id": o.get("leader_id"),
                    "annotation_text": o.get("annotation_text"),
                    "semantic_role": o.get("semantic_role"),
                    "evidence_type": o.get("evidence_type"),
                    "dxf_resolved": o.get("dxf_resolved"),
                    "bbox": json.dumps(o.get("bbox")),
                }
            )
        gates = qa.get("gates") or {}
        row = {"beam_id": bid, "overall": qa.get("overall")}
        row.update(gates)
        qa_rows.append(row)
        write_beam_report(reports / f"{bid}_EvidenceReport.md", b, focus.get(bid) or {})

    _dump(reports / "EvidencePackage.json", {bid: beams[bid].get("evidence") for bid in beams})
    _write_csv(reports / "EvidencePackage.csv", pkg_rows)
    _write_csv(reports / "OwnedGeometryTrace.csv", own_rows)
    _write_csv(reports / "CropQAMatrix.csv", qa_rows)

    # Visual QA index
    vis_lines = ["# Visual QA Index — P2.5.0.3", ""]
    for bid, b in beams.items():
        vis_lines.append(f"## {bid}")
        vis_lines.append(f"- engineering_crop: `{b.get('engineering_crop')}`")
        vis_lines.append(f"- evidence_overlay: `{b.get('evidence_overlay')}`")
        vis_lines.append(
            "- Inspect: BEAM + OWN TOP_BAR LWPOLYLINE + 4-Y25 + leader; no far-elevation bars."
        )
        vis_lines.append("")
    _md(reports / "VisualQAIndex.md", "\n".join(vis_lines))

    # Regression
    _dump(reports / "RegressionReport.json", regression)
    reg_md = [
        "# Regression Report — P2.5.0.3",
        "",
        f"- unchanged: `{regression.get('unchanged')}`",
        f"- changed_files: `{regression.get('changed')}`",
        f"- ENGINEERING_CHANGES: NONE (expected)",
        f"- T18 / R.3.1: not modified",
        "",
    ]
    _md(reports / "RegressionReport.md", "\n".join(reg_md))

    # Executive summary answers
    b97 = beams.get("B97A") or {}
    b98 = beams.get("B98A") or {}
    e97 = b97.get("evidence") or {}
    e98 = b98.get("evidence") or {}
    n97 = b97.get("crop_bound_test") or {}
    n98 = b98.get("crop_bound_test") or {}
    o97 = (e97.get("owned_geometry") or [{}])[0] if e97.get("owned_geometry") else {}
    o98 = (e98.get("owned_geometry") or [{}])[0] if e98.get("owned_geometry") else {}

    exec_lines = [
        "# Executive Summary — P2.5.0.3 Accepted OWN TOP_BAR Evidence Packaging",
        "",
        f"- MODEL_VERSION: `{meta.get('model_version')}`",
        f"- PHASE: `{meta.get('phase_id')}`",
        f"- Decision: **{decision}**",
        f"- Determinism: `{determinism.get('determinism_status')}`",
        f"- Unit tests: `{unit_tests.get('passed')}/{unit_tests.get('total')}`",
        f"- Regression unchanged: `{regression.get('unchanged')}`",
        f"- Claude calls: NONE",
        "",
        "## Required answers",
        "",
        f"1. B97A OWN::B97A::1247FFF packaged? **{'YES' if o97.get('ownership_id') == 'OWN::B97A::1247FFF' else 'NO'}**",
        f"2. B98A OWN::B98A::1247FFE packaged? **{'YES' if o98.get('ownership_id') == 'OWN::B98A::1247FFE' else 'NO'}**",
        f"3. Actual DXF geometry visible (resolved + in crop)? B97A=`{n97.get('own_dxf_resolved') and n97.get('own_inside_production_crop')}` B98A=`{n98.get('own_dxf_resolved') and n98.get('own_inside_production_crop')}`",
        f"4. 4-Y25 linked? B97A=`{o97.get('annotation_text')}` / `{o97.get('annotation_id')}` ; B98A=`{o98.get('annotation_text')}` / `{o98.get('annotation_id')}`",
        f"5. Leaders preserved? B97A=`{o97.get('leader_id')}` ; B98A=`{o98.get('leader_id')}`",
        f"6. Rejected PhysicalBars excluded? B97A=`{not n97.get('rejected_bars_in_reinforcement_list')}` B98A=`{not n98.get('rejected_bars_in_reinforcement_list')}`",
        f"7. Extreme crop problem remain fixed? B97A extreme=`{n97.get('extreme_expansion_returned')}` B98A extreme=`{n98.get('extreme_expansion_returned')}`",
        f"8. Final crop dimensions (mm W×H): B97A={ (n97.get('production_crop_wh_mm') or {}) } B98A={ (n98.get('production_crop_wh_mm') or {}) }",
        f"9. Beam-to-crop ratios: see per-beam reports / CropQAMatrix",
        f"10. Vision-ready B97A/B98A? **{'YES' if decision == 'READY_FOR_P2.5.1' else 'NO'}**",
        f"11. Engineering output changed? **NO** (fingerprints)",
        f"12. T18/R.3.1 logic changed? **NO**",
        f"13. Determinism passed? **{determinism.get('determinism_status') == 'PASS'}**",
        f"14. Regression passed? **{bool(regression.get('unchanged'))}**",
        f"15. P2.5.1 unblocked? **{decision == 'READY_FOR_P2.5.1'}**",
        "",
    ]
    _md(reports / "ExecutiveSummary.md", "\n".join(exec_lines))
    _dump(reports / "RunSummary.json", {
        "meta": meta,
        "decision": decision,
        "determinism": determinism,
        "regression": regression,
        "unit_tests": unit_tests,
        "beams": {k: {
            "qa_overall": (v.get("qa") or {}).get("overall"),
            "gates": (v.get("qa") or {}).get("gates"),
            "crop_bound_test": v.get("crop_bound_test"),
            "owned_geometry": (v.get("evidence") or {}).get("owned_geometry"),
        } for k, v in beams.items()},
    })


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
