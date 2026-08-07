"""
Aggregate per-beam diagnostics into global summaries.
MODEL_VERSION: 10.0.1
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def _avg(vals: List[float]) -> float:
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def aggregate(beam_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    freq = Counter()
    owned_bar = []
    rejected_bar = []
    ann_own = []
    crop_util = []
    render_util = []
    missing = 0
    diagnosable = 0

    for rec in beam_records:
        root = rec.get("root_cause") or {}
        primary = root.get("primary_category") or "Unknown"
        if primary == "None":
            freq["None (no stage FAIL)"] += 1
        else:
            freq[primary] += 1

        stages = rec.get("stages") or {}
        own = stages.get("Ownership") or {}
        crop = stages.get("Crop Window") or {}
        rend = stages.get("Rendering") or {}

        if own.get("owned_bar_pct") is not None:
            owned_bar.append(float(own["owned_bar_pct"]))
        if own.get("rejected_bar_pct") is not None:
            rejected_bar.append(float(own["rejected_bar_pct"]))
        if own.get("annotation_ownership_pct") is not None:
            ann_own.append(float(own["annotation_ownership_pct"]))
        if crop.get("crop_utilisation_pct") is not None:
            crop_util.append(float(crop["crop_utilisation_pct"]))
        if rend.get("render_utilisation_pct") is not None:
            render_util.append(float(rend["render_utilisation_pct"]))

        arts = rec.get("artefacts") or {}
        if not arts.get("has_beam_ownership") and not arts.get("has_geometry_envelope"):
            missing += 1
        else:
            diagnosable += 1

    # Hypothesis
    ownership_like = sum(
        freq[k]
        for k in (
            "Ownership",
            "Annotation Association",
            "Crop Window",
            "Beam Extent",
            "Beam Discovery",
        )
    )
    rendering = freq.get("Rendering", 0)
    n = max(len(beam_records), 1)
    dominant = ownership_like >= rendering and ownership_like >= max(1, n // 3)
    renderer_faithful = rendering <= max(1, n // 5)

    # Count beams where ownership FAIL and rendering PASS
    own_fail_rend_pass = 0
    for rec in beam_records:
        st = rec.get("stages") or {}
        if (st.get("Ownership") or {}).get("status") == "FAIL" and (
            st.get("Rendering") or {}
        ).get("status") == "PASS":
            own_fail_rend_pass += 1

    if own_fail_rend_pass >= max(2, len(beam_records) // 3):
        dominant = True
        renderer_faithful = True

    conf = "High" if diagnosable >= 8 else ("Medium" if diagnosable >= 4 else "Low")

    failure_frequency = {
        "Beam Discovery": freq.get("Beam Discovery", 0),
        "Beam Extents": freq.get("Beam Extent", 0),
        "Crop Window": freq.get("Crop Window", 0),
        "Ownership": freq.get("Ownership", 0),
        "Annotation Association": freq.get("Annotation Association", 0),
        "Rendering": freq.get("Rendering", 0),
        "Mixed": freq.get("Mixed", 0),
        "None (no stage FAIL)": freq.get("None (no stage FAIL)", 0),
    }

    return {
        "beams_analysed": len(beam_records),
        "beams_diagnosable": diagnosable,
        "beams_with_missing_artefacts": missing,
        "failure_frequency": failure_frequency,
        "averages": {
            "average_owned_bar_pct": _avg(owned_bar),
            "average_rejected_bar_pct": _avg(rejected_bar),
            "average_annotation_ownership_pct": _avg(ann_own),
            "average_crop_utilisation_pct": _avg(crop_util),
            "average_render_utilisation_pct": _avg(render_util),
        },
        "hypothesis": {
            "ownership_or_scoping_before_render_is_dominant": bool(dominant),
            "renderer_mostly_faithful_to_owned_set": bool(renderer_faithful),
            "evidence_confidence": conf,
            "ownership_fail_render_pass_count": own_fail_rend_pass,
        },
        "top_primary_root_cause": (
            max(
                (
                    (k, v)
                    for k, v in failure_frequency.items()
                    if k != "None (no stage FAIL)"
                ),
                key=lambda kv: kv[1],
                default=("Unknown", 0),
            )[0]
        ),
    }


def build_recommendations(agg: Dict[str, Any], beam_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    freq = agg.get("failure_frequency") or {}
    ranked = sorted(
        ((k, v) for k, v in freq.items() if v > 0 and not k.startswith("None")),
        key=lambda kv: -kv[1],
    )
    hyp = agg.get("hypothesis") or {}

    def beams_for(cat: str) -> List[str]:
        return [
            r["beam_id"]
            for r in beam_records
            if (r.get("root_cause") or {}).get("primary_category") == cat
            or (r.get("root_cause") or {}).get("first_failing_stage") == cat
        ]

    priorities = []
    defaults = [
        (
            "Ownership",
            "Tighten beam-scoped ownership / neighbour rejection so crop-local bars and annotations are retained.",
            "High impact on Bar Detection / Missing bars",
        ),
        (
            "Annotation Association",
            "Repair leader-to-beam association for multi-beam clusters and neighbour-side marks.",
            "Medium-High impact on Bar Matching / diameter roles",
        ),
        (
            "Crop Window",
            "Review adaptive extent margins where annotation/leader clipping is flagged.",
            "Medium impact on incomplete crops before ownership",
        ),
    ]
    used = set()
    for cat, count in ranked[:3]:
        used.add(cat)
        priorities.append(
            {
                "priority": len(priorities) + 1,
                "target_stage": cat,
                "supporting_beam_ids": beams_for(cat),
                "frequency": count,
                "recommendation": f"Investigate {cat} failures first (n={count}).",
                "estimated_impact": "High" if count >= 4 else "Medium",
                "deferred_note": "Deferred to next engineering phase",
            }
        )
    for cat, rec, impact in defaults:
        if len(priorities) >= 3:
            break
        if cat in used:
            continue
        priorities.append(
            {
                "priority": len(priorities) + 1,
                "target_stage": cat,
                "supporting_beam_ids": beams_for(cat),
                "frequency": freq.get(cat, 0),
                "recommendation": rec,
                "estimated_impact": impact,
                "deferred_note": "Deferred to next engineering phase",
            }
        )

    if hyp.get("ownership_or_scoping_before_render_is_dominant") and priorities:
        priorities[0]["recommendation"] = (
            "Priority confirmed by diagnostics: ownership/scoping fails before render on multiple beams. "
            + priorities[0]["recommendation"]
        )

    return {"priorities": priorities, "hypothesis": hyp}
