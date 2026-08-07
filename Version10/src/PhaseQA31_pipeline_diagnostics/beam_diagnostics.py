"""
Per-beam stage diagnostics from existing Track1 artefacts.
MODEL_VERSION: 10.0.1
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

STAGE_ORDER = (
    "Beam Discovery",
    "Beam Extent",
    "Crop Window",
    "Ownership",
    "Annotation Association",
    "Rendering",
)


def _by_beam(doc: Optional[Dict[str, Any]], beam_id: str) -> Optional[Any]:
    if not doc:
        return None
    bb = doc.get("by_beam")
    if isinstance(bb, dict) and beam_id in bb:
        return bb[beam_id]
    if beam_id in doc and not isinstance(doc.get(beam_id), (str, int, float)):
        return doc[beam_id]
    return None


def _extent_ok(extent: Any) -> bool:
    if not extent or not isinstance(extent, (list, tuple)) or len(extent) < 4:
        return False
    try:
        x0, y0, x1, y1 = map(float, extent[:4])
    except Exception:
        return False
    return (x1 - x0) > 1e-6 and (y1 - y0) > 1e-6


def _area(extent: Any) -> float:
    if not _extent_ok(extent):
        return 0.0
    x0, y0, x1, y1 = map(float, extent[:4])
    return abs((x1 - x0) * (y1 - y0))


def diagnose_beam(
    beam_id: str,
    drawing_set: str,
    set_key: str,
    bundle: Dict[str, Any],
    comparison_dir: Optional[Path],
    render_dir: Optional[Path],
) -> Dict[str, Any]:
    env = _by_beam(bundle.get("geometry_envelopes"), beam_id)
    own = _by_beam(bundle.get("beam_ownership"), beam_id)
    scoped = _by_beam(bundle.get("beam_scoped"), beam_id)
    own_diag = _by_beam(bundle.get("ownership_diagnostics"), beam_id)
    ext_qa = _by_beam(bundle.get("render_extent_qa"), beam_id)
    merged = _by_beam(bundle.get("merged_ownership"), beam_id)
    t16 = _by_beam(bundle.get("t16_ownership"), beam_id)
    graph = _by_beam(bundle.get("annotation_graph_by_beam"), beam_id)
    graph_qa = _by_beam(bundle.get("graph_qa"), beam_id)
    rend = _by_beam(bundle.get("render_validation"), beam_id)

    # --- 1 Discovery ---
    discovery = _diagnose_discovery(beam_id, env, own, scoped)
    # --- 2 Extents ---
    extents = _diagnose_extents(beam_id, env, own, ext_qa)
    # --- 3 Crop ---
    crop = _diagnose_crop(beam_id, env, ext_qa, t16, graph, comparison_dir)
    # --- 4 Ownership ---
    ownership = _diagnose_ownership(beam_id, own, own_diag, t16, merged)
    # --- 5 Annotation ---
    annotation = _diagnose_annotation(beam_id, own, scoped, graph_qa, merged)
    # --- 6 Rendering ---
    rendering = _diagnose_rendering(beam_id, own, rend, comparison_dir, render_dir)
    # --- 7 Root cause ---
    stages = {
        "Beam Discovery": discovery,
        "Beam Extent": extents,
        "Crop Window": crop,
        "Ownership": ownership,
        "Annotation Association": annotation,
        "Rendering": rendering,
    }
    root = classify_root_cause(stages)

    pngs = {}
    if comparison_dir and comparison_dir.exists():
        for kind in ("manual", "render", "side_by_side"):
            p = comparison_dir / f"{beam_id}_{kind}.png"
            if p.exists():
                pngs[kind] = str(p)

    return {
        "beam_id": beam_id,
        "drawing_set": drawing_set,
        "set_key": set_key,
        "stages": stages,
        "root_cause": root,
        "artefacts": {
            "comparison_pngs": pngs,
            "has_geometry_envelope": env is not None,
            "has_beam_ownership": own is not None,
            "has_render_extent_qa": ext_qa is not None,
            "has_render_validation": rend is not None,
        },
    }


def _diagnose_discovery(beam_id, env, own, scoped) -> Dict[str, Any]:
    if env is None and own is None and scoped is None:
        return {
            "status": "MISSING_ARTEFACT",
            "detected": False,
            "expected_beam_label": beam_id,
            "detected_beam_label": None,
            "geometry_found": False,
            "notes": "No discovery/ownership/envelope record for beam",
        }
    geom = False
    length = width = orientation = None
    conf = None
    if env:
        geom = _extent_ok(env.get("extent") or [env.get("xmin"), env.get("ymin"), env.get("xmax"), env.get("ymax")])
        orientation = env.get("orientation")
        conf = env.get("geometry_confidence")
        if geom:
            x0, y0, x1, y1 = map(float, (env.get("extent") or [env["xmin"], env["ymin"], env["xmax"], env["ymax"]])[:4])
            length = round(max(abs(x1 - x0), abs(y1 - y0)), 3)
            width = round(min(abs(x1 - x0), abs(y1 - y0)), 3)
    detected = bool(env or own or scoped)
    label = (own or {}).get("beam") or (scoped or {}).get("beam_id") or (env or {}).get("beam_id") or beam_id
    status = "PASS" if detected and geom else ("FAIL" if detected and not geom else ("PASS" if detected else "FAIL"))
    if detected and not geom:
        status = "FAIL"
    return {
        "status": status,
        "detected": detected,
        "expected_beam_label": beam_id,
        "detected_beam_label": label,
        "geometry_found": geom,
        "beam_length": length,
        "beam_width": width,
        "beam_orientation": orientation,
        "discovery_confidence": conf,
        "notes": "" if status == "PASS" else "Beam missing usable geometry envelope",
    }


def _diagnose_extents(beam_id, env, own, ext_qa) -> Dict[str, Any]:
    original = None
    if env:
        original = env.get("extent") or [
            env.get("xmin"), env.get("ymin"), env.get("xmax"), env.get("ymax")
        ]
    own_env = ((own or {}).get("envelope") or {})
    crop_from_own = own_env.get("crop_extent")
    final = None
    padding = None
    source = None
    if ext_qa:
        final = ext_qa.get("computed_render_bbox") or ext_qa.get("beam_bbox")
        padding = ext_qa.get("margin_applied")
        source = "T182_RenderExtentQA"
    elif crop_from_own:
        final = crop_from_own
        source = "T18_crop_extent"
    elif original:
        final = original
        source = "T1_geometry_envelope"

    null_extent = not _extent_ok(final)
    # Over-expansion heuristic vs geometry
    expanded = ((own or {}).get("envelope") or {}).get("concrete_envelope")
    over = False
    if _extent_ok(original) and _extent_ok(final):
        if _area(final) > 25.0 * max(_area(original), 1.0):
            over = True

    if final is None and original is None:
        status = "MISSING_ARTEFACT"
    elif null_extent:
        status = "FAIL"
    elif over:
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "status": status,
        "original_extents": original,
        "expanded_extents": expanded,
        "final_crop_window": final,
        "crop_padding": padding,
        "crop_clipping": {
            "annotation_clipped": (ext_qa or {}).get("annotation_clipped"),
            "leader_clipped": (ext_qa or {}).get("leader_clipped"),
        },
        "extent_source": source,
        "null_extent": null_extent,
        "notes": "null/degenerate extent" if null_extent else ("suspected over-expanded crop" if over else ""),
    }


def _diagnose_crop(beam_id, env, ext_qa, t16, graph, comparison_dir) -> Dict[str, Any]:
    final = None
    if ext_qa:
        final = ext_qa.get("computed_render_bbox")
    if not _extent_ok(final) and env:
        final = env.get("extent")

    # Entity counts from available registries (read-only, no DXF rewrite)
    counts = {
        "total_entities": 0,
        "bars": 0,
        "leaders": 0,
        "annotations": 0,
        "polylines": 0,
        "lines": 0,
        "mtext": 0,
        "text": 0,
        "dimensions": 0,
        "blocks": 0,
    }
    if isinstance(t16, list):
        counts["total_entities"] = len(t16)
        for e in t16:
            t = str(e.get("type") or e.get("role") or "").upper()
            if "BAR" in t or e.get("role") in ("BAR", "PHYSICAL_BAR", "STIRRUP"):
                counts["bars"] += 1
            elif "LEADER" in t or e.get("role") == "LEADER":
                counts["leaders"] += 1
            elif "TEXT" in t or "MTEXT" in t or e.get("role") in ("ANNOTATION", "TEXT", "MTEXT"):
                counts["annotations"] += 1
                if "MTEXT" in t:
                    counts["mtext"] += 1
                else:
                    counts["text"] += 1
            elif "LINE" in t:
                counts["lines"] += 1
            elif "POLY" in t:
                counts["polylines"] += 1
            elif "INSERT" in t or "BLOCK" in t:
                counts["blocks"] += 1
            elif "DIM" in t:
                counts["dimensions"] += 1

    if graph:
        counts["bars"] = max(counts["bars"], len(graph.get("physical_bars") or []))
        counts["leaders"] = max(counts["leaders"], len(graph.get("leaders") or []))
        counts["annotations"] = max(counts["annotations"], len(graph.get("annotations") or []))

    # Crop vs annotation extent comparison from envelopes file if present later
    clipped = False
    if ext_qa:
        clipped = bool(ext_qa.get("annotation_clipped") or ext_qa.get("leader_clipped"))
        failures = ext_qa.get("visibility_failures") or []
        if failures:
            clipped = True

    has_manual = False
    if comparison_dir:
        has_manual = (comparison_dir / f"{beam_id}_manual.png").exists()

    if not _extent_ok(final) and counts["total_entities"] == 0 and not graph:
        status = "MISSING_ARTEFACT"
    elif clipped or (counts["bars"] + counts["annotations"] + counts["leaders"] == 0 and _extent_ok(final)):
        # empty reinforcement content in crop is a crop/ownership precursor fail;
        # attribute to crop only when extent QA reports clipping
        status = "FAIL" if clipped else "PASS"
    else:
        status = "PASS"

    util = None
    if isinstance(t16, list) and t16:
        high = sum(1 for e in t16 if str(e.get("ownership", "")).upper() == "HIGH")
        util = round(100.0 * high / len(t16), 2)

    return {
        "status": status,
        **counts,
        "crop_excludes_required_entities": True if clipped else (False if status == "PASS" else "UNKNOWN"),
        "crop_utilisation_pct": util,
        "comparison_render_available": has_manual,
        "final_crop_window": final,
        "notes": "annotation/leader clipped by crop window" if clipped else "",
    }


def _diagnose_ownership(beam_id, own, own_diag, t16, merged) -> Dict[str, Any]:
    if own is None and t16 is None:
        return {
            "status": "MISSING_ARTEFACT",
            "owned_bars": 0,
            "rejected_bars": 0,
            "notes": "No ownership artefacts",
            "rejected_entities": [],
        }

    rejected_entities: List[Dict[str, Any]] = []
    owned_ann = rejected_ann = owned_leaders = rejected_leaders = 0
    owned_bars = rejected_bars = 0

    if own:
        acc = own.get("accepted_annotations") or []
        rej = own.get("rejected_annotations") or []
        owned_ann = len(acc)
        rejected_ann = len(rej)
        for r in rej:
            rejected_entities.append(
                {
                    "entity_id": r.get("id"),
                    "entity_type": "annotation",
                    "distance_from_beam": r.get("distance") or r.get("dist"),
                    "reason_rejected": r.get("ownership_reason") or r.get("reason"),
                    "ownership_rule_responsible": r.get("rejected_rule"),
                    "rejection_expected": "UNKNOWN",
                    "text": r.get("text"),
                }
            )
        for r in own.get("rejected_chains") or []:
            rejected_leaders += 1
            rejected_entities.append(
                {
                    "entity_id": r.get("annotation_id") or r.get("id"),
                    "entity_type": "leader_chain",
                    "distance_from_beam": r.get("distance"),
                    "reason_rejected": r.get("ownership_reason") or r.get("reason"),
                    "ownership_rule_responsible": r.get("rejected_rule"),
                    "rejection_expected": "UNKNOWN",
                }
            )
        owned_leaders = len(own.get("accepted_chains") or [])
        bar_results = own.get("bar_results") or {}
        for bid, row in bar_results.items():
            if row.get("accepted"):
                owned_bars += 1
            else:
                rejected_bars += 1
                rejected_entities.append(
                    {
                        "entity_id": bid,
                        "entity_type": "bar",
                        "distance_from_beam": row.get("distance"),
                        "reason_rejected": row.get("ownership_reason"),
                        "ownership_rule_responsible": row.get("rejected_rule"),
                        "rejection_expected": "UNKNOWN",
                    }
                )
        leader_results = own.get("leader_results") or {}
        for lid, row in leader_results.items():
            if row.get("accepted"):
                owned_leaders += 1
            else:
                rejected_leaders += 1
                rejected_entities.append(
                    {
                        "entity_id": lid,
                        "entity_type": "leader",
                        "distance_from_beam": row.get("distance"),
                        "reason_rejected": row.get("ownership_reason"),
                        "ownership_rule_responsible": row.get("rejected_rule"),
                        "rejection_expected": "UNKNOWN",
                    }
                )

    # T16 LOW ownership as soft rejects
    if isinstance(t16, list):
        high = [e for e in t16 if str(e.get("ownership", "")).upper() == "HIGH"]
        low = [e for e in t16 if str(e.get("ownership", "")).upper() != "HIGH"]
        if owned_bars == 0:
            owned_bars = sum(1 for e in high if "BAR" in str(e.get("role", "")).upper() or "BAR" in str(e.get("type", "")).upper())
        for e in low:
            rejected_entities.append(
                {
                    "entity_id": e.get("handle"),
                    "entity_type": e.get("type") or e.get("role") or "entity",
                    "distance_from_beam": None,
                    "reason_rejected": ",".join(e.get("reasons") or []) or "LOW_ownership",
                    "ownership_rule_responsible": "T16_LOW",
                    "rejection_expected": "UNKNOWN",
                }
            )

    total_bars = owned_bars + rejected_bars
    owned_bar_pct = round(100.0 * owned_bars / total_bars, 2) if total_bars else None
    rejected_bar_pct = round(100.0 * rejected_bars / total_bars, 2) if total_bars else None
    total_ann = owned_ann + rejected_ann
    ann_own_pct = round(100.0 * owned_ann / total_ann, 2) if total_ann else None

    stats = (own_diag or {}).get("stats") or {}
    rej_ann_stat = int(stats.get("rejected_annotation_count") or rejected_ann or 0)
    rej_bar_stat = int(stats.get("rejected_bar_count") or rejected_bars or 0)
    leakage = int(stats.get("cross_beam_leakage_count") or 0)

    # Ownership FAIL when beam-scoped content is rejected / leaked to neighbours.
    # Render may still PASS because it faithfully draws the (incomplete) owned set.
    status = "PASS"
    if rej_ann_stat >= 1 or rej_bar_stat >= 1 or leakage >= 1:
        status = "FAIL"
    if rejected_ann + rejected_bars + rejected_leaders > 0 and owned_ann + owned_bars == 0:
        status = "FAIL"
    if merged and (merged.get("counts") or {}).get("effective", 1) == 0 and rejected_ann:
        status = "FAIL"

    return {
        "status": status,
        "owned_bars": owned_bars,
        "rejected_bars": rejected_bars,
        "owned_leaders": owned_leaders,
        "rejected_leaders": rejected_leaders,
        "owned_annotations": owned_ann,
        "rejected_annotations": rejected_ann,
        "owned_bar_pct": owned_bar_pct,
        "rejected_bar_pct": rejected_bar_pct,
        "annotation_ownership_pct": ann_own_pct,
        "rejected_entities": rejected_entities,
        "merged_counts": (merged or {}).get("counts"),
        "notes": f"rejected_ann={rejected_ann} rejected_bars={rejected_bars} rejected_leaders={rejected_leaders}",
    }


def _diagnose_annotation(beam_id, own, scoped, graph_qa, merged) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    if own:
        for a in own.get("accepted_annotations") or []:
            items.append(
                {
                    "annotation_text": a.get("text"),
                    "leader_target": None,
                    "associated_beam": beam_id,
                    "association_confidence": a.get("ownership_score"),
                    "rejected": False,
                    "reason": a.get("ownership_reason") or "accepted",
                }
            )
        for a in own.get("rejected_annotations") or []:
            items.append(
                {
                    "annotation_text": a.get("text"),
                    "leader_target": a.get("neighbour_beam_source"),
                    "associated_beam": None,
                    "association_confidence": a.get("ownership_score"),
                    "rejected": True,
                    "reason": a.get("ownership_reason") or a.get("rejected_rule"),
                }
            )
    unattached = (graph_qa or {}).get("unattached_annotations") or []
    unresolved = (graph_qa or {}).get("unresolved_leaders") or []

    rejected_n = sum(1 for i in items if i.get("rejected"))
    accepted_n = sum(1 for i in items if not i.get("rejected"))
    neighbour_rejects = sum(
        1
        for i in items
        if i.get("rejected")
        and (
            "neighbour" in str(i.get("reason") or "").lower()
            or "NEIGHBOUR" in str(i.get("reason") or "").upper()
            or "R5_" in str(i.get("reason") or "").upper()
        )
    )
    if own is None and scoped is None and graph_qa is None:
        status = "MISSING_ARTEFACT"
    elif rejected_n > 0 and accepted_n == 0:
        status = "FAIL"
    elif neighbour_rejects >= 1:
        status = "FAIL"
    elif len(unattached) + len(unresolved) >= 3 and accepted_n <= 1:
        status = "FAIL"
    elif rejected_n >= max(2, accepted_n):
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "status": status,
        "annotations": items,
        "unattached_annotations": len(unattached),
        "unresolved_leaders": len(unresolved),
        "accepted_count": accepted_n,
        "rejected_count": rejected_n,
        "notes": "",
    }


def _diagnose_rendering(beam_id, own, rend, comparison_dir, render_dir) -> Dict[str, Any]:
    owned_count = 0
    if own:
        owned_count = (
            len(own.get("accepted_annotations") or [])
            + len(own.get("accepted_chains") or [])
            + sum(1 for v in (own.get("bar_results") or {}).values() if v.get("accepted"))
        )
    missing = (rend or {}).get("missing_annotations") or []
    expected = (rend or {}).get("expected_annotations") or []
    rendered = (rend or {}).get("rendered_annotations") or []
    leak = (rend or {}).get("neighbour_leak_annotations") or []

    render_path = None
    if comparison_dir and (comparison_dir / f"{beam_id}_render.png").exists():
        render_path = str(comparison_dir / f"{beam_id}_render.png")
    elif render_dir and (render_dir / f"{beam_id}_render.png").exists():
        render_path = str(render_dir / f"{beam_id}_render.png")

    if rend is None and render_path is None:
        status = "MISSING_ARTEFACT"
        mismatch = "UNKNOWN"
    else:
        # Renderer fails only if it drops owned/expected content
        if missing and expected:
            status = "FAIL"
            mismatch = "YES"
        elif leak:
            status = "FAIL"
            mismatch = "YES"
        else:
            status = "PASS"
            mismatch = "NO"

    util = None
    if expected:
        util = round(100.0 * len(rendered) / max(len(expected), 1), 2)
    elif owned_count:
        util = round(100.0 * len(rendered) / max(owned_count, 1), 2) if rendered else None

    return {
        "status": status,
        "owned_entities_count": owned_count,
        "rendered_entities_count": len(rendered) if rendered else None,
        "missing_rendered_entities": missing,
        "unexpected_rendered_entities": leak,
        "rendering_mismatch": mismatch,
        "render_utilisation_pct": util,
        "render_paths": [p for p in [render_path] if p],
        "rejected_annotation_count": (rend or {}).get("rejected_annotation_count"),
        "notes": "",
    }


def classify_root_cause(stages: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    fails = []
    for name in STAGE_ORDER:
        st = (stages.get(name) or {}).get("status")
        if st == "FAIL":
            fails.append(name)

    if not fails:
        # If all PASS/UNKNOWN but missing later artefacts, still OK
        missing = [
            n for n in STAGE_ORDER
            if (stages.get(n) or {}).get("status") == "MISSING_ARTEFACT"
        ]
        if missing and any(
            (stages.get(n) or {}).get("status") in ("PASS", "UNKNOWN")
            for n in STAGE_ORDER
            if n not in missing
        ):
            return {
                "primary_category": "Mixed" if len(missing) > 1 else missing[0],
                "first_failing_stage": missing[0],
                "confidence": "Low",
                "confidence_score": 0.35,
                "evidence_summary": [f"Missing artefacts at {m}" for m in missing[:3]],
                "secondary_contributors": missing[1:],
            }
        return {
            "primary_category": "None",
            "first_failing_stage": None,
            "confidence": "Medium",
            "confidence_score": 0.6,
            "evidence_summary": ["No FAIL stages detected in available artefacts"],
            "secondary_contributors": [],
            "all_pass": True,
        }

    first = fails[0]
    # Special rule: if Ownership FAIL and Rendering PASS -> root Ownership
    rend = (stages.get("Rendering") or {}).get("status")
    own = (stages.get("Ownership") or {}).get("status")
    if own == "FAIL" and rend == "PASS":
        primary = "Ownership"
        conf = "High"
        score = 0.9
    elif len(fails) >= 3:
        primary = "Mixed"
        conf = "Medium"
        score = 0.55
    else:
        primary = first
        conf = "High" if len(fails) == 1 else "Medium"
        score = 0.85 if len(fails) == 1 else 0.65

    evidence = []
    for name in fails[:4]:
        notes = (stages.get(name) or {}).get("notes") or ""
        evidence.append(f"{name}: {(stages.get(name) or {}).get('status')} {notes}".strip())

    out = {
        "primary_category": primary,
        "first_failing_stage": first,
        "confidence": conf,
        "confidence_score": score,
        "evidence_summary": evidence,
        "secondary_contributors": fails[1:],
        "all_pass": False,
    }
    if out.get("all_pass"):
        out["primary_category"] = "None"
    return out
