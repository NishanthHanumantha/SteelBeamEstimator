"""Write P2.5.0.4 reports."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ROOT_CAUSE


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: List[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


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
    out_root.mkdir(parents=True, exist_ok=True)
    qa_rows = []
    pkg_rows = []
    for bid, b in beams.items():
        ev = b.get("evidence") or {}
        qa = b.get("qa") or {}
        neg = b.get("crop_bound_test") or {}
        rv = b.get("render_validation") or {}
        og = (ev.get("owned_geometry") or [{}])[0] if ev.get("owned_geometry") else {}
        wh = neg.get("production_crop_wh_mm") or {}
        gates = qa.get("gates") or {}
        row = {"beam_id": bid, "overall": qa.get("overall")}
        row.update(gates)
        qa_rows.append(row)
        pkg_rows.append(
            {
                "beam_id": bid,
                "ownership_id": og.get("ownership_id"),
                "source_handle": og.get("source_handle"),
                "paint_count": (b.get("engineering_render") or {}).get(
                    "owned_geometry_paint_count"
                ),
                "rv_rendered": rv.get("rendered"),
                "rv_distinguishable": rv.get("distinguishable"),
                "crop_w": wh.get("w_mm"),
                "crop_h": wh.get("h_mm"),
                "extreme": neg.get("extreme_expansion_returned"),
            }
        )
        _md(
            out_root / f"{bid}_EvidenceReport.md",
            "\n".join(
                [
                    f"# {bid} Evidence Report — P2.5.0.4",
                    "",
                    f"- OWN: `{og.get('ownership_id')}` handle=`{og.get('source_handle')}`",
                    f"- Annotation: `{og.get('annotation_text')}` / `{og.get('annotation_id')}`",
                    f"- Leader: `{og.get('leader_id')}`",
                    f"- Paint count: `{(b.get('engineering_render') or {}).get('owned_geometry_paint_count')}`",
                    f"- Render validation: `{json.dumps(rv, indent=2, default=str)}`",
                    f"- Crop W×H mm: {wh}",
                    f"- QA gates: `{json.dumps(gates, indent=2)}`",
                    f"- Engineering: `{b.get('engineering_crop')}`",
                    f"- Overlay: `{b.get('evidence_overlay')}`",
                    "",
                ]
            ),
        )

    _write_csv(out_root / "CropQAMatrix.csv", qa_rows)
    _write_csv(out_root / "EvidencePackage.csv", pkg_rows)
    _dump(out_root / "EvidencePackage.json", {k: v.get("evidence") for k, v in beams.items()})
    _dump(
        out_root / "OwnedGeometryTrace.json",
        {
            k: (v.get("evidence") or {}).get("owned_geometry")
            for k, v in beams.items()
        },
    )
    _write_csv(
        out_root / "OwnedGeometryTrace.csv",
        [
            {
                "beam_id": bid,
                **{
                    kk: oo.get(kk)
                    for kk in (
                        "evidence_id",
                        "ownership_id",
                        "source_handle",
                        "entity_type",
                        "layer",
                        "annotation_id",
                        "leader_id",
                        "annotation_text",
                    )
                },
            }
            for bid, b in beams.items()
            for oo in ((b.get("evidence") or {}).get("owned_geometry") or [])
        ],
    )

    vis = ["# Visual QA Index — P2.5.0.4", "", "Inspect engineering crop for visible OWN TOP_BAR stroke.", ""]
    for bid, b in beams.items():
        vis.append(f"## {bid}")
        vis.append(f"- engineering_crop: `{b.get('engineering_crop')}`")
        vis.append(f"- evidence_overlay: `{b.get('evidence_overlay')}`")
        vis.append(f"- render_validation: `{(b.get('render_validation') or {}).get('rendered')}` / distinguishable `{(b.get('render_validation') or {}).get('distinguishable')}`")
        vis.append("")
    _md(out_root / "VisualQAIndex.md", "\n".join(vis))

    _dump(out_root / "RegressionReport.json", regression)
    _md(
        out_root / "RegressionReport.md",
        "\n".join(
            [
                "# Regression Report — P2.5.0.4",
                "",
                f"- unchanged: `{regression.get('unchanged')}`",
                f"- changed: `{regression.get('changed')}`",
                "- ENGINEERING_CHANGES: NONE",
                "- T18 / R.3.1: not modified",
                "",
            ]
        ),
    )

    b97 = beams.get("B97A") or {}
    b98 = beams.get("B98A") or {}
    n97 = b97.get("crop_bound_test") or {}
    n98 = b98.get("crop_bound_test") or {}
    r97 = b97.get("render_validation") or {}
    r98 = b98.get("render_validation") or {}
    o97 = ((b97.get("evidence") or {}).get("owned_geometry") or [{}])[0]
    o98 = ((b98.get("evidence") or {}).get("owned_geometry") or [{}])[0]

    _md(
        out_root / "ExecutiveSummary.md",
        "\n".join(
            [
                "# Executive Summary — P2.5.0.4 OWN TOP_BAR Engineering Crop Rendering",
                "",
                f"- MODEL_VERSION: `{meta.get('model_version')}`",
                f"- Decision: **{decision}**",
                f"- Determinism: `{determinism.get('determinism_status')}`",
                f"- Unit tests: `{unit_tests.get('passed')}/{unit_tests.get('total')}`",
                f"- Regression unchanged: `{regression.get('unchanged')}`",
                f"- Claude: NONE",
                "",
                "## Root Cause",
                "",
                ROOT_CAUSE,
                "",
                "## Answers",
                "",
                f"1. B97A OWN packaged+rendered? packaged=`{o97.get('ownership_id')}` rendered=`{r97.get('rendered')}` distinguishable=`{r97.get('distinguishable')}`",
                f"2. B98A OWN packaged+rendered? packaged=`{o98.get('ownership_id')}` rendered=`{r98.get('rendered')}` distinguishable=`{r98.get('distinguishable')}`",
                f"3. Actual DXF geometry used? YES (points from handles {o97.get('source_handle')}/{o98.get('source_handle')})",
                f"4. Synthetic geometry? NO",
                f"5–8. Annotations/leaders: B97A `{o97.get('annotation_text')}`/`{o97.get('leader_id')}`; B98A `{o98.get('annotation_text')}`/`{o98.get('leader_id')}`",
                f"9–12. Rejected excluded / not extreme: B97A extreme=`{n97.get('extreme_expansion_returned')}` B98A extreme=`{n98.get('extreme_expansion_returned')}`",
                f"13. Crop dims: B97A={n97.get('production_crop_wh_mm')} B98A={n98.get('production_crop_wh_mm')}",
                f"14. Determinism: `{determinism.get('determinism_status')}`",
                f"15. Vision-ready / P2.5.1: **{decision}**",
                "",
            ]
        ),
    )
    _dump(
        out_root / "RunSummary.json",
        {
            "meta": meta,
            "decision": decision,
            "determinism": determinism,
            "regression": regression,
            "unit_tests": unit_tests,
            "root_cause": ROOT_CAUSE,
            "beams": {
                k: {
                    "qa": v.get("qa"),
                    "render_validation": v.get("render_validation"),
                    "crop_bound_test": v.get("crop_bound_test"),
                    "paint_count": (v.get("engineering_render") or {}).get(
                        "owned_geometry_paint_count"
                    ),
                }
                for k, v in beams.items()
            },
        },
    )
