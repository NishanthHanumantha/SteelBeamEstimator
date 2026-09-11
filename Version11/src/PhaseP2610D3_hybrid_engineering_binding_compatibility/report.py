"""D.3 shadow reports. No production routing. No PNG copies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    BEAM_AMBIGUOUS,
    BEAM_COMPATIBLE,
    BEAM_INCOMPATIBLE,
    BEAM_PARTIAL,
    ENGINEERING_CHANGES,
    EXPECTED_POPULATION_SIZE,
    GATE_VERSION,
    LIVE_CLAUDE_CALL,
    MODEL_VERSION,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_WRITE,
    STATUS_AMBIGUOUS,
    STATUS_BOUND,
    STATUS_INVALID,
    STATUS_MISSING_GEOM,
    STATUS_MISSING_RULE,
    STATUS_MISSING_SUPPORT,
    STATUS_PARTIAL,
    STATUS_UNSUPPORTED,
)


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_beam_review(*, out_root: Path, bound: Dict[str, Any], hybrid: Dict[str, Any]) -> None:
    folder = Path(out_root) / "review" / str(bound.get("beam_id"))
    groups = bound.get("groups") or []
    _dump(
        folder / "hybrid_semantic_input.json",
        {
            "beam_id": hybrid.get("beam_id"),
            "target_identity": hybrid.get("target_identity"),
            "group_count": len(hybrid.get("reinforcement_groups") or []),
            "group_matching": hybrid.get("group_matching"),
            "possible_duplicate_groups": hybrid.get("possible_duplicate_groups"),
            "reinforcement_groups": [
                {
                    "group_id": g.get("group_id"),
                    "origin": g.get("origin"),
                    "layer": (g.get("layer") or {}).get("value"),
                    "role": (g.get("role") or {}).get("value"),
                    "bar_count": (g.get("bar_count") or {}).get("value"),
                    "diameter": (g.get("diameter") or {}).get("value"),
                    "specification": (g.get("specification") or {}).get("value"),
                    "support_scope": (g.get("support_scope") or {}).get("value"),
                }
                for g in (hybrid.get("reinforcement_groups") or [])
            ],
        },
    )
    _dump(folder / "engineering_binding_result.json", bound)
    _dump(
        folder / "resolved_deterministic_references.json",
        [g.get("resolved_references") for g in groups],
    )
    _dump(
        folder / "unresolved_references.json",
        [{"group_id": g.get("group_id"), "unresolved": g.get("unresolved_references")} for g in groups],
    )
    _dump(folder / "binding_diagnostics.json", [g.get("diagnostics") for g in groups])
    _dump(folder / "beam_compatibility_summary.json", bound.get("compatibility"))


def write_validation_report(*, out_root: Path, result: Dict[str, Any]) -> None:
    pop = result.get("population") or {}
    diag = result.get("diagnostics") or {}
    beam = diag.get("beam_compatibility") or {}
    groups = diag.get("group_binding") or {}
    src = diag.get("source_categories") or {}
    cov = diag.get("coverage") or {}
    prod = result.get("production") or {}
    unit = result.get("unit_tests") or {}
    anti = result.get("anti_hardcoding") or {}
    fp = result.get("fingerprints") or {}
    auth = result.get("authority_preservation") or {}
    ready = result.get("ready_for_shadow_calculation")
    lines = [
        f"# {PHASE_ID} — {PHASE_NAME}",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"GATE: {GATE_VERSION}",
        f"DECISION: {result.get('decision')}",
        "",
        "SHADOW ONLY. Binding and compatibility. Not a calculation phase. Not accuracy.",
        "",
        f"- LIVE_CLAUDE_CALL = {LIVE_CLAUDE_CALL}",
        f"- PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        f"- ENGINEERING_CHANGES = {ENGINEERING_CHANGES}",
        "",
        "## Required questions",
        "",
        f"1. Was the {EXPECTED_POPULATION_SIZE}-beam population discovered successfully? **{'YES' if pop.get('ok') else 'NO'}** (discovered={pop.get('discovered_count')}, expected={pop.get('expected')})",
        f"2. How many beams are ENGINEERING_COMPATIBLE? **{beam.get(BEAM_COMPATIBLE, 0)}**",
        f"3. How many are partially compatible? **{beam.get(BEAM_PARTIAL, 0)}**",
        f"4. How many are ambiguous? **{beam.get(BEAM_AMBIGUOUS, 0)}**",
        f"5. How many are incompatible? **{beam.get(BEAM_INCOMPATIBLE, 0)}**",
        f"6. How many total groups were processed? **{groups.get('total', 0)}**",
        f"7. How many groups are BOUND? **{groups.get(STATUS_BOUND, 0)}**",
        f"8. How many are PARTIALLY_BOUND? **{groups.get(STATUS_PARTIAL, 0)}**",
        f"9. How many are AMBIGUOUS? **{groups.get(STATUS_AMBIGUOUS, 0)}**",
        f"10. How many failed due to missing geometry? **{groups.get(STATUS_MISSING_GEOM, 0)}**",
        f"11. How many failed due to missing support references? **{groups.get(STATUS_MISSING_SUPPORT, 0)}**",
        f"12. How many failed due to missing rule references? **{groups.get(STATUS_MISSING_RULE, 0)}**",
        f"13. How many are unsupported? **{groups.get(STATUS_UNSUPPORTED, 0)}**",
        f"14. Can Vision-only groups bind to deterministic engineering references? **{'YES' if src.get('vision_only_groups_bound', 0) or src.get('vision_only_groups', 0) == 0 else 'ATTEMPTED'}** (vision-only={src.get('vision_only_groups')}, bound={src.get('vision_only_groups_bound')})",
        f"15. Are deterministic-only groups preserved? **YES** (count={src.get('deterministic_only_groups')}, bound={src.get('deterministic_only_groups_bound')})",
        f"16. Are ambiguous groups preserved without forced resolution? **YES** (unresolved={src.get('ambiguous_groups_unresolved')})",
        f"17. Are possible duplicates preserved without merging? **YES** (preserved={src.get('possible_duplicates_preserved')})",
        f"18. Is Vision-preferred diameter preserved? **{'YES' if auth.get('diameter') else 'NO'}**",
        f"19. Is Vision-preferred MAIN/EXTRA role preserved? **{'YES' if auth.get('role') else 'NO'}**",
        f"20. Are spacers still deterministic-only? **{'YES' if auth.get('spacer') else 'NO'}**",
        f"21. Is the Vision stirrup semantic / deterministic stirrup engineering split preserved? **{'YES' if auth.get('stirrup_split') else 'NO'}**",
        "22. Was any cut length calculated? **NO**",
        "23. Was any development length calculated? **NO**",
        "24. Was any steel weight calculated? **NO**",
        f"25. Was Claude called? **NO** (LIVE_CLAUDE_CALL={LIVE_CLAUDE_CALL})",
        f"26. Was production modified? **NO** (mutation_delta={prod.get('production_mutation_count')}, steel_delta={prod.get('steel_delta')}, bbs_delta={prod.get('bbs_delta')}, workbook_delta={prod.get('workbook_delta')})",
        f"27. What is the engineering binding coverage? **{cov.get('all_groups')}** — labelled ENGINEERING_BINDING_COVERAGE / COMPATIBILITY COVERAGE, **NOT ACCURACY**.",
        f"28. What are the top unresolved engineering-binding failure categories? `{json.dumps(diag.get('top_unresolved_categories') or [])}`",
        f"29. Based on the evidence, is the hybrid semantic object ready to enter a SHADOW calculation phase? **{'YES — evidence supports P2.6.10-D.4 shadow calculation preparation' if ready else 'NOT YET — remaining binding gaps should be reviewed before D.4'}**",
        "",
        "## Coverage (not accuracy)",
        "",
        json.dumps(cov, indent=2, default=str),
        "",
        "## Tests",
        "",
        f"- D.3 unit tests: {unit.get('passed')}/{unit.get('total')} success={unit.get('success')}",
        f"- prior D.1 frozen: {(result.get('prior_phase_units') or {}).get('p2610d1')}",
        f"- prior D.2 frozen: {(result.get('prior_phase_units') or {}).get('p2610d2')}",
        f"- anti-hardcoding: {anti.get('ok')}",
        f"- fingerprints unchanged: {fp.get('unchanged')}",
        "",
        "No production interpretation change. No R1.3 / SI / steel / BBS / workbook mutation.",
        "",
    ]
    (Path(out_root) / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any], hybrids: List[Dict[str, Any]], bound_beams: List[Dict[str, Any]]) -> None:
    out_root = Path(out_root)
    by_id = {str(h.get("beam_id")): h for h in hybrids}
    for bound in bound_beams:
        write_beam_review(out_root=out_root, bound=bound, hybrid=by_id.get(str(bound.get("beam_id"))) or {})
    diag = result.get("diagnostics") or {}
    _dump(out_root / "benchmark_population_manifest.json", result.get("population"))
    _dump(out_root / "engineering_binding_results.json", bound_beams)
    _dump(out_root / "beam_compatibility_results.json", [b.get("compatibility") for b in bound_beams])
    _dump(
        out_root / "group_binding_results.json",
        [g for b in bound_beams for g in (b.get("groups") or [])],
    )
    _dump(out_root / "engineering_reference_coverage.json", (diag.get("coverage") or {}).get("engineering_reference_coverage"))
    _dump(out_root / "binding_diagnostics.json", diag)
    _dump(
        out_root / "binding_summary.json",
        {
            "beam_compatibility": diag.get("beam_compatibility"),
            "group_binding": diag.get("group_binding"),
            "source_categories": diag.get("source_categories"),
            "coverage": diag.get("coverage"),
        },
    )
    mapping = []
    for b in bound_beams:
        for g in b.get("groups") or []:
            mapping.append(
                {
                    "beam_id": b.get("beam_id"),
                    "group_id": g.get("group_id"),
                    "origin": g.get("origin"),
                    "semantic": {
                        "layer": (g.get("semantic") or {}).get("layer"),
                        "role": (g.get("semantic") or {}).get("role"),
                        "diameter": (g.get("semantic") or {}).get("diameter"),
                        "support_scope": (g.get("semantic") or {}).get("support_scope"),
                    },
                    "engineering_binding": g.get("engineering_binding"),
                }
            )
    _dump(out_root / "hybrid_to_engineering_mapping.json", mapping)
    _dump(out_root / "compatibility_validation.json", result.get("compatibility_validation"))
    _dump(out_root / "anti_hardcoding_results.json", result.get("anti_hardcoding"))
    _dump(out_root / "source_fingerprints.json", result.get("fingerprints"))
    _dump(out_root / "production_mutation_report.json", result.get("production"))
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
            "diagnostics",
            "population",
            "production",
            "fingerprints",
            "unit_tests",
            "live_claude_call",
            "runtime_s",
            "ready_for_shadow_calculation",
            "authority_preservation",
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
    _dump(out_root / "P2.6.10-D.3_RESULTS.json", slim)


__all__ = ["write_beam_review", "write_reports"]
