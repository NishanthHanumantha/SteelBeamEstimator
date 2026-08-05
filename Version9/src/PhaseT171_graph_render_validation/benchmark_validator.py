"""
T1.7.1 — Benchmark validation checks for graph-aware renders.
MODEL_VERSION: 9.4.1
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "9.4.1"

REQUIRED_FILES = (
    "Original_Render.png",
    "GraphAware_Render.png",
    "Overlay_Render.png",
    "SideBySide.png",
    "Difference_Report.json",
)


def validate_beam_artefacts(beam_dir: Path, diff: Dict[str, Any]) -> Dict[str, Any]:
    beam_dir = Path(beam_dir)
    files_ok = {name: (beam_dir / name).exists() for name in REQUIRED_FILES}
    flags = diff.get("flags") or {}
    texts = diff.get("graph_texts") or []
    joined = " ".join(texts).upper()

    def _has_ld() -> bool:
        return any(re.search(r"\bLD\b", t) for t in texts) or "DEVELOPMENT" in joined

    def _has_side() -> bool:
        return "SIDE FACE" in joined or "SIDE.FACE" in joined

    checks = {
        "artefacts_present": all(files_ok.values()),
        "top_bar_callout_visible": bool(flags.get("top_bar_callout")),
        "stirrup_visible": bool(flags.get("stirrup")),
        "physical_bar_chain_visible": bool(flags.get("physical_bar_chain")),
        "leader_chain_complete": bool(flags.get("leader_chain")),
        "semantics_connected": bool(flags.get("semantics_connected")),
        "side_face_visible": (not _has_side()) or bool(flags.get("side_face")),
        "ld_visible": (not _has_ld()) or bool(flags.get("ld")),
        "multi_leader_rendered": (
            (diff.get("leader_bar_chains") or 0) < 2
            or bool(flags.get("multi_leader"))
        ),
    }
    overall = "PASS" if all(checks.values()) else "FAIL"
    return {
        "beam_id": diff.get("beam"),
        "files": files_ok,
        "checks": checks,
        "validation": overall,
        "difference_validation": diff.get("validation"),
        "newly_visible": diff.get("newly_visible"),
        "model_version": MODEL_VERSION,
    }


def summarize_benchmark(per_beam: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "model_version": MODEL_VERSION,
        "beam_count": len(per_beam),
        "pass_count": sum(1 for r in per_beam if r.get("validation") == "PASS"),
        "fail_count": sum(1 for r in per_beam if r.get("validation") != "PASS"),
        "by_beam": {r["beam_id"]: r for r in per_beam},
    }
