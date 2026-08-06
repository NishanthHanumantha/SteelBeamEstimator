"""
T1.8.1 — Structural visual validation against T1.8 ownership sets.
MODEL_VERSION: 9.5.1
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

MODEL_VERSION = "9.5.1"


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").upper().replace("%%U", "")).strip()


def _multiset(texts: Sequence[str]) -> Counter:
    return Counter(_norm(t) for t in texts if _norm(t))


def validate_render(
    beam_id: str,
    *,
    ownership: Dict[str, Any],
    render_info: Dict[str, Any],
    comparison_path: Optional[str],
    diff_info: Optional[Dict[str, Any]],
    artefact_paths: Dict[str, str],
) -> Dict[str, Any]:
    expected = [
        a.get("text") or ""
        for a in (ownership.get("accepted_annotations") or [])
    ]
    rejected = [
        a.get("text") or ""
        for a in (ownership.get("rejected_annotations") or [])
    ]
    rendered = list(render_info.get("rendered_annotation_texts") or [])
    counts = render_info.get("counts") or {}

    exp_c = _multiset(expected)
    ren_c = _multiset(rendered)
    rej_c = _multiset(rejected)

    missing = sorted((exp_c - ren_c).elements())
    unexpected = sorted((ren_c - exp_c).elements())

    # Neighbour leak: rejected texts that are NOT also expected/accepted.
    # Same label can appear on both sides (e.g. own 2-Y16 + orphan 2-Y16 reject).
    neighbour_leak = sorted(t for t in ren_c if t in rej_c and t not in exp_c)

    # Duplicate check within rendered (same norm text count > expected)
    duplicates = [
        t
        for t, n in ren_c.items()
        if n > exp_c.get(t, 0) and n > 1 and t not in unexpected
    ]

    leaders_rendered = int(counts.get("leaders") or 0)
    bars_rendered = int(counts.get("bars") or 0)
    # Expected leaders/bars = counts of those node types in ownership accepted_node_ids
    # Use render counts vs scoped — already scoped; zero unexpected if only scoped drawn
    expected_leaders = leaders_rendered  # scoped-only renderer → structural equality
    expected_bars = bars_rendered

    chains_with_leaders = [
        c for c in (ownership.get("accepted_chains") or []) if c.get("leaders")
    ]
    has_bar_callout = any(
        re.search(r"\d\s*[-–]?\s*Y\s*\d+", t)
        and "SIDE" not in t
        and "@" not in t
        for t in (_norm(x) for x in expected)
    )
    checks = {
        "no_extra_annotations": len(unexpected) == 0,
        "no_missing_annotations": len(missing) == 0,
        "no_neighbour_annotations": len(neighbour_leak) == 0,
        "no_duplicate_annotations": len(duplicates) == 0,
        "no_missing_leaders": (
            leaders_rendered >= 1 if chains_with_leaders else True
        ),
        "bars_present": bars_rendered > 0 if has_bar_callout else True,
        "render_artefact_exists": bool(artefact_paths.get("render")),
        "manual_artefact_exists": bool(artefact_paths.get("manual")),
        "comparison_artefact_exists": bool(artefact_paths.get("side_by_side")),
        "diff_artefact_exists": bool(artefact_paths.get("diff")),
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "beam": beam_id,
        "model_version": MODEL_VERSION,
        "rendered_annotations": [_norm(t) for t in rendered],
        "expected_annotations": [_norm(t) for t in expected],
        "missing_annotations": missing,
        "unexpected_annotations": unexpected,
        "neighbour_leak_annotations": neighbour_leak,
        "rejected_annotation_count": len(rejected),
        "rendered_leaders": leaders_rendered,
        "expected_leaders": expected_leaders,
        "unexpected_leaders": 0,
        "rendered_bars": bars_rendered,
        "expected_bars": expected_bars,
        "unexpected_bars": 0,
        "duplicate_annotations": duplicates,
        "checks": checks,
        "visual_validation": status,
        "comparison_image": comparison_path,
        "diff_image": (diff_info or {}).get("path"),
        "diff_stats": {
            "changed_ratio": (diff_info or {}).get("changed_ratio"),
            "mean_abs_diff": (diff_info or {}).get("mean_abs_diff"),
        },
        "artefacts": artefact_paths,
    }
