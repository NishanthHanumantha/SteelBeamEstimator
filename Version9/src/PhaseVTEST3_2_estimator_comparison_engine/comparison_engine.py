"""
comparison_engine.py — Core engineering comparison logic.
MODEL_VERSION: 8.1.3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from comparison_models import (
    DIAMETER_MM,
    ROLE_PATTERNS,
    ROOT_CAUSE_CATEGORIES,
    BeamBlock,
    ComparisonResult,
    ModelBeam,
    ProjectSummary,
    RoleLine,
)


def _accuracy(est: float, mod: float) -> float:
    if est <= 0 and mod <= 0:
        return 100.0
    if est <= 0:
        return 0.0
    diff_pct = abs(est - mod) / est * 100.0
    return round(max(0.0, 100.0 - diff_pct), 4)


def _diff_row(label: str, est: float, mod: float, unit: str = "kg") -> Dict[str, Any]:
    diff = round(mod - est, 4)
    pct = round((diff / est * 100.0) if est else (100.0 if mod else 0.0), 4)
    return {
        "metric": label,
        "unit": unit,
        "estimator": round(est, 4),
        "model": round(mod, 4),
        "absolute_difference": diff,
        "percentage_difference": pct,
        "accuracy_pct": _accuracy(est, mod),
    }


def _info_row(label: str, est: float, mod: float, unit: str) -> Dict[str, Any]:
    """Informational quantity — excluded from all accuracy calculations."""
    return {
        "metric": label,
        "unit": unit,
        "estimator": round(est, 4),
        "model": round(mod, 4),
        "included_in_accuracy": False,
        "note": "Outside current Beam Steel Estimation model scope — informational only.",
    }


def compare_project_summaries(
    est: ProjectSummary, mod: ProjectSummary
) -> Dict[str, Any]:
    informational = [
        _info_row("Concrete", est.concrete_m3, mod.concrete_m3, "m3"),
        _info_row("Shuttering", est.shuttering_m2, mod.shuttering_m2, "m2"),
    ]
    reinforcement_rows = []
    for dia in DIAMETER_MM:
        reinforcement_rows.append(
            _diff_row(
                f"{dia}mm",
                est.diameter_kg.get(dia, 0.0),
                mod.diameter_kg.get(dia, 0.0),
            )
        )
    reinforcement_rows.append(_diff_row("TOTAL Steel", est.total_steel_kg, mod.total_steel_kg))
    for row in reinforcement_rows:
        row["included_in_accuracy"] = True
    return {
        "estimator_label": est.label,
        "estimator_source_row": est.source_row,
        "estimator_total_steel_source": est.total_steel_source,
        "estimator_total_steel_mt": est.total_steel_mt,
        "estimator_parser_warnings": est.parser_warnings,
        "model_label": mod.label,
        "informational_only": informational,
        "reinforcement_metrics": reinforcement_rows,
        "rows": reinforcement_rows,
        "total_steel": reinforcement_rows[-1],
    }


def compare_diameters(est: ProjectSummary, mod: ProjectSummary) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for dia in DIAMETER_MM:
        e = est.diameter_kg.get(dia, 0.0)
        m = mod.diameter_kg.get(dia, 0.0)
        out.append(
            {
                "diameter_mm": dia,
                "estimator_kg": round(e, 4),
                "model_kg": round(m, 4),
                "absolute_difference_kg": round(m - e, 4),
                "percentage_difference": round(((m - e) / e * 100.0) if e else (100.0 if m else 0.0), 4),
                "accuracy_pct": _accuracy(e, m),
            }
        )
    out.sort(key=lambda x: x["accuracy_pct"], reverse=True)
    for i, row in enumerate(out, 1):
        row["rank"] = i
    return out


def _role_totals_est(blocks: List[BeamBlock]) -> Dict[str, float]:
    totals: Dict[str, float] = {r: 0.0 for r in list(ROLE_PATTERNS.keys()) + ["Unknown"]}
    for b in blocks:
        for line in b.lines:
            totals[line.role] = totals.get(line.role, 0.0) + line.steel_kg
    return totals


def _role_totals_mod(beams: List[ModelBeam]) -> Dict[str, float]:
    totals: Dict[str, float] = {r: 0.0 for r in list(ROLE_PATTERNS.keys()) + ["Unknown"]}
    for b in beams:
        for line in b.roles:
            totals[line.role] = totals.get(line.role, 0.0) + line.steel_kg
        if not b.roles and b.steel_kg > 0:
            totals["Unknown"] = totals.get("Unknown", 0.0) + b.steel_kg
    return totals


def compare_roles(
    est_blocks: List[BeamBlock], mod_beams: List[ModelBeam]
) -> List[Dict[str, Any]]:
    est_t = _role_totals_est(est_blocks)
    mod_t = _role_totals_mod(mod_beams)
    roles = list(ROLE_PATTERNS.keys()) + ["Unknown"]
    out: List[Dict[str, Any]] = []
    for role in roles:
        e = est_t.get(role, 0.0)
        m = mod_t.get(role, 0.0)
        diff = round(m - e, 4)
        out.append(
            {
                "role": role,
                "estimator_kg": round(e, 4),
                "model_kg": round(m, 4),
                "absolute_difference_kg": diff,
                "percentage_difference": round(((diff / e * 100.0) if e else (100.0 if m else 0.0)), 4),
                "accuracy_pct": _accuracy(e, m),
                "likely_engineering_reason": _role_reason(role, e, m),
            }
        )
    return out


def _role_reason(role: str, est: float, mod: float) -> str:
    if est <= 0 and mod <= 0:
        return "No steel in either workbook for this role."
    if est > 0 and mod <= 0:
        return f"Model workbook shows zero {role} steel; estimator has {est:.1f} kg — reinforcement discovery or bar propagation gap."
    if est <= 0 and mod > 0:
        return f"Model reports {mod:.1f} kg {role} not present in estimator totals."
    pct = abs(mod - est) / est * 100
    if pct < 5:
        return "Minor quantity variance within engineering tolerance."
    if role in ("Stirrups", "Hooks", "Spacer Bars"):
        return "Difference likely in stirrup/hook/spacer discovery, spacing, or cutting length."
    if role in ("Top Bars Extra", "Bottom Bars Extra"):
        return "Difference likely in extra bar annotation interpretation or lap/extension rules."
    return "Difference in bar count, diameter assignment, or cutting/total length calculation."


def beam_coverage(
    est_blocks: List[BeamBlock], mod_beams: List[ModelBeam]
) -> Dict[str, Any]:
    est_ids = {b.beam_id.upper() for b in est_blocks}
    mod_ids = {b.beam_id.upper() for b in mod_beams}
    matched = sorted(est_ids & mod_ids)
    missing = sorted(est_ids - mod_ids)
    extra = sorted(mod_ids - est_ids)

    est_map = {b.beam_id.upper(): b for b in est_blocks}
    mod_map = {b.beam_id.upper(): b for b in mod_beams}

    zero_steel_est = [bid for bid in est_ids if est_map[bid].total_steel_kg <= 0]
    zero_steel_mod = [bid for bid in mod_ids if mod_map[bid].steel_kg <= 0]
    zero_reinf_mod = [
        bid for bid in mod_ids
        if mod_map[bid].steel_kg <= 0 and len(mod_map[bid].roles) == 0
    ]
    incomplete_mod = [
        bid for bid in matched
        if mod_map[bid].steel_kg <= 0 and est_map[bid].total_steel_kg > 0
    ]

    return {
        "estimator_beam_count": len(est_ids),
        "model_beam_count": len(mod_ids),
        "matched_beams": len(matched),
        "missing_in_model": missing,
        "extra_in_model": extra,
        "matched_beam_ids": matched,
        "estimator_zero_steel_beams": zero_steel_est,
        "model_zero_steel_beams": zero_steel_mod,
        "model_zero_reinforcement_beams": zero_reinf_mod,
        "model_incomplete_reinforcement_beams": incomplete_mod,
        "beam_coverage_pct": round(len(matched) / len(est_ids) * 100.0, 2) if est_ids else 0.0,
    }


def _role_steel_by_name(lines: List[RoleLine]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for ln in lines:
        out[ln.role] = out.get(ln.role, 0.0) + ln.steel_kg
    return out


def compare_beams(
    est_blocks: List[BeamBlock], mod_beams: List[ModelBeam]
) -> List[Dict[str, Any]]:
    est_map = {b.beam_id.upper(): b for b in est_blocks}
    mod_map = {b.beam_id.upper(): b for b in mod_beams}
    all_ids = sorted(set(est_map) | set(mod_map))
    results: List[Dict[str, Any]] = []

    for bid in all_ids:
        eb = est_map.get(bid)
        mb = mod_map.get(bid)
        status = "matched"
        if eb and not mb:
            status = "missing_in_model"
        elif mb and not eb:
            status = "extra_in_model"

        est_steel = eb.total_steel_kg if eb else 0.0
        mod_steel = mb.steel_kg if mb else 0.0
        steel_diff = round(mod_steel - est_steel, 4)

        est_roles = _role_steel_by_name(eb.lines) if eb else {}
        mod_roles = _role_steel_by_name(mb.roles) if mb else {}

        role_rows = {}
        for role in list(ROLE_PATTERNS.keys()) + ["Unknown"]:
            e = est_roles.get(role, 0.0)
            m = mod_roles.get(role, 0.0)
            role_rows[role] = {
                "estimator_kg": round(e, 4),
                "model_kg": round(m, 4),
                "difference_kg": round(m - e, 4),
            }

        dia_rows = {}
        for dia in DIAMETER_MM:
            e = (eb.diameter_kg.get(dia, 0.0) if eb else 0.0)
            m = (mb.diameter_kg.get(dia, 0.0) if mb else 0.0)
            dia_rows[str(dia)] = {
                "estimator_kg": round(e, 4),
                "model_kg": round(m, 4),
                "difference_kg": round(m - e, 4),
            }

        severity = "perfect_match"
        if status != "matched":
            severity = "missing_beam" if status == "missing_in_model" else "extra_beam"
        elif abs(steel_diff) < 0.5:
            severity = "perfect_match"
        elif abs(steel_diff) / max(est_steel, 1) < 0.05:
            severity = "minor_difference"
        else:
            severity = "major_difference"

        first_diff = _first_beam_difference(bid, eb, mb, est_roles, mod_roles)

        results.append(
            {
                "beam_id": bid,
                "status": status,
                "severity": severity,
                "concrete_m3": {
                    "estimator": eb.concrete_m3 if eb else None,
                    "model": None,
                },
                "shuttering_m2": {
                    "estimator": eb.shuttering_m2 if eb else None,
                    "model": None,
                },
                "steel_kg": {
                    "estimator": round(est_steel, 4),
                    "model": round(mod_steel, 4),
                    "difference_kg": steel_diff,
                    "accuracy_pct": _accuracy(est_steel, mod_steel),
                },
                "roles": role_rows,
                "diameters": dia_rows,
                "first_observable_difference": first_diff,
            }
        )

    results.sort(key=lambda x: abs(x["steel_kg"]["difference_kg"]), reverse=True)
    return results


def _first_beam_difference(
    bid: str,
    eb: Optional[BeamBlock],
    mb: Optional[ModelBeam],
    est_roles: Dict[str, float],
    mod_roles: Dict[str, float],
) -> str:
    if eb and not mb:
        return f"Beam {bid} present in estimator workbook but absent from model beam list."
    if mb and not eb:
        return f"Beam {bid} present in model workbook but absent from estimator beam blocks."
    if not eb or not mb:
        return "Beam not present in both workbooks."

    if mb.steel_kg <= 0 and eb.total_steel_kg > 0:
        return f"Model reports zero steel ({mb.steel_kg:.2f} kg) vs estimator {eb.total_steel_kg:.2f} kg."

    for role in ROLE_PATTERNS:
        e = est_roles.get(role, 0.0)
        m = mod_roles.get(role, 0.0)
        if e > 0 and m <= 0:
            return f"{role} missing in model (estimator {e:.2f} kg)."
        if e > 0 and abs(m - e) / e > 0.05:
            return f"{role} quantity mismatch: estimator {e:.2f} kg, model {m:.2f} kg."

    if abs(mb.steel_kg - eb.total_steel_kg) > 0.5:
        return (
            f"Total steel mismatch: estimator {eb.total_steel_kg:.2f} kg, "
            f"model {mb.steel_kg:.2f} kg."
        )
    return "Perfect match within tolerance."


def engineering_differences(
    beam_comparisons: List[Dict[str, Any]],
    coverage: Dict[str, Any],
    est_summary: ProjectSummary,
    mod_summary: ProjectSummary,
) -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []

    ts = _diff_row("Project Total Steel", est_summary.total_steel_kg, mod_summary.total_steel_kg)
    if abs(ts["absolute_difference"]) > 0.5:
        diffs.append(
            {
                "scope": "project",
                "beam_id": None,
                "metric": "Total Steel",
                "estimator": ts["estimator"],
                "model": ts["model"],
                "absolute_difference": ts["absolute_difference"],
                "first_observable_difference": (
                    f"Project total steel: estimator {ts['estimator']:.2f} kg vs "
                    f"model {ts['model']:.2f} kg (Δ {ts['absolute_difference']:.2f} kg)."
                ),
            }
        )

    for bid in coverage.get("missing_in_model", []):
        diffs.append(
            {
                "scope": "beam",
                "beam_id": bid,
                "metric": "Beam Coverage",
                "estimator": "present",
                "model": "absent",
                "absolute_difference": None,
                "first_observable_difference": f"Beam {bid} missing from model workbook.",
            }
        )

    for bc in beam_comparisons:
        if bc["severity"] in ("perfect_match",):
            continue
        if bc["status"] == "extra_in_model":
            continue
        fd = bc.get("first_observable_difference", "")
        if fd and "Perfect match" not in fd:
            diffs.append(
                {
                    "scope": "beam",
                    "beam_id": bc["beam_id"],
                    "metric": "Beam Steel / Roles",
                    "estimator": bc["steel_kg"]["estimator"],
                    "model": bc["steel_kg"]["model"],
                    "absolute_difference": bc["steel_kg"]["difference_kg"],
                    "first_observable_difference": fd,
                }
            )

    return diffs


def categorize_root_causes(
    engineering_diffs: List[Dict[str, Any]],
    coverage: Dict[str, Any],
    mod_summary: ProjectSummary,
) -> List[Dict[str, Any]]:
    causes: List[Dict[str, Any]] = []

    if mod_summary.total_steel_kg < 1000:
        causes.append(
            {
                "category": ROOT_CAUSE_CATEGORIES[1],  # B
                "evidence": (
                    f"Model total steel {mod_summary.total_steel_kg:.2f} kg vs "
                    f"estimator scale — majority of beams show zero steel in model Steel Summary."
                ),
                "beam_count_affected": len(coverage.get("model_incomplete_reinforcement_beams", [])),
            }
        )

    for bid in coverage.get("model_incomplete_reinforcement_beams", [])[:20]:
        causes.append(
            {
                "category": ROOT_CAUSE_CATEGORIES[1],
                "evidence": f"Beam {bid} has estimator reinforcement but model steel_kg = 0.",
                "beam_id": bid,
            }
        )

    for d in engineering_diffs:
        fd = d.get("first_observable_difference", "")
        cat = ROOT_CAUSE_CATEGORIES[7]  # H
        if "missing" in fd.lower() and "role" in fd.lower() or any(
            r in fd for r in ("Top Bars", "Bottom Bars", "Stirrups", "Hooks", "SFR", "Spacer")
        ):
            if "missing in model" in fd.lower():
                cat = ROOT_CAUSE_CATEGORIES[1]  # B discovery
            else:
                cat = ROOT_CAUSE_CATEGORIES[2]  # C semantics
        elif "zero steel" in fd.lower():
            cat = ROOT_CAUSE_CATEGORIES[1]
        elif "Project total steel" in fd:
            cat = ROOT_CAUSE_CATEGORIES[1]
        elif "quantity mismatch" in fd.lower():
            cat = ROOT_CAUSE_CATEGORIES[4]  # D geometry or F steel calc
        causes.append(
            {
                "category": cat,
                "beam_id": d.get("beam_id"),
                "evidence": fd,
                "metric": d.get("metric"),
            }
        )

    # Aggregate counts
    agg: Dict[str, int] = {}
    for c in causes:
        agg[c["category"]] = agg.get(c["category"], 0) + 1
    summary = [{"category": k, "count": v} for k, v in sorted(agg.items(), key=lambda x: -x[1])]

    return {"items": causes, "summary_by_category": summary}


def accuracy_metrics(
    est_summary: ProjectSummary,
    mod_summary: ProjectSummary,
    diameter_comp: List[Dict[str, Any]],
    role_comp: List[Dict[str, Any]],
    coverage: Dict[str, Any],
    beam_comparisons: List[Dict[str, Any]],
) -> Dict[str, Any]:
    matched = [bc for bc in beam_comparisons if bc["status"] == "matched"]
    beam_qty_acc = (
        sum(bc["steel_kg"]["accuracy_pct"] for bc in matched) / len(matched)
        if matched else 0.0
    )
    dia_acc = sum(d["accuracy_pct"] for d in diameter_comp) / len(diameter_comp) if diameter_comp else 0.0
    role_acc = sum(r["accuracy_pct"] for r in role_comp if r["estimator_kg"] > 0) / max(
        1, sum(1 for r in role_comp if r["estimator_kg"] > 0)
    )

    overall_steel = _accuracy(est_summary.total_steel_kg, mod_summary.total_steel_kg)

    similarity = round(
        (overall_steel * 0.40 + dia_acc * 0.30 + coverage["beam_coverage_pct"] * 0.15
         + beam_qty_acc * 0.075 + role_acc * 0.075),
        2,
    )

    return {
        "overall_steel_accuracy_pct": overall_steel,
        "project_accuracy_pct": overall_steel,
        "diameter_accuracy_pct": round(dia_acc, 4),
        "beam_coverage_pct": coverage["beam_coverage_pct"],
        "beam_quantity_accuracy_pct": round(beam_qty_acc, 4),
        "engineering_role_accuracy_pct": round(role_acc, 4),
        "overall_estimator_similarity_score": similarity,
        "scope_note": (
            "Reinforcement-only metrics. Concrete and Shuttering excluded "
            "from all accuracy and similarity calculations."
        ),
    }


def top_20_differences(beam_comparisons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = sorted(
        beam_comparisons,
        key=lambda x: abs(x["steel_kg"]["difference_kg"]),
        reverse=True,
    )[:20]
    return [
        {
            "rank": i + 1,
            "beam_id": bc["beam_id"],
            "estimator_kg": bc["steel_kg"]["estimator"],
            "model_kg": bc["steel_kg"]["model"],
            "difference_kg": bc["steel_kg"]["difference_kg"],
            "first_observable_difference": bc["first_observable_difference"],
        }
        for i, bc in enumerate(ranked)
    ]


def recommended_investigation_order(
    root_causes: Dict[str, Any], coverage: Dict[str, Any]
) -> List[str]:
    order = [
        "1. Reinforcement discovery / bar propagation — model Steel Summary shows steel on ~7/61 beams only.",
        "2. Compare project Reinforcement Total (Pink) table — diameter-wise MT totals vs model Diameter Summary.",
        "3. Audit beams with estimator steel but model zero (see model_incomplete_reinforcement_beams).",
        "4. Role-level gaps — Stirrups, Hooks, SFR, Spacer bars absent or under-reported in model.",
        "5. Beam-by-beam review of top 20 largest steel differences.",
    ]
    n_incomplete = len(coverage.get("model_incomplete_reinforcement_beams", []))
    if n_incomplete:
        order[2] = (
            f"3. Audit {n_incomplete} beams with estimator reinforcement but model zero steel."
        )
    return order
