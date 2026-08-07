"""
Global aggregation + recommendations for QA.3.2.
MODEL_VERSION: 10.0.2
"""
from __future__ import annotations

from typing import Any, Dict, List


def _avg(vals: List[float]) -> float:
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def aggregate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    cats = {"A": 0, "B": 0, "C": 0}
    statuses = {"VALID": 0, "PARTIALLY VALID": 0, "INVALID": 0}
    ious: List[float] = []
    overlaps: List[float] = []
    align_errs: List[float] = []
    centroid_errs: List[float] = []
    pad_errs: List[float] = []
    comps: List[float] = []
    centering: List[float] = []
    whitespace: List[float] = []
    clipping: List[float] = []
    intrusion: List[float] = []
    regenerated = 0
    qa31_trust = 0

    for r in records:
        d = r.get("decision") or {}
        cats[d.get("category") or "C"] = cats.get(d.get("category") or "C", 0) + 1
        st = d.get("status") or "INVALID"
        statuses[st] = statuses.get(st, 0) + 1
        m = r.get("alignment_metrics") or {}
        if m.get("iou") is not None:
            ious.append(float(m["iou"]))
        if m.get("overlap_pct_actual_in_expected") is not None:
            overlaps.append(float(m["overlap_pct_actual_in_expected"]))
        if m.get("centroid_error") is not None:
            centroid_errs.append(float(m["centroid_error"]))
            align_errs.append(float(m["centroid_error"]))
        if m.get("width_diff") is not None and m.get("height_diff") is not None:
            pad_errs.append(
                (abs(float(m["width_diff"])) + abs(float(m["height_diff"]))) / 2.0
            )
        ec = r.get("entity_completeness") or {}
        if ec.get("completeness_pct") is not None:
            comps.append(float(ec["completeness_pct"]))
        ba = r.get("beam_alignment") or {}
        if ba.get("centering_pct") is not None:
            centering.append(float(ba["centering_pct"]))
        if ba.get("whitespace_pct") is not None:
            whitespace.append(float(ba["whitespace_pct"]))
        clipping.append(100.0 if ba.get("beam_clipped") else 0.0)
        intrusion.append(100.0 if ba.get("neighbour_beam_intrusion") else 0.0)
        if (r.get("manual_source") or {}).get("regenerated"):
            regenerated += 1
        if d.get("qa31_ownership_conclusion_still_valid"):
            qa31_trust += 1

    n = len(records)
    return {
        "beams_analysed": n,
        "manual_crops_fully_correct": statuses.get("VALID", 0),
        "manual_crops_partially_correct": statuses.get("PARTIALLY VALID", 0),
        "manual_crops_incorrect": statuses.get("INVALID", 0),
        "category_counts": cats,
        "status_counts": statuses,
        "average_crop_overlap": _avg(overlaps),
        "average_iou": _avg(ious),
        "average_alignment_error": _avg(align_errs),
        "average_centroid_error": _avg(centroid_errs),
        "average_padding_error": _avg(pad_errs),
        "average_completeness_pct": _avg(comps),
        "average_beam_centering_pct": _avg(centering),
        "average_whitespace_pct": _avg(whitespace),
        "average_clipping_pct": _avg(clipping),
        "average_neighbour_intrusion_pct": _avg(intrusion),
        "regenerated_manual_crops": regenerated,
        "qa31_trustworthy_beam_count": qa31_trust,
        "baseline_trustworthy": qa31_trust == n and n > 0,
        "dominant_finding": (
            "manual_crops_are_regenerated_tight_envelopes_not_true_autocad_gt"
            if regenerated >= max(1, n // 2)
            else "mixed_or_external_manual_sources"
        ),
    }


def build_recommendations(
    agg: Dict[str, Any], records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    cats = agg.get("category_counts") or {}
    c_count = int(cats.get("C") or 0)
    b_count = int(cats.get("B") or 0)
    a_count = int(cats.get("A") or 0)
    regen = int(agg.get("regenerated_manual_crops") or 0)
    n = int(agg.get("beams_analysed") or 0)

    if c_count + b_count >= max(1, n // 2):
        p1 = {
            "priority": 1,
            "title": "Correct Manual Comparison Crop generation before Ownership work",
            "recommendation": (
                "Manual crops for unseen sets are regenerated from T1 geometry "
                "envelopes (tight beam bbox), not true AutoCAD ground-truth crops. "
                "Ownership investigation should be postponed until crop generation "
                "is corrected or a verified GT crop source is established."
            ),
            "evidence": {
                "category_C": c_count,
                "category_B": b_count,
                "regenerated": regen,
                "average_iou": agg.get("average_iou"),
                "average_completeness_pct": agg.get("average_completeness_pct"),
            },
        }
        p2 = {
            "priority": 2,
            "title": "Coordinate / extent mismatch between Manual and Owned Render",
            "recommendation": (
                "Documented divergence: Manual uses geometry_envelopes.extent; "
                "Owned Render uses T182 computed_render_bbox. Align comparison "
                "baseline extent with the reinforcement context under evaluation."
            ),
            "evidence": {
                "average_centroid_error": agg.get("average_centroid_error"),
                "average_padding_error": agg.get("average_padding_error"),
            },
        }
        p3 = {
            "priority": 3,
            "title": "Resume Ownership Engine investigation after GT baseline fix",
            "recommendation": (
                "Once Manual crops are trustworthy (Category A), re-run QA.3.1-style "
                "ownership diagnostics. Until then, QA.3.1 Ownership FAIL counts "
                "may mix true ownership defects with baseline crop defects."
            ),
            "evidence": {"qa31_trustworthy_beam_count": agg.get("qa31_trustworthy_beam_count")},
        }
    else:
        p1 = {
            "priority": 1,
            "title": "Manual crop generation verified",
            "recommendation": (
                "Ground-truth crops are sufficiently correct; Ownership investigation "
                "should continue."
            ),
            "evidence": {"category_A": a_count},
        }
        p2 = {
            "priority": 2,
            "title": "Spot-check partially valid beams",
            "recommendation": "Review Category B beams for padding / whitespace issues.",
            "evidence": {"category_B": b_count},
        }
        p3 = {
            "priority": 3,
            "title": "Maintain additive crop provenance logging",
            "recommendation": (
                "Persist manual crop source (benchmark vs regenerated) and extent "
                "metadata on every comparison export."
            ),
            "evidence": {"regenerated": regen},
        }

    return {
        "priorities": [p1, p2, p3],
        "summary": (
            f"A={a_count} B={b_count} C={c_count}; regenerated_manual={regen}/{n}; "
            f"avg_iou={agg.get('average_iou')}; avg_completeness={agg.get('average_completeness_pct')}"
        ),
    }
