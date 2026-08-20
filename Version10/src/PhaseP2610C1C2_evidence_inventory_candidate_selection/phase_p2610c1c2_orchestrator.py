"""P2.6.10-C.1+C.2 orchestrator. Read-only inventory + selection. No Vision. No DXF."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .anti_hardcoding import run_anti_hardcoding
from .config import (
    CRITICAL_STATUSES,
    ENGINEERING_CHANGES,
    GATE_VERSION,
    LIVE_VISION_CALLS,
    MATERIAL_SCORE_MARGIN,
    MAX_COVERAGE_REGRESSION,
    MIN_FOREGROUND_GAIN,
    MODEL_VERSION,
    MODE_OFFLINE,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    REPORT_ALIAS_DISCOVERED,
    REPORT_BLANK_BEAMS,
    REPORT_CLIP_BEAMS,
    REPORT_QUALITY_BEAMS,
    SHADOW_ONLY,
    SOURCE_B1,
    SOURCE_B2,
    SOURCE_B3,
)
from .inventory import inventory_beam, population_beam_ids, sha256_file
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .report import write_reports
from .selector import select_beam
from .unit_tests import run_unit_tests

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _slim(c: Dict[str, Any]) -> Dict[str, Any]:
    keys = (
        "source_phase",
        "crop_type",
        "artefact_id",
        "path",
        "exists",
        "candidate_status",
        "prior_action",
        "sha256",
        "width_px",
        "height_px",
        "pixel_count",
        "file_size_bytes",
        "quality_flags",
        "usable_status",
        "primary_status",
        "critical_failure",
        "score",
        "foreground_ratio",
        "coverage_x",
        "coverage_y",
        "empty_sides",
    )
    return {k: c.get(k) for k in keys}


def _side_manifest(sel: Dict[str, Any], cands: List[Dict[str, Any]]) -> Dict[str, Any]:
    chosen = sel.get("selected") or {}
    return {
        "selected_source_phase": chosen.get("source_phase"),
        "selected_path": chosen.get("path"),
        "selected_sha256": chosen.get("sha256"),
        "selected_primary_status": chosen.get("primary_status"),
        "selected_critical_failure": chosen.get("critical_failure"),
        "selection_status": sel.get("selection_status"),
        "selection_reason_codes": list(sel.get("selection_reason_codes") or []),
        "decision": sel.get("decision"),
        "candidates": [_slim(c) for c in cands],
    }


def _cand_status(cands: List[Dict[str, Any]], phase: str) -> str:
    rows = [c for c in cands if c.get("source_phase") == phase]
    if not rows:
        return "MISSING"
    if any(c.get("candidate_status") == "AVAILABLE" for c in rows):
        best = next((c for c in rows if c.get("candidate_status") == "AVAILABLE"), rows[0])
        return str(best.get("primary_status") or "AVAILABLE")
    if any(c.get("candidate_status") == "DUPLICATE_OF_PREFERRED" for c in rows):
        return "DUPLICATE_OF_PREFERRED"
    return str(rows[0].get("candidate_status") or "MISSING")


def _reporting_ids(discovered: List[str]) -> Dict[str, List[str]]:
    have = set(discovered)

    def _resolve(ids: tuple) -> List[str]:
        out: List[str] = []
        for x in ids:
            if x in have and x not in out:
                out.append(x)
                continue
            for alias, real in REPORT_ALIAS_DISCOVERED:
                if x == alias and real in have and real not in out:
                    out.append(real)
        return out

    return {
        "blank_crushed": _resolve(REPORT_BLANK_BEAMS),
        "long_horizontal": _resolve(REPORT_CLIP_BEAMS),
        "less_accurate": _resolve(REPORT_QUALITY_BEAMS),
    }


def _copy_if_present(src: Optional[str], dest: Path) -> Optional[Dict[str, Any]]:
    if not src:
        return {"copied": False, "reason": "missing_source"}
    p = Path(src)
    if not p.exists():
        return {"copied": False, "reason": "source_not_found", "source": src}
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
    src_sha = sha256_file(p)
    dst_sha = sha256_file(dest)
    return {
        "copied": True,
        "source": str(p),
        "dest": str(dest),
        "source_sha256": src_sha,
        "copy_sha256": dst_sha,
        "sha_equal": src_sha == dst_sha,
    }


def _path_for_phase(cands: List[Dict[str, Any]], phase: str) -> Optional[str]:
    for c in cands:
        if c.get("source_phase") == phase and c.get("exists") and c.get("candidate_status") == "AVAILABLE":
            return c.get("path")
    for c in cands:
        if c.get("source_phase") == phase and c.get("exists"):
            return c.get("path")
    return None


def _classify_decision(
    *,
    tests_ok: bool,
    fingerprints_ok: bool,
    anti_ok: bool,
    processed: int,
    discovered: int,
    hardcoding: bool,
    newest_wins: bool,
    production_mutations: int,
    unresolved_limitations: bool,
) -> str:
    if hardcoding or not tests_ok or not fingerprints_ok or not anti_ok or newest_wins:
        return "FAIL"
    if production_mutations or processed != discovered or discovered <= 0:
        return "FAIL"
    if unresolved_limitations:
        return "PASS_WITH_LIMITATIONS"
    return "PASS"


def _newest_wins_violation(decisions: List[Dict[str, Any]]) -> bool:
    allowed = {
        "CLEARS_BASELINE_CRITICAL_FAILURE",
        "MATERIAL_SCORE_AND_FOREGROUND_GAIN",
        "PREFERRED_MISSING",
        "SELECTED_BEST_AVAILABLE",
    }
    for rec in decisions:
        for kind in ("context", "detail"):
            side = rec.get(kind) or {}
            if side.get("decision") != "REPLACE":
                continue
            codes = set(side.get("selection_reason_codes") or [])
            if not (codes & allowed):
                return True
    return False


def run_phase_p2610c1c2(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_OFFLINE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    pkg = Path(__file__).resolve().parent
    out_root.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode != MODE_OFFLINE:
        raise RuntimeError(f"unsupported P2.6.10-C.1+C.2 mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log("  READ-ONLY: no DXF, no rerender, no Vision")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.10-C.1+C.2 unit tests failed: {failed}")
    else:
        existing = out_root / "unit_tests.json"
        if existing.exists():
            unit = json.loads(existing.read_text(encoding="utf-8"))
            unit["loaded_from_previous_run"] = True

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(pkg)
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.10-C.1+C.2 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.10-C.1+C.2 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    intact = prior_artefacts_intact(v10)
    if not intact.get("ok"):
        raise RuntimeError(f"Prior artefacts missing: {intact.get('missing')}")

    anti = run_anti_hardcoding(package_dir=pkg)
    if not anti.get("ok"):
        raise RuntimeError(f"P2.6.10-C.1+C.2 anti-hardcoding failed: {anti}")

    t_all = time.perf_counter()
    t0 = time.perf_counter()
    beam_ids = population_beam_ids(v10)
    inventory_discovery_s = time.perf_counter() - t0
    _log(f"  unique beams from B.1 validation: {len(beam_ids)}")

    inventories: List[Dict[str, Any]] = []
    hash_s = 0.0
    evidence_s = 0.0
    t_inv = time.perf_counter()
    for i, beam_id in enumerate(beam_ids, start=1):
        t_e = time.perf_counter()
        inv = inventory_beam(v10, beam_id)
        evidence_s += time.perf_counter() - t_e
        inventories.append(inv)
        if i % 25 == 0 or i == len(beam_ids):
            _log(f"  inventory {i}/{len(beam_ids)}")
    file_inspection_hashing_s = time.perf_counter() - t_inv - evidence_s
    hash_s = file_inspection_hashing_s

    t_sel = time.perf_counter()
    selection_manifest: List[Dict[str, Any]] = []
    candidate_decisions: List[Dict[str, Any]] = []
    rejection_report: List[Dict[str, Any]] = []
    b1_replacements: List[Dict[str, Any]] = []
    unresolved_beams: List[Dict[str, Any]] = []
    ctx_src = {SOURCE_B1: 0, SOURCE_B2: 0, SOURCE_B3: 0, None: 0}
    det_src = {SOURCE_B1: 0, SOURCE_B2: 0, SOURCE_B3: 0, None: 0}
    mixed = 0
    retain_pref = 0
    replace_crit = 0
    replace_mat = 0
    ambiguous = 0
    b1_ctx_n = 0
    b1_det_n = 0
    b2_n = 0
    b3_n = 0
    status_counts: Dict[str, int] = {}

    for inv in inventories:
        beam_id = inv["beam_id"]
        sel = select_beam(inv)
        ctx_m = _side_manifest(sel["context"], inv["context_candidates"])
        det_m = _side_manifest(sel["detail"], inv["detail_candidates"])
        selection_manifest.append({"beam_id": beam_id, "context": ctx_m, "detail": det_m})

        ctx_phase = ctx_m.get("selected_source_phase")
        det_phase = det_m.get("selected_source_phase")
        ctx_src[ctx_phase] = ctx_src.get(ctx_phase, 0) + 1
        det_src[det_phase] = det_src.get(det_phase, 0) + 1
        if ctx_phase and det_phase and ctx_phase != det_phase:
            mixed += 1

        if any(c.get("exists") and c.get("source_phase") == SOURCE_B1 for c in inv["context_candidates"]):
            b1_ctx_n += 1
        if any(c.get("exists") and c.get("source_phase") == SOURCE_B1 for c in inv["detail_candidates"]):
            b1_det_n += 1
        if any(c.get("exists") and c.get("source_phase") == SOURCE_B2 for c in inv["context_candidates"] + inv["detail_candidates"]):
            b2_n += 1
        if any(
            c.get("exists")
            and c.get("source_phase") == SOURCE_B3
            and c.get("candidate_status") == "AVAILABLE"
            for c in inv["context_candidates"] + inv["detail_candidates"]
        ):
            b3_n += 1

        for kind in ("context", "detail"):
            side = sel[kind]
            st = str(side.get("selection_status") or "UNKNOWN")
            status_counts[st] = status_counts.get(st, 0) + 1
            codes = list(side.get("selection_reason_codes") or [])
            if side.get("decision") == "RETAIN":
                retain_pref += 1
                if "CHALLENGERS_REJECTED" in codes:
                    ambiguous += 1
            elif side.get("decision") == "REPLACE":
                if "CLEARS_BASELINE_CRITICAL_FAILURE" in codes:
                    replace_crit += 1
                if "MATERIAL_SCORE_AND_FOREGROUND_GAIN" in codes:
                    replace_mat += 1
                if side.get("baseline") == SOURCE_B1 or "PREFERRED_MISSING" in codes:
                    b1_replacements.append(
                        {
                            "beam_id": beam_id,
                            "render_type": kind,
                            "baseline": side.get("baseline") or SOURCE_B1,
                            "challenger": side.get("challenger") or (side.get("selected") or {}).get("source_phase"),
                            "decision": "REPLACE",
                            "reason_codes": codes,
                            "selection_status": st,
                            "baseline_evidence": side.get("baseline_evidence"),
                            "challenger_evidence": side.get("challenger_evidence"),
                            "material_improvement": side.get("material_improvement"),
                        }
                    )
            if st in ("UNRESOLVED_MISSING", "RETAIN_PREFERRED_STILL_CRITICAL", "FALLBACK_STILL_CRITICAL") or (
                (side.get("selected") or {}).get("critical_failure")
            ):
                unresolved_beams.append(
                    {
                        "beam_id": beam_id,
                        "render_type": kind,
                        "selection_status": st,
                        "reason_codes": codes,
                        "selected_source": (side.get("selected") or {}).get("source_phase"),
                    }
                )
            distinct = [
                c
                for c in inv[f"{kind}_candidates"]
                if c.get("exists") and c.get("candidate_status") not in ("MISSING",)
            ]
            if len({c.get("sha256") or c.get("path") for c in distinct}) > 1:
                candidate_decisions.append(
                    {
                        "beam_id": beam_id,
                        "render_type": kind,
                        "baseline": SOURCE_B1,
                        "challenger": side.get("challenger"),
                        "decision": side.get("decision"),
                        "reason_codes": codes,
                        "baseline_evidence": side.get("baseline_evidence"),
                        "challenger_evidence": side.get("challenger_evidence"),
                        "material_improvement": side.get("material_improvement"),
                        "rejections": side.get("rejections") or [],
                    }
                )
            selected_path = (side.get("selected") or {}).get("path")
            for c in inv[f"{kind}_candidates"]:
                if not c.get("exists"):
                    rejection_report.append(
                        {
                            "beam_id": beam_id,
                            "render_type": kind,
                            "candidate": c.get("source_phase"),
                            "path": c.get("path"),
                            "rejection_reason": ["MISSING_CANDIDATE"],
                            "baseline": SOURCE_B1,
                            "critical_failure": True,
                            "material_improvement": False,
                        }
                    )
                    continue
                if c.get("path") == selected_path and c.get("sha256") == (side.get("selected") or {}).get("sha256"):
                    continue
                reasons = ["NOT_SELECTED"]
                for rej in side.get("rejections") or []:
                    if rej.get("path") == c.get("path") or rej.get("candidate") == c.get("source_phase"):
                        reasons = list(rej.get("rejection_reason") or reasons)
                        rejection_report.append(
                            {
                                "beam_id": beam_id,
                                "render_type": kind,
                                "candidate": c.get("source_phase"),
                                "path": c.get("path"),
                                "rejection_reason": reasons,
                                "baseline": SOURCE_B1,
                                "critical_failure": c.get("critical_failure"),
                                "material_improvement": False,
                                "comparison_target": SOURCE_B1,
                            }
                        )
                        break
                else:
                    if c.get("candidate_status") == "DUPLICATE_OF_PREFERRED":
                        reasons = ["DUPLICATE_OF_PREFERRED"]
                    rejection_report.append(
                        {
                            "beam_id": beam_id,
                            "render_type": kind,
                            "candidate": c.get("source_phase"),
                            "path": c.get("path"),
                            "rejection_reason": reasons,
                            "baseline": SOURCE_B1,
                            "critical_failure": c.get("critical_failure"),
                            "material_improvement": False,
                            "comparison_target": SOURCE_B1,
                        }
                    )

    selection_s = time.perf_counter() - t_sel

    t_rep = time.perf_counter()
    cohort_map = _reporting_ids(beam_ids)
    known_cohorts: Dict[str, List[Dict[str, Any]]] = {}
    inv_by_id = {r["beam_id"]: r for r in inventories}
    man_by_id = {r["beam_id"]: r for r in selection_manifest}
    for group, ids in cohort_map.items():
        rows = []
        for beam_id in ids:
            inv = inv_by_id[beam_id]
            man = man_by_id[beam_id]
            ctx_unres = man["context"]["selection_status"] in (
                "UNRESOLVED_MISSING",
                "RETAIN_PREFERRED_STILL_CRITICAL",
                "FALLBACK_STILL_CRITICAL",
            ) or man["context"].get("selected_critical_failure")
            det_unres = man["detail"]["selection_status"] in (
                "UNRESOLVED_MISSING",
                "RETAIN_PREFERRED_STILL_CRITICAL",
                "FALLBACK_STILL_CRITICAL",
            ) or man["detail"].get("selected_critical_failure")
            rows.append(
                {
                    "beam_id": beam_id,
                    "b1_context_status": _cand_status(inv["context_candidates"], SOURCE_B1),
                    "b2_context_status": _cand_status(inv["context_candidates"], SOURCE_B2),
                    "b3_context_status": _cand_status(inv["context_candidates"], SOURCE_B3),
                    "b1_detail_status": _cand_status(inv["detail_candidates"], SOURCE_B1),
                    "b2_detail_status": _cand_status(inv["detail_candidates"], SOURCE_B2),
                    "b3_detail_status": _cand_status(inv["detail_candidates"], SOURCE_B3),
                    "selected_context_source": man["context"].get("selected_source_phase"),
                    "selected_detail_source": man["detail"].get("selected_source_phase"),
                    "context_decision": man["context"].get("decision"),
                    "detail_decision": man["detail"].get("decision"),
                    "context_reasons": man["context"].get("selection_reason_codes"),
                    "detail_reasons": man["detail"].get("selection_reason_codes"),
                    "unresolved": bool(ctx_unres or det_unres),
                }
            )
            review = out_root / "review" / beam_id
            ctx_copies = {
                "b1": _copy_if_present(_path_for_phase(inv["context_candidates"], SOURCE_B1), review / "context" / "b1.png"),
                "b2": _copy_if_present(_path_for_phase(inv["context_candidates"], SOURCE_B2), review / "context" / "b2.png"),
                "b3": _copy_if_present(_path_for_phase(inv["context_candidates"], SOURCE_B3), review / "context" / "b3.png"),
                "selected": _copy_if_present(man["context"].get("selected_path"), review / "context" / "selected.png"),
            }
            det_copies = {
                "b1": _copy_if_present(_path_for_phase(inv["detail_candidates"], SOURCE_B1), review / "detail" / "b1.png"),
                "b2": _copy_if_present(_path_for_phase(inv["detail_candidates"], SOURCE_B2), review / "detail" / "b2.png"),
                "b3": _copy_if_present(_path_for_phase(inv["detail_candidates"], SOURCE_B3), review / "detail" / "b3.png"),
                "selected": _copy_if_present(man["detail"].get("selected_path"), review / "detail" / "selected.png"),
            }
            _dump(
                review / "decision.json",
                {
                    "beam_id": beam_id,
                    "cohort_group": group,
                    "context": man["context"],
                    "detail": man["detail"],
                    "copies": {"context": ctx_copies, "detail": det_copies},
                    "note": "Copies for review only. Source artefacts are immutable. Manifest paths are source of truth.",
                },
            )
        known_cohorts[group] = rows

    selection_summary = {
        "total_unique_beams": len(beam_ids),
        "beams_with_b1_context": b1_ctx_n,
        "beams_with_b1_detail": b1_det_n,
        "beams_with_b2_candidates": b2_n,
        "beams_with_b3_candidates": b3_n,
        "context_selected_b1": ctx_src.get(SOURCE_B1, 0),
        "context_selected_b2": ctx_src.get(SOURCE_B2, 0),
        "context_selected_b3": ctx_src.get(SOURCE_B3, 0),
        "context_unresolved_missing": ctx_src.get(None, 0),
        "detail_selected_b1": det_src.get(SOURCE_B1, 0),
        "detail_selected_b2": det_src.get(SOURCE_B2, 0),
        "detail_selected_b3": det_src.get(SOURCE_B3, 0),
        "detail_unresolved_missing": det_src.get(None, 0),
        "mixed_source_selections": mixed,
        "b1_retained_by_preference": retain_pref,
        "b1_replaced_critical_failure": replace_crit,
        "b1_replaced_material_improvement": replace_mat,
        "ambiguous_no_replacement": ambiguous,
        "missing_selections": ctx_src.get(None, 0) + det_src.get(None, 0),
        "per_status_counts": status_counts,
        "unresolved_render_count": len(unresolved_beams),
    }

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    prior_ok = {
        "p266": prior_phase_unit_ok(v10, "PhaseP266_semantic_longitudinal_resolver", 36),
        "p2610a": prior_phase_unit_ok(v10, "PhaseP2610A_beam_region_crop_audit", 14),
        "p2610b": prior_phase_unit_ok(v10, "PhaseP2610B_adaptive_beam_detail_crop", 18),
        "p2610b1": prior_phase_unit_ok(v10, "PhaseP2610B1_population_generalization", 16),
        "p2610b2": prior_phase_unit_ok(v10, "PhaseP2610B2_render_quality_directional_recovery", 29),
        "p2610b3": prior_phase_unit_ok(v10, "PhaseP2610B3_target_anchor_geometry_context_recovery", 18),
    }

    unresolved_limitations = bool(unresolved_beams) or replace_crit > 0
    newest_wins = _newest_wins_violation(candidate_decisions)
    decision = _classify_decision(
        tests_ok=bool(unit.get("success")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        anti_ok=bool(anti.get("ok")),
        processed=len(selection_manifest),
        discovered=len(beam_ids),
        hardcoding=bool(anti.get("beam_id_special_cases")),
        newest_wins=newest_wins,
        production_mutations=0,
        unresolved_limitations=unresolved_limitations,
    )
    total_s = time.perf_counter() - t_all
    performance = {
        "total_runtime_s": round(total_s, 3),
        "inventory_discovery_s": round(inventory_discovery_s, 3),
        "file_inspection_hashing_s": round(hash_s, 3),
        "evidence_loading_s": round(evidence_s, 3),
        "selection_s": round(selection_s, 3),
        "report_generation_s": round(time.perf_counter() - t_rep, 3),
        "note": "No DXF load. No rerender. SHA cache keyed by resolved path.",
    }
    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "pass_fail": "PASS" if decision.startswith("PASS") else "FAIL",
        "decision": decision,
        "recommendation": (
            "Evidence inventory and preference-preserving selection complete. "
            "B.1 is retained by default. Consume selection_manifest.json in P2.6.10-C.3. "
            "Do not treat this as production-ready."
        ),
        "thresholds": {
            "MATERIAL_SCORE_MARGIN": MATERIAL_SCORE_MARGIN,
            "MIN_FOREGROUND_GAIN": MIN_FOREGROUND_GAIN,
            "MAX_COVERAGE_REGRESSION": MAX_COVERAGE_REGRESSION,
            "CRITICAL_STATUSES": list(CRITICAL_STATUSES),
        },
        "evidence_inventory": inventories,
        "selection_manifest": selection_manifest,
        "selection_summary": selection_summary,
        "candidate_decisions": candidate_decisions,
        "rejection_report": rejection_report,
        "b1_replacements": b1_replacements,
        "unresolved_beams": unresolved_beams,
        "known_reporting_cohorts": known_cohorts,
        "validation_summary": {
            **selection_summary,
            "shadow_only": SHADOW_ONLY,
            "production_write": PRODUCTION_WRITE,
            "engineering_changes": ENGINEERING_CHANGES,
            "live_vision_calls": LIVE_VISION_CALLS,
            "prior_phase_units": {k: bool(v.get("ok")) for k, v in prior_ok.items()},
        },
        "performance": performance,
        "anti_hardcoding": anti,
        "unit_tests": unit,
        "fingerprints": fp_cmp,
        "production": {
            "production_mutation_count": 0,
            "production_write": PRODUCTION_WRITE,
            "production_action": PRODUCTION_ACTION,
            "engineering_changes": ENGINEERING_CHANGES,
            "live_vision_invoked": False,
            "shadow_only": SHADOW_ONLY,
        },
        "live_claude_vision": "NOT_CALLED",
        "handoff": {
            "ready_for": "P2.6.10-C.3",
            "name": "Visual Completeness Gate + Claude Vision Shadow Benchmark",
            "manifest": "selection_manifest.json",
        },
        "output_root": str(out_root),
    }
    write_reports(out_root=out_root, result=result)
    _dump(out_root / "performance_profile.json", performance)
    _log(f"  decision={decision} unique={len(beam_ids)} runtime_s={performance['total_runtime_s']}")
    return result


__all__ = ["run_phase_p2610c1c2"]
