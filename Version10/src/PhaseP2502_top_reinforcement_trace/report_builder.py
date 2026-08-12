"""Reports for P2.5.0.2."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _csv(path: Path, rows: List[Dict[str, Any]], cols: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in cols})


def write_reports(out_root: Path, payload: Dict[str, Any]) -> None:
    out_root = Path(out_root)
    for d in ("reports", "traces", "metrics", "diagnostics", "visuals"):
        (out_root / d).mkdir(parents=True, exist_ok=True)

    meta = payload["meta"]
    decision = payload["decision"]
    answers = payload["answers"]
    beams = payload["beams"]
    det = payload["determinism"]
    reg = payload["regression"]

    _dump(out_root / "diagnostics" / "meta.json", meta)
    _dump(out_root / "diagnostics" / "Decision.json", decision)
    _dump(out_root / "diagnostics" / "P2502_determinism.json", det)
    _dump(out_root / "diagnostics" / "RegressionReport.json", reg)

    # Per-beam traces
    for bid, data in beams.items():
        _dump(out_root / f"{bid}_bar_trace.json", data)
        _dump(out_root / "traces" / f"{bid}_bar_trace.json", data)
        rc_lines = [
            f"# {bid} Root Cause Report — P2.5.0.2",
            "",
            f"- Actual top reinforcement: `{data.get('actual_top_reinforcement')}`",
            f"- Outcome: `{data.get('outcome')}`",
            f"- ACCEPTED_SEMANTIC_WITHOUT_PHYSICAL_GEOMETRY: "
            f"**{(data.get('completeness') or {}).get('condition_ACCEPTED_SEMANTIC_WITHOUT_PHYSICAL_GEOMETRY')}**",
            "",
            "## Rejected BAR classifications",
            "",
        ]
        for c in data.get("classifications") or []:
            rc_lines.append(
                f"- `{c.get('bar_id')}` → **{c.get('classification')}** "
                f"({c.get('confidence')}): {json.dumps(c.get('evidence'), default=str)[:500]}"
            )
        rc_lines += ["", "## Annotation chain", "", "```json", json.dumps(data.get("annotation_trace"), indent=2, default=str)[:4000], "```", ""]
        (out_root / f"{bid}_RootCauseReport.md").write_text("\n".join(rc_lines), encoding="utf-8")
        (out_root / "reports" / f"{bid}_RootCauseReport.md").write_text(
            "\n".join(rc_lines), encoding="utf-8"
        )

    # CSVs
    trace_rows = []
    spat_rows = []
    rel_rows = []
    class_rows = []
    asym_rows = []
    for bid, data in beams.items():
        for bt in data.get("bar_traces") or []:
            m = bt.get("metrics") or {}
            trace_rows.append(
                {
                    "beam_id": bid,
                    "bar_id": bt.get("bar_id"),
                    "dxf_handle": bt.get("1_dxf_entity_id"),
                    "layer": bt.get("3_layer"),
                    "r31_y": (bt.get("9_final_r31_coordinates") or {}).get("y_position"),
                    "t18_accepted": bt.get("14_t18_accepted"),
                    "t18_rule": bt.get("15_t18_rejection_rule"),
                    "t18_reason": bt.get("16_t18_rejection_reason"),
                }
            )
            spat_rows.append({"beam_id": bid, "bar_id": bt.get("bar_id"), **m})
        for c in data.get("classifications") or []:
            class_rows.append(
                {
                    "beam_id": bid,
                    "bar_id": c.get("bar_id"),
                    "classification": c.get("classification"),
                    "confidence": c.get("confidence"),
                    "corresponds_to_4Y25": c.get("corresponds_to_4Y25"),
                }
            )
        at = data.get("annotation_trace") or {}
        rel_rows.append(
            {
                "beam_id": bid,
                "annotation_id": at.get("annotation_id"),
                "text": at.get("raw_text"),
                "leader_id": at.get("leader_id"),
                "describes": json.dumps(at.get("describes")),
                "own_entity": (at.get("own_entity") or {}).get("id"),
                "evidence_reinf_count": at.get("evidence_package_reinforcement_count"),
            }
        )
        comp = data.get("completeness") or {}
        asym_rows.append(comp)

    _csv(
        out_root / "TopReinforcementTrace.csv",
        trace_rows,
        ["beam_id", "bar_id", "dxf_handle", "layer", "r31_y", "t18_accepted", "t18_rule", "t18_reason"],
    )
    _csv(
        out_root / "SpatialMetrics.csv",
        spat_rows,
        [
            "beam_id",
            "bar_id",
            "beam_to_bar_y_offset_mm",
            "beam_to_bar_x_overlap_mm",
            "beam_to_bar_euclidean_mm",
            "beam_depth_mm",
            "bar_to_beam_depth_ratio",
            "annotation_to_bar_distance_mm",
            "leader_tip_to_bar_distance_mm",
            "intersects_or_overlaps_envelope",
            "bar_vs_envelope_position",
            "r31_detection_status",
            "t18_acceptance_status",
            "t18_rejection_rule",
        ],
    )
    _csv(
        out_root / "AnnotationBarRelationship.csv",
        rel_rows,
        ["beam_id", "annotation_id", "text", "leader_id", "describes", "own_entity", "evidence_reinf_count"],
    )
    _csv(
        out_root / "ClassificationMatrix.csv",
        class_rows,
        ["beam_id", "bar_id", "classification", "confidence", "corresponds_to_4Y25"],
    )
    _csv(
        out_root / "AcceptedSemanticWithoutPhysicalGeometry.csv",
        asym_rows,
        [
            "beam_id",
            "accepted_top_bar_annotation",
            "accepted_leader",
            "target_beam_ownership",
            "accepted_physical_reinforcement_count",
            "condition_ACCEPTED_SEMANTIC_WITHOUT_PHYSICAL_GEOMETRY",
            "upstream_physical_geometry_available",
            "upstream_geometry_id",
            "legitimate_or_missing_detection",
        ],
    )

    # Before/after
    ba = [
        "# Before / After Comparison",
        "",
        "## P2.5.0 (pre spatial fix)",
        "- Crops included rejected far-elevation BAR::* → extreme tall images.",
        "- Top reinforcement OWN::* may have been visible incidentally inside huge crops.",
        "",
        "## P2.5.0.1 (accepted-only)",
        "- Rejected BAR::* excluded → crops tight.",
        "- reinforcement=[] because only PhysicalBar accepted IDs were considered.",
        "- OWN::* TOP_BAR still present upstream but not packaged as reinforcement.",
        "",
        "## Model belief vs reality",
        "- Model rejected BAR::* (correct).",
        "- Model accepted 4-Y25 → OWN::* (correct).",
        "- Evidence package omitted OWN::* geometry (gap).",
        "",
    ]
    (out_root / "BeforeAfterComparison.md").write_text("\n".join(ba), encoding="utf-8")

    reg_md = [
        "# Regression Report — P2.5.0.2",
        "",
        f"- Unchanged: **{reg.get('unchanged')}**",
        f"- Changed keys: `{reg.get('changed_keys')}`",
        f"- Determinism: **{det.get('determinism_status')}**",
        "- Engineering / T18 / R.3.1 / P2.4 / P2.5.0 production logic: **NOT MODIFIED**",
        "",
    ]
    (out_root / "RegressionReport.md").write_text("\n".join(reg_md), encoding="utf-8")

    vqa = [
        "# Visual QA Index — P2.5.0.2",
        "",
        "| Beam | Actual top | Rejected bars | Overlay |",
        "|------|------------|---------------|---------|",
    ]
    for bid, data in beams.items():
        vqa.append(
            f"| {bid} | `{data.get('actual_top_reinforcement')}` | "
            f"`{[c.get('bar_id') for c in data.get('classifications') or []]}` | "
            f"`visuals/{bid}_diagnostic_overlay.png` |"
        )
    (out_root / "VisualQAIndex.md").write_text("\n".join(vqa), encoding="utf-8")

    # Executive summary with 17 answers
    q = answers
    ex = [
        "# P2.5.0.2 Executive Summary — Top Reinforcement Trace",
        "",
        f"- MODEL_VERSION: `{meta.get('model_version')}`",
        f"- MODE: `{meta.get('mode')}`",
        f"- ENGINEERING_CHANGES: `{meta.get('engineering_changes')}`",
        f"- Decision: **{decision.get('decision')}**",
        f"- Determinism: **{det.get('determinism_status')}**",
        f"- Regression unchanged: **{reg.get('unchanged')}**",
        "",
        "## Answers",
        "",
    ]
    for i in range(1, 18):
        ex.append(f"{i}. {q.get(f'q{i}')}")
        ex.append("")
    ex += ["## Decision rationale", "", decision.get("rationale") or "", ""]
    (out_root / "ExecutiveSummary.md").write_text("\n".join(ex), encoding="utf-8")
    (out_root / "reports" / "ExecutiveSummary.md").write_text("\n".join(ex), encoding="utf-8")
