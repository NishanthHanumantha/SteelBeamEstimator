"""D.2 shadow reports. No production routing. No PNG copies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ENGINEERING_CHANGES, LIVE_CLAUDE_CALL, MODEL_VERSION, PHASE_ID, PHASE_NAME, PRODUCTION_WRITE


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_beam_review(*, out_root: Path, rec: Dict[str, Any], hybrid: Dict[str, Any], audit: Dict[str, Any]) -> None:
    folder = Path(out_root) / "review" / str(hybrid.get("beam_id"))
    _dump(folder / "vision_input.json", rec.get("parsed") or {})
    _dump(folder / "deterministic_input.json", rec.get("detected_groups") or [])
    _dump(folder / "hybrid_result.json", hybrid)
    _dump(folder / "resolution_audit.json", audit)


def write_validation_report(*, out_root: Path, result: Dict[str, Any]) -> None:
    metrics = result.get("metrics") or {}
    pop = result.get("population") or {}
    lines = [
        f"# {PHASE_ID} — {PHASE_NAME}",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        "SHADOW ONLY. Structural hybrid application of the D.1 authority contract.",
        "Not accuracy. Not production integration.",
        "",
        f"- LIVE_CLAUDE_CALL = {LIVE_CLAUDE_CALL}",
        f"- PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        f"- ENGINEERING_CHANGES = {ENGINEERING_CHANGES}",
        "",
        "## Population",
        "",
        f"- discovered: {pop.get('discovered_count')}",
        f"- expected: {pop.get('expected')}",
        f"- ok: {pop.get('ok')}",
        f"- beam_ids: {pop.get('beam_ids')}",
        "",
        "## Groups",
        "",
        json.dumps(metrics.get("groups") or {}, indent=2),
        "",
        "## Field resolution",
        "",
        json.dumps(metrics.get("field_resolution") or {}, indent=2),
        "",
        "## Provenance (not accuracy)",
        "",
        json.dumps(metrics.get("provenance") or {}, indent=2),
        "",
        "## Stirrups",
        "",
        json.dumps(metrics.get("stirrups") or {}, indent=2),
        "",
        "## Engineering fields",
        "",
        json.dumps(metrics.get("engineering_fields") or {}, indent=2),
        "",
        "No production interpretation change.",
        "",
    ]
    (Path(out_root) / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> None:
    out_root = Path(out_root)
    _dump(out_root / "hybrid_resolution_manifest.json", result.get("manifest"))
    _dump(out_root / "hybrid_beam_results.json", result.get("hybrid_results"))
    _dump(out_root / "hybrid_resolution_audit.json", result.get("resolution_audits"))
    _dump(out_root / "field_conflicts.json", result.get("conflicts"))
    _dump(out_root / "fallback_audit.json", result.get("fallbacks"))
    _dump(out_root / "group_matching_audit.json", result.get("matching_audits"))
    _dump(out_root / "provenance_summary.json", (result.get("metrics") or {}).get("provenance"))
    _dump(out_root / "hybrid_metrics.json", result.get("metrics"))
    _dump(out_root / "benchmark_population_manifest.json", result.get("population"))
    write_validation_report(out_root=out_root, result=result)
    slim = {
        k: result.get(k)
        for k in (
            "phase_id",
            "phase_name",
            "model_version",
            "gate_version",
            "decision",
            "pass_fail",
            "metrics",
            "population",
            "production",
            "fingerprints",
            "unit_tests",
            "live_claude_call",
            "runtime_s",
        )
    }
    if isinstance(slim.get("unit_tests"), dict):
        slim["unit_tests"] = {k: slim["unit_tests"].get(k) for k in ("success", "passed", "total")}
    pop = slim.get("population")
    if isinstance(pop, dict):
        slim["population"] = {k: pop.get(k) for k in ("ok", "expected", "discovered_count", "beam_ids", "reason")}
    fp = slim.get("fingerprints")
    if isinstance(fp, dict):
        slim["fingerprints"] = {"unchanged": fp.get("unchanged"), "changed_keys": fp.get("changed_keys")}
    _dump(out_root / "P2.6.10-D.2_RESULTS.json", slim)


__all__ = ["write_beam_review", "write_reports"]
