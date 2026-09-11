"""D.1 shadow reports. No production routing."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from .config import ENGINEERING_CHANGES, LIVE_CLAUDE_CALL, MODEL_VERSION, PHASE_ID, PHASE_NAME, PRODUCTION_WRITE
from .hybrid_authority_contract import DETERMINISTIC_AUTHORITY_FIELDS, VISION_PREFERRED_FIELDS


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


FIELD_KEYS = ("TARGET_IDENTITY", "LAYER", "ROLE", "BAR_COUNT", "DIAMETER", "SPECIFICATION", "SUPPORT_SCOPE", "STIRRUP_IDENTIFICATION")


def field_counts(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Counter] = {f: Counter() for f in FIELD_KEYS}

    def bump(field: str, rec: Dict[str, Any]) -> None:
        if rec.get("reason") == "VISION_ACCEPTED":
            out[field]["VISION_ACCEPTED"] += 1
        elif str(rec.get("authority_used") or "").startswith("DETERMINISTIC"):
            if rec.get("reason") in ("DETERMINISTIC_AUTHORITY",):
                out[field]["DETERMINISTIC_AUTHORITY"] += 1
            else:
                out[field]["DETERMINISTIC_FALLBACK"] += 1
            out[field]["VISION_REJECTED"] += 1
        else:
            out[field]["OTHER"] += 1
        if rec.get("conflict_recorded"):
            out[field]["CONFLICT_RECORDED"] += 1

    for beam in results:
        bump("TARGET_IDENTITY", beam.get("target_identity") or {})
        for g in beam.get("groups") or []:
            bump("LAYER", g.get("layer") or {})
            bump("ROLE", g.get("role") or {})
            bump("BAR_COUNT", g.get("bar_count") or {})
            bump("DIAMETER", g.get("diameter") or {})
            bump("SPECIFICATION", g.get("specification") or {})
            bump("SUPPORT_SCOPE", g.get("support_scope") or {})
        for s in beam.get("stirrups") or []:
            bump("STIRRUP_IDENTIFICATION", s.get("identification") or {})
    return {k: dict(v) for k, v in out.items()}


def validation_failures(validations: List[Dict[str, Any]]) -> Dict[str, int]:
    c: Counter = Counter()
    for rec in validations:
        if rec.get("accepted") is False:
            c[str(rec.get("reason") or "UNKNOWN")] += 1
    return dict(c)


def collect_validations(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for beam in results:
        t = beam.get("target_identity") or {}
        if t.get("validation"):
            rows.append({"beam_id": beam.get("beam_id"), **t["validation"]})
        for g in beam.get("groups") or []:
            for field in ("layer", "role", "bar_count", "diameter", "specification", "support_scope"):
                val = (g.get(field) or {}).get("validation")
                if val:
                    rows.append({"beam_id": beam.get("beam_id"), "group_id": g.get("group_id"), **val})
        for s in beam.get("stirrups") or []:
            val = (s.get("identification") or {}).get("validation")
            if val:
                rows.append({"beam_id": beam.get("beam_id"), **val})
    return rows


def write_validation_report(*, out_root: Path, result: Dict[str, Any]) -> None:
    metrics = result.get("metrics") or {}
    pop = result.get("population") or {}
    lines = [
        f"# {PHASE_ID} — {PHASE_NAME}",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        "SHADOW ONLY. Automated reconciliation is not ground-truth accuracy.",
        "",
        f"- LIVE_CLAUDE_CALL = {LIVE_CLAUDE_CALL}",
        f"- PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        f"- ENGINEERING_CHANGES = {ENGINEERING_CHANGES}",
        "",
        "## Population",
        "",
        f"- C.3 observations: {pop.get('c3_count')}",
        f"- C.5 observations: {pop.get('c5_count')}",
        f"- deduplicated: {pop.get('deduplicated_count')}",
        f"- beam_ids: {pop.get('beam_ids')}",
        "",
        "## Vision-preferred fields",
        "",
        ", ".join(VISION_PREFERRED_FIELDS),
        "",
        "## Deterministic-authority fields",
        "",
        ", ".join(DETERMINISTIC_AUTHORITY_FIELDS),
        "",
        "## Field-level resolution",
        "",
    ]
    for field, counts in (metrics.get("field_counts") or {}).items():
        lines += [
            f"### {field}",
            "",
            f"- VISION_ACCEPTED: {counts.get('VISION_ACCEPTED', 0)}",
            f"- VISION_REJECTED: {counts.get('VISION_REJECTED', 0)}",
            f"- DETERMINISTIC_FALLBACK: {counts.get('DETERMINISTIC_FALLBACK', 0)}",
            f"- CONFLICT_RECORDED: {counts.get('CONFLICT_RECORDED', 0)}",
            "",
        ]
    lines += [
        "## Group preservation",
        "",
        f"- VISION_ONLY_GROUPS: {metrics.get('vision_only_groups')}",
        f"- DETERMINISTIC_ONLY_GROUPS: {metrics.get('deterministic_only_groups')}",
        f"- POSSIBLE_DUPLICATE_GROUPS: {metrics.get('possible_duplicates')}",
        "",
        "## Validation failures by category",
        "",
        json.dumps(metrics.get("validation_failures") or {}, indent=2),
        "",
        "## Diameter",
        "",
        "Valid Vision diameter overrides conflicting deterministic diameter when validation passes.",
        json.dumps(metrics.get("field_counts", {}).get("DIAMETER") or {}, indent=2),
        "",
        "## MAIN / EXTRA role",
        "",
        "Valid Vision role overrides conflicting deterministic role when validation passes.",
        json.dumps(metrics.get("field_counts", {}).get("ROLE") or {}, indent=2),
        "",
        "No production interpretation change.",
        "",
    ]
    (Path(out_root) / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> None:
    out_root = Path(out_root)
    _dump(out_root / "hybrid_authority_contract.json", result.get("authority_contract"))
    _dump(out_root / "vision_contract_validation.json", result.get("validations"))
    _dump(out_root / "hybrid_semantic_results.json", result.get("hybrid_results"))
    _dump(out_root / "vision_deterministic_comparison.json", result.get("comparisons"))
    _dump(out_root / "resolution_audit.json", result.get("audit"))
    _dump(out_root / "resolution_summary.json", result.get("metrics"))
    _dump(out_root / "benchmark_population_manifest.json", result.get("population"))
    write_validation_report(out_root=out_root, result=result)
    slim = {k: result.get(k) for k in ("phase_id", "phase_name", "model_version", "gate_version", "decision", "pass_fail", "metrics", "population", "production", "fingerprints", "unit_tests", "live_claude_call")}
    if isinstance(slim.get("unit_tests"), dict):
        slim["unit_tests"] = {k: slim["unit_tests"].get(k) for k in ("success", "passed", "total")}
    pop = slim.get("population")
    if isinstance(pop, dict):
        slim["population"] = {k: pop.get(k) for k in ("c3_count", "c5_count", "deduplicated_count", "beam_ids")}
    _dump(out_root / "P2.6.10-D.1_RESULTS.json", slim)


__all__ = ["collect_validations", "field_counts", "validation_failures", "write_reports"]
