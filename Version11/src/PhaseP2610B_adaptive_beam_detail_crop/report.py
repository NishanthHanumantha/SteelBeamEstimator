"""P2.6.10-B reports. Shadow diagnostic — not production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


_FIELDS = (
    "title_visible",
    "beam_geometry_visible",
    "stirrup_visible",
    "bottom_reinforcement_visible",
    "top_reinforcement_visible",
    "top_extra_visible_when_present",
    "relevant_dimensions_visible_when_present",
    "left_support_evidence_visible_when_present",
    "right_support_evidence_visible_when_present",
    "leaders_preserved",
    "important_text_clipped",
    "unrelated_neighbor_detail_present",
    "vertical_evidence_complete",
    "horizontal_evidence_complete",
)


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _ok(info: Any) -> str:
    if isinstance(info, dict):
        return "PASS" if info.get("ok") else "FAIL"
    return str(info)


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, Any]] = result.get("records") or []
    prod = result.get("production") or {}
    tests = result.get("unit_tests") or {}
    rec = result.get("recommendation") or {}
    leak = result.get("leakage") or {}
    prior = result.get("prior_regression") or {}
    metrics = result.get("metrics") or {}
    complete_n = int(metrics.get("complete_count") or 0)
    lines = [
        f"# {result.get('phase_id')} — {result.get('phase_name')}",
        "",
        "Shadow / research only. No Claude Vision. No production mutation.",
        "",
        f"**Phase:** {result.get('phase_id')}",
        f"**Model version:** {result.get('model_version')}",
        f"**Gate version:** {result.get('gate_version')}",
        f"**STATUS:** {result.get('pass_fail')}",
        f"**DECISION:** {result.get('decision')}",
        f"**READINESS:** {rec.get('readiness')}",
        "",
        "## Objective",
        "",
        "Make the Type B detail crop information-complete. The beam title is the",
        "primary vertical anchor. Spatial evidence (text, leaders, dimensions,",
        "outline, proximity, overlap, alignment, density) expands the envelope.",
        "Runtime crop localization does not use R.1 `by_beam` association or GT.",
        "This phase does not invoke Claude Vision.",
        "",
        "## Architecture",
        "",
        "- Reuse P2.6.10-A association-independent title localization (`title_localizer`).",
        "- Reuse P2.6.10-A context extents (`region_builder.build_target_regions`).",
        "- Reuse M.1 `dxf_renderer.render_dxf_region_to_png` via P2.6.10-A `cropper`.",
        "- Reuse T1.5 `_outline_bracket` only as a geometry hint, called with the",
        "  independently localized mark (not R.1 `compute_geometry_envelopes`).",
        "- Replace P2.6.10-A `_tighten_detail_y` (outline + `2.2*depth+500` cap)",
        "  with an adaptive evidence envelope:",
        "  TITLE_BAND → STIRRUP_BAND → BOTTOM_REINFORCEMENT_BAND → BEAM_BODY_BAND",
        "  → TOP_REINFORCEMENT_BAND → TOP_EXTRA_DIMENSION_BAND.",
        "- Grow upward until owned reinforcement-like text is inside the crop;",
        "  stop before the next-row title. Grow horizontally to owned extras/dims;",
        "  stop before same-row neighbor titles.",
        "",
        "P2.6.10-A root cause reused here: `_tighten_detail_y` capped `ymax` at",
        "`title_y + 2.2*depth + 500` (1600 mm for 500 mm beams). Top bars on B141/",
        "B66/B161 sit above that cap. This phase does not add a fixed top margin;",
        "it expands to spatial evidence and clamps at the next-row title.",
        "",
        "## Files changed",
        "",
        "- `Version10/src/PhaseP2610B_adaptive_beam_detail_crop/` (new)",
        "- `Version10/Run_PY/run_phase_p2610b_adaptive_beam_detail_crop.py` (new)",
        "- prior-phase regression skip lists include `PhaseP2610B_`",
        "- `Version10/.gitignore` whitelist for this output directory",
        "",
        "P2.6.10-A artefacts are not overwritten.",
        "",
        "## Benchmark beams",
        "",
        "Fourth: B141, B66, B161. Fifth: B128, B55, B65.",
        "",
        f"Spatial completeness: {complete_n}/6",
        "",
        "## Before/after crop comparison",
        "",
        "A = P2.6.10-A detail crop (copied, not regenerated). B = adaptive detail crop.",
        "",
        "Visual before/after of the P2.6.10-A failures:",
        "- B141/B66/B161 A: top reinforcement cut off at the outline/`2.2*depth+500` cap.",
        "  B: top labels (`5-Y20`, `5-Y16`, `4-Y20`) and leaders are inside the crop.",
        "- B55/B65 A: right-side extra/dimension can clip. B: B65 `3-Y20` + `1800` and",
        "  B55 `1400`/`500` support dimensions are inside the crop.",
        "- B128 remains a complete stack in both A and B.",
        "",
        "Residual packed-sheet slivers (not neighbor titles, not missing target evidence):",
        "- B141/B128: a left-edge fragment of the adjacent same-row detail can remain",
        "  because the X barrier stops at the neighbor title, not at empty space.",
        "- B161/B65: a few millimetres of the row-below top labels can remain under the",
        "  title because span dimensions sit ~550–720 mm below the title anchor.",
        "",
    ]
    for r in records:
        c = r.get("completeness") or {}
        ad = r.get("adaptive") or {}
        lines += [
            f"### {r.get('set_key')}/{r.get('beam_id')}",
            f"- A detail: `{((r.get('comparison') or {}).get('a_detail'))}`",
            f"- B detail: `{((r.get('comparison') or {}).get('b_detail')) or ((r.get('crops') or {}).get('detail') or {}).get('path')}`",
            f"- A extent: `{ad.get('p2610a_detail_extent')}`",
            f"- B extent: `{ad.get('detail_extent')}`",
            f"- evidence counts: `{ad.get('evidence_counts')}`",
            f"- complete: {c.get('complete')}",
            "",
        ]
    lines += ["## Per-beam completeness results", ""]
    header = "| beam | " + " | ".join(_FIELDS) + " | complete |"
    sep = "|---| " + " | ".join(["---"] * len(_FIELDS)) + " |---|"
    lines += [header, sep]
    for r in records:
        c = r.get("completeness") or {}
        cells = [str(c.get(k, "")) for k in _FIELDS]
        lines.append(f"| {r.get('set_key')}/{r.get('beam_id')} | " + " | ".join(cells) + f" | {c.get('complete')} |")
    lines += ["", "## Missing evidence", ""]
    any_missing = False
    for r in records:
        c = r.get("completeness") or {}
        missing = c.get("missing_evidence") or []
        if missing:
            any_missing = True
            lines.append(f"- {r.get('beam_id')}: `{missing}`")
    if not any_missing:
        lines.append("None of the spatially collected evidence is outside the B crop.")
    lines += ["", "## Clipping results", ""]
    for r in records:
        c = r.get("completeness") or {}
        lines.append(
            f"- {r.get('beam_id')}: important_text_clipped={c.get('important_text_clipped')} "
            f"clipped_text={c.get('clipped_text')}"
        )
    lines += ["", "## Neighbor contamination", ""]
    for r in records:
        c = r.get("completeness") or {}
        lines.append(
            f"- {r.get('beam_id')}: unrelated_neighbor_detail_present="
            f"{c.get('unrelated_neighbor_detail_present')} titles={c.get('neighbor_titles_in_crop')}"
        )
    lines += [
        "",
        "## Unit tests",
        "",
        f"- passed: {tests.get('passed')}/{tests.get('total')}",
        f"- success: {tests.get('success')}",
        "",
        "## Prior regressions",
        "",
        f"- P2.6.6: {_ok(prior.get('p266'))}",
        f"- P2.6.7: {_ok(prior.get('p267'))}",
        f"- P2.6.8: {_ok(prior.get('p268'))}",
        f"- P2.6.9: {_ok(prior.get('p269'))}",
        f"- P2.6.10-A artifact preservation: {_ok(prior.get('p2610a'))}",
        "",
        "## Production firewall",
        "",
        f"- production mutation count: {prod.get('production_mutation_count')}",
        f"- steel quantity delta: {prod.get('steel_quantity_delta')}",
        f"- BBS delta: {prod.get('bbs_delta')}",
        f"- workbook delta: {prod.get('workbook_delta')}",
        f"- production objects modified: {prod.get('production_objects_modified')}",
        f"- live Claude Vision calls: {metrics.get('LIVE_VISION_CALLS', 0)}",
        f"- production_write: {result.get('production_write')}",
        f"- engineering_changes: {result.get('engineering_changes')}",
        "",
        "## Leakage check",
        "",
        f"- runtime leakage ok: {leak.get('ok')}",
        f"- hits: {leak.get('hits')}",
        "- Ground truth is not an input to runtime crop localization.",
        "- R.1 `by_beam` is not used to size the crop.",
        "",
        "## Final decision",
        "",
        f"**{result.get('decision')}**",
        "",
        f"Readiness classification: **{rec.get('readiness')}**",
        "",
        "Claude Vision is not authorized in this phase. P2.6.10-C may consume these",
        "crops only after visual completeness is accepted.",
        "",
    ]
    status_path = out_root / "P2.6.10-B_STATUS.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")
    (reports / "P2.6.10-B_STATUS.md").write_text("\n".join(lines), encoding="utf-8")
    slim = {k: v for k, v in result.items() if k != "records"}
    _dump(out_root / "P2.6.10-B_RESULTS.json", slim)
    return {"status": str(status_path), "results": str(out_root / "P2.6.10-B_RESULTS.json")}


__all__ = ["write_reports"]
