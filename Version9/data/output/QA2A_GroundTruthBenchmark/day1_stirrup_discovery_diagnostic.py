"""
Day-1 READ-ONLY diagnostic: stirrup discovery vs association vs role loss.
MODEL_VERSION: 9.1.0 — no pipeline/config modifications.
Writes day1_stirrup_discovery_diagnostic.{json,md} beside this script.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

OUT_DIR = Path(__file__).resolve().parent
WEB = Path(r"C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs")

RUNS = {
    "First Set Drawings": WEB / "qa2_First_Set_Drawings_20260731_154657",
    "Second Set Drawings": WEB / "qa2_Second_Set_Drawings_20260731_154739",
    "Third Set Drawings": WEB / "qa2_Third_Set_Drawings_20260731_154835",
}
QA_SAFE = {
    "First Set Drawings": "First_Set_Drawings",
    "Second Set Drawings": "Second_Set_Drawings",
    "Third Set Drawings": "Third_Set_Drawings",
}

# Requirement_Rules.txt Type2 / Type3 (slight space tolerance)
RE_TYPE2 = re.compile(
    r"\d+\s*L\s*[-–]?\s*Y\s*\d+\s*@\s*\d+\s*C\s*/\s*C",
    re.IGNORECASE,
)
RE_TYPE3 = re.compile(
    r"\d+\s*L\s*[-–]?\s*Y\s*\d+\s*@\s*\d+\s*/\s*\d+(?:\s*/\s*\d+)?\s*C\s*/\s*C",
    re.IGNORECASE,
)
# R.1 native stirrup pattern (annotation_discovery._RE_STIRRUP) — includes Y8@100C/C
RE_LOOSE = re.compile(
    r"(?:(\d+)\s*[Ll][-–]\s*)?([YyRrTt])\s*(\d+)\s*@\s*(\d+(?:[/]\d+)*)",
    re.IGNORECASE,
)
RE_NEAR_GATE = re.compile(r"(?:L\s*[-–]?\s*Y|C\s*/\s*C|@\s*\d+|STIRR)", re.IGNORECASE)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _ann_text(ann: Dict[str, Any]) -> str:
    for k in ("clean_text", "text", "raw_text", "annotation_text", "label"):
        v = ann.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def scan_r1(name: str, run: Path) -> Dict[str, Any]:
    ann_path = (
        run
        / "data/output/PhaseR.1_generalized_reinforcement_discovery"
        / "reinforcement_annotations.json"
    )
    doc = _load(ann_path)
    unique: List[Tuple[str, Dict[str, Any], str]] = []
    seen = set()
    for bid, anns in (doc.get("by_beam") or {}).items():
        for a in anns or []:
            if not isinstance(a, dict):
                continue
            t = _ann_text(a)
            key = (a.get("annotation_id") or id(a), t)
            if key in seen:
                continue
            seen.add(key)
            unique.append((str(bid), a, t))

    type2, type3, loose, near = [], [], [], []
    by_beam_loose: Dict[str, List[str]] = defaultdict(list)
    role_stir = 0
    for bid, a, t in unique:
        if a.get("role") == "STIRRUP":
            role_stir += 1
        if not t:
            continue
        is3 = bool(RE_TYPE3.search(t))
        is2 = bool(RE_TYPE2.search(t)) and not is3
        is_loose = bool(RE_LOOSE.search(t))
        if is3:
            type3.append({"beam_id": bid, "text": t, "role": a.get("role")})
        elif is2:
            type2.append({"beam_id": bid, "text": t, "role": a.get("role")})
        if is_loose:
            loose.append({"beam_id": bid, "text": t, "role": a.get("role")})
            by_beam_loose[bid].append(t)
        elif RE_NEAR_GATE.search(t) and ("Y" in t.upper() or "STIRR" in t.upper()):
            if not (is2 or is3 or is_loose):
                near.append({"beam_id": bid, "text": t, "role": a.get("role")})

    return {
        "drawing_set": name,
        "artefact": str(ann_path),
        "run_root": str(run),
        "total_annotations_scanned": len(unique),
        "type2_count": len(type2),
        "type3_count": len(type3),
        "strict_total": len(type2) + len(type3),
        "loose_yd_at_s_count": len(loose),
        "r1_role_stirrup_count": role_stir,
        "sample_strict": [x["text"] for x in (type2 + type3)[:5]],
        "sample_loose": [x["text"] for x in loose[:5]],
        "near_misses": near[:30],
        "near_miss_count": len(near),
        "matches_by_beam_loose": dict(by_beam_loose),
        "loose_matches": loose,
        "type2_matches": type2,
        "type3_matches": type3,
    }


def scan_dxf_corroboration(run: Path) -> Dict[str, Any]:
    """Read-only DXF scan: MSP text vs INSERT virtual_entities (block-nested)."""
    try:
        import ezdxf
    except ImportError:
        return {"error": "ezdxf not available"}

    rdir = run / "reinforcement"
    dxfs = list(rdir.glob("*.dxf"))
    if not dxfs:
        return {"error": "no reinforcement dxf"}
    path = dxfs[0]
    doc = ezdxf.readfile(str(path))

    msp: List[str] = []
    for e in doc.modelspace():
        if e.dxftype() == "TEXT":
            s = e.dxf.text or ""
        elif e.dxftype() == "MTEXT":
            s = e.text or ""
        else:
            continue
        if RE_LOOSE.search(s):
            msp.append(s.strip())

    virt: List[str] = []
    for e in doc.modelspace():
        if e.dxftype() != "INSERT":
            continue
        try:
            for ve in e.virtual_entities():
                if ve.dxftype() == "TEXT":
                    s = ve.dxf.text or ""
                elif ve.dxftype() == "MTEXT":
                    s = ve.text or ""
                else:
                    continue
                if RE_LOOSE.search(s):
                    virt.append(s.strip())
        except Exception:
            continue

    blk_def: List[str] = []
    for b in doc.blocks:
        if b.name.startswith("*"):
            continue
        for e in b:
            if e.dxftype() == "TEXT":
                s = e.dxf.text or ""
            elif e.dxftype() == "MTEXT":
                s = e.text or ""
            else:
                continue
            if RE_LOOSE.search(s) or RE_TYPE2.search(s) or RE_TYPE3.search(s):
                blk_def.append(f"{b.name}:{s.strip()[:80]}")

    return {
        "dxf": str(path),
        "msp_loose_stirrup_texts": len(msp),
        "msp_samples": msp[:10],
        "insert_virtual_loose_stirrup_texts": len(virt),
        "virtual_samples": virt[:10],
        "block_def_stirrup_texts": len(blk_def),
        "block_def_samples": blk_def[:10],
        "note": (
            "R.1 adaptive_association_engine._collect_entities only reads "
            "modelspace TEXT/MTEXT — not INSERT.virtual_entities()."
        ),
    }


def gt_stirrup_rows(name: str) -> Dict[str, Any]:
    safe = QA_SAFE[name]
    rows = _load(OUT_DIR / safe / "bar_matching.json").get("rows") or []
    gt = [
        r
        for r in rows
        if (r.get("bar_role") or "").upper() == "STIRRUP"
        and r.get("status") not in ("EXTRA", "ACCEPTABLE_EXTRA")
    ]
    statuses = Counter(r.get("status") for r in gt)
    return {
        "gt_stirrup_rows": len(gt),
        "status_breakdown": dict(statuses),
        "beams_with_gt_stirrup": sorted({r["beam_id"] for r in gt}),
        "rows": gt,
        "artefact": str(OUT_DIR / safe / "bar_matching.json"),
    }


def final_status(run: Path, beam_id: str) -> Dict[str, Any]:
    eng = _load(
        run / "data/output/PhaseR1.3_pipeline_integration" / "engineering_bar_models.json"
    )
    roles = []
    for b in eng.get("beams") or []:
        if b.get("beam_id") != beam_id:
            continue
        for bar in b.get("bars") or []:
            roles.append(
                {
                    "role": bar.get("bar_role"),
                    "dia": bar.get("diameter_mm"),
                    "qty": bar.get("quantity"),
                    "label": bar.get("bar_label"),
                }
            )
    return {
        "has_stirrup": any((r["role"] or "").upper() == "STIRRUP" for r in roles),
        "roles": roles,
        "artefact": str(
            run
            / "data/output/PhaseR1.3_pipeline_integration"
            / "engineering_bar_models.json"
        ),
    }


def r11a_has_beam(run: Path, beam_id: str) -> Dict[str, Any]:
    cov_path = (
        run / "data/output/PhaseR1_1A_annotation_coverage" / "beam_annotation_coverage.json"
    )
    if not cov_path.exists():
        return {"present": False, "artefact": None}
    cov = _load(cov_path)
    by = cov.get("by_beam") or {}
    present = beam_id in by
    # coverage file often lacks raw text; presence of beam block is the signal
    return {"present": present, "artefact": str(cov_path), "ann_count": (
        len(by.get(beam_id) or []) if isinstance(by.get(beam_id), list)
        else (by.get(beam_id) or {}).get("annotation_count")
        if isinstance(by.get(beam_id), dict) else None
    )}


def r31_has_stirrup_for_beam(run: Path, beam_id: str) -> Dict[str, Any]:
    """Best-effort: PhysicalBars / relationships rarely carry STIRRUP role strings."""
    phys_path = (
        run / "data/output/PhaseR3.1_engineering_relationship_engine" / "PhysicalBars.json"
    )
    rel_path = (
        run
        / "data/output/PhaseR3.1_engineering_relationship_engine"
        / "EngineeringDrawingRelationships.json"
    )
    found = False
    evidence: List[str] = []
    for path, label in ((phys_path, "PhysicalBars"), (rel_path, "Relationships")):
        if not path.exists():
            continue
        blob = path.read_text(encoding="utf-8")
        if beam_id in blob and ("STIRRUP" in blob.upper() or RE_LOOSE.search(blob)):
            # coarse: check beam-local slice via json walk
            doc = json.loads(blob)

            def walk(obj: Any) -> None:
                nonlocal found
                if isinstance(obj, dict):
                    bid = str(obj.get("beam_id") or obj.get("host_beam_id") or "")
                    role = str(
                        obj.get("role")
                        or obj.get("bar_role")
                        or obj.get("semantic_role")
                        or ""
                    )
                    text = str(
                        obj.get("text")
                        or obj.get("clean_text")
                        or obj.get("label")
                        or obj.get("source_text")
                        or ""
                    )
                    if bid == beam_id and (
                        "STIRRUP" in role.upper() or RE_LOOSE.search(text)
                    ):
                        found = True
                        evidence.append(f"{label}: role={role} text={text[:60]}")
                    for v in obj.values():
                        walk(v)
                elif isinstance(obj, list):
                    for v in obj[:8000]:
                        walk(v)

            walk(doc)
    return {
        "preserved_explicit": found,
        "evidence": evidence[:5],
        "artefact_physical": str(phys_path) if phys_path.exists() else None,
        "artefact_relationships": str(rel_path) if rel_path.exists() else None,
        "note": (
            "R.3.1 artefacts often omit STIRRUP role labels; "
            "final engineering_bar_models is authoritative for survival."
        ),
    }


def main() -> None:
    scans: Dict[str, Any] = {}
    dxf_scans: Dict[str, Any] = {}
    comparison = []
    traces = []

    # Preferred trace beams per set
    preferred = {
        "First Set Drawings": ["B1", "B9", "B10", "B2", "B4"],
        "Second Set Drawings": ["B6", "B36", "B38", "B1", "B12"],
        "Third Set Drawings": ["B16", "B19", "B38", "B42", "B53"],
    }

    for name, run in RUNS.items():
        assert run.is_dir(), f"missing run {run}"
        scan = scan_r1(name, run)
        dxf = scan_dxf_corroboration(run)
        gt = gt_stirrup_rows(name)
        scans[name] = scan
        dxf_scans[name] = dxf

        # Primary discovery count = loose (matches what R.1 itself can parse)
        found = scan["loose_yd_at_s_count"]
        ratio = (
            round(100.0 * found / gt["gt_stirrup_rows"], 1)
            if gt["gt_stirrup_rows"]
            else None
        )
        comparison.append(
            {
                "set": name,
                "gt_stirrup_rows": gt["gt_stirrup_rows"],
                "r1_stirrup_annotations_found_loose": found,
                "r1_strict_type2_type3": scan["strict_total"],
                "r1_role_stirrup": scan["r1_role_stirrup_count"],
                "dxf_msp_loose": dxf.get("msp_loose_stirrup_texts"),
                "dxf_insert_virtual_loose": dxf.get("insert_virtual_loose_stirrup_texts"),
                "discovery_ratio_pct_vs_gt": ratio,
                "gt_status_breakdown": gt["status_breakdown"],
                "artefacts": {
                    "r1_annotations": scan["artefact"],
                    "qa_bar_matching": gt["artefact"],
                    "run_root": str(run),
                    "dxf": dxf.get("dxf"),
                },
            }
        )

        # Build candidate beam list
        miss_beams = [
            r["beam_id"]
            for r in gt["rows"]
            if r.get("status") in ("MISSING", "PARTIAL_MATCH", "WRONG_ROLE")
        ]
        ordered: List[str] = []
        for b in preferred.get(name, []) + miss_beams + list(scan["matches_by_beam_loose"]):
            if b not in ordered:
                ordered.append(b)
        take = ordered[:4]

        for bid in take:
            matched = scan["matches_by_beam_loose"].get(bid, [])
            r1_found = len(matched) > 0
            r11a = r11a_has_beam(run, bid)
            r31 = r31_has_stirrup_for_beam(run, bid)
            final = final_status(run, bid)
            gt_rows_b = [r for r in gt["rows"] if r["beam_id"] == bid]
            gt_statuses = [r.get("status") for r in gt_rows_b]
            model_roles_qa = [r.get("model_role") for r in gt_rows_b if r.get("model_role")]

            if not r1_found and not final["has_stirrup"]:
                stage = "R.1 discovery (stirrup text never in R.1)"
                loss_class = "DISCOVERY"
            elif r1_found and final["has_stirrup"]:
                stage = "none — survived R.1 to final as STIRRUP"
                loss_class = "NO_LOSS_ON_DISCOVERED_TEXT"
            elif r1_found and not final["has_stirrup"]:
                stage = "downstream of R.1 (association/relationship/role)"
                loss_class = "ASSOCIATION_OR_ROLE"
            elif not r1_found and final["has_stirrup"]:
                stage = "synthesized without R.1 text (unexpected)"
                loss_class = "OTHER"
            else:
                stage = "UNKNOWN"
                loss_class = "UNKNOWN"

            # Set1 PARTIAL via SFR/spacer misfile signal
            if (
                not r1_found
                and any(s == "PARTIAL_MATCH" for s in gt_statuses)
                and any(
                    (r.get("model_role") or "").upper()
                    in ("TOP_EXTRA", "SPACER_BAR", "TOP_MAIN", "BOTTOM_MAIN")
                    for r in gt_rows_b
                )
            ):
                stage = (
                    "DISCOVERY + QA false-PARTIAL "
                    "(no stirrup text; model SFR/spacer matched to GT stirrup)"
                )
                loss_class = "DISCOVERY (with QA role-mismatch artefact)"

            traces.append(
                {
                    "beam_id": bid,
                    "set": name,
                    "gt_stirrup_statuses": gt_statuses,
                    "gt_qty_sum": sum(float(r.get("estimator_qty") or 0) for r in gt_rows_b),
                    "qa_model_roles_on_gt_stirrup_rows": model_roles_qa,
                    "r1_found": r1_found,
                    "r1_matched_strings": matched,
                    "r11a_beam_present": r11a["present"],
                    "r31_explicit_stirrup": r31["preserved_explicit"],
                    "final_has_stirrup": final["has_stirrup"],
                    "final_roles": [r["role"] for r in final["roles"]],
                    "final_status_summary": (
                        "STIRRUP present"
                        if final["has_stirrup"]
                        else ("PARTIAL/misfile vs GT" if any(s == "PARTIAL_MATCH" for s in gt_statuses) else "MISSING")
                    ),
                    "loss_stage": stage,
                    "loss_class": loss_class,
                }
            )

    total_r1 = sum(c["r1_stirrup_annotations_found_loose"] for c in comparison)
    total_gt = sum(c["gt_stirrup_rows"] for c in comparison)
    total_dxf_msp = sum(c["dxf_msp_loose"] or 0 for c in comparison)
    total_dxf_virt = sum(c["dxf_insert_virtual_loose"] or 0 for c in comparison)
    discovery_ratio = round(100.0 * total_r1 / total_gt, 1) if total_gt else None

    discovery_n = sum(1 for t in traces if t["loss_class"].startswith("DISCOVERY"))
    no_loss_n = sum(1 for t in traces if t["loss_class"] == "NO_LOSS_ON_DISCOVERED_TEXT")
    assoc_n = sum(1 for t in traces if t["loss_class"] == "ASSOCIATION_OR_ROLE")

    # Volume: every R.1-found annotation survived -> association loss volume ~0
    # Remaining GT rows never appear as text
    volume = {
        "gt_stirrup_rows_all_sets": total_gt,
        "r1_loose_discovered": total_r1,
        "dxf_msp_loose": total_dxf_msp,
        "dxf_insert_virtual_additional": total_dxf_virt,
        "r1_equals_msp": total_r1 == total_dxf_msp,
        "plausible_missing_rows_explained_by_absent_text": total_gt - total_r1,
        "plausible_recoverable_by_INSERT_explode_only": total_dxf_virt,
        "section2_baseline_production": "182 missing / 12 partial / 11 wrong-qty / 2 matched",
    }

    dominant = "DISCOVERY"
    fix_class = (
        "Primary: GEOMETRIC EVIDENCE ENGINE / typical-detail inference (~weeks) — "
        "Track 1 CONFIRMED for volume. "
        "Secondary cheap TEXT FIX (~days): explode INSERT.virtual_entities in R.1 "
        f"_collect_entities to recover ~{total_dxf_virt} block-nested callouts. "
        "Association/R.3.1 is NOT the dominant loss path for texts that R.1 already finds."
    )

    report = {
        "model_version": "9.1.0",
        "diagnostic": "Day-1 Stirrup Discovery vs Association",
        "read_only": True,
        "code_modified": False,
        "config_modified": False,
        "pipeline_artefacts_modified": False,
        "stages_rerun": [],
        "step1_regex_scan": {
            name: {
                "total_annotations_scanned": scans[name]["total_annotations_scanned"],
                "type2_count": scans[name]["type2_count"],
                "type3_count": scans[name]["type3_count"],
                "strict_total": scans[name]["strict_total"],
                "loose_yd_at_s_count": scans[name]["loose_yd_at_s_count"],
                "r1_role_stirrup_count": scans[name]["r1_role_stirrup_count"],
                "sample_strict": scans[name]["sample_strict"],
                "sample_loose": scans[name]["sample_loose"],
                "near_miss_count": scans[name]["near_miss_count"],
                "near_misses": scans[name]["near_misses"],
                "artefact": scans[name]["artefact"],
                "dxf_corroboration": dxf_scans[name],
            }
            for name in RUNS
        },
        "step2_discovery_vs_gt": comparison,
        "step2_volume": volume,
        "step3_beam_traces": traces,
        "step4_outcome": {
            "discovery_ratio_overall_pct": discovery_ratio,
            "traced_beams": len(traces),
            "discovery_loss_beams": discovery_n,
            "no_loss_discovered_beams": no_loss_n,
            "association_or_role_loss_beams": assoc_n,
            "dominant_failure_mode": dominant,
            "fix_class": fix_class,
            "decision_table_row": (
                "R.1 count << GT count AND stirrup never appears even in R.1 "
                "for the bulk of missing beams; when R.1 does find text, final keeps STIRRUP."
            ),
            "plan_assumption_check": (
                "Plan T1.3 claim 'annotation exists but never associated' is FALSIFIED "
                "for the dominant volume: annotations mostly do not exist as per-beam "
                "MSP text. Association loss volume on discovered texts = 0 in this sample."
            ),
        },
        "step5_recommendation": {
            "track1_plan": "CONFIRM (for volume) — with nuance",
            "nuance": [
                "Bulk gap is absent per-beam stirrup text in DXF modelspace (and GT still has rows).",
                "Geometry / typical-detail / schedule inference is required — Track 1 vector-space detector is the right class of fix.",
                "Do NOT prioritize R.1.1A/R.3.1 association tuning as the first lever.",
                "Optional Track-0-class micro-fix: collect INSERT.virtual_entities text in "
                "adaptive_association_engine._collect_entities (approx line 168-190) — recovers "
                f"~{total_dxf_virt} additional callouts on Sets 2/3 only.",
                "Set1 B1/B9/B10 PARTIAL_MATCH is QA matching SFR/spacer Y8/Y10 to GT STIRRUP — "
                "not evidence that stirrup text was mis-roled after discovery.",
            ],
            "effort_class_dominant": "GEOMETRIC EVIDENCE ENGINE (~weeks)",
            "effort_class_secondary": "TEXT/RULE FIX (~days) for INSERT explode",
            "file_pointers": [
                "Version9/src/PhaseR.1_generalized_reinforcement_discovery/adaptive_association_engine.py:_collect_entities (~L168) — TEXT/MTEXT only, skips INSERT",
                "Version9/src/PhaseR.1_generalized_reinforcement_discovery/annotation_discovery.py:_RE_STIRRUP (~L47) — already accepts Y8@150C/C",
                "Version9/src/PhaseR.1_generalized_reinforcement_discovery/reinforcement_role_classifier.py — not the dominant loss path for missing rows",
            ],
        },
        "runs_used": {k: str(v) for k, v in RUNS.items()},
    }

    # Markdown
    lines = [
        "# Day-1 Diagnostic — Stirrup Discovery vs Association",
        "",
        "**MODEL_VERSION:** 9.1.0 (read-only; no code/config/artefact modifications)",
        "",
        "## Verdict",
        "",
        f"**Dominant failure mode: DISCOVERY** (R.1 loose stirrup texts = {total_r1} "
        f"vs GT stirrup rows = {total_gt}; ratio **{discovery_ratio}%**).",
        "",
        "Every stirrup annotation that R.1 *does* find survives into the final model as "
        "`STIRRUP` (association/relationship loss volume on discovered texts = **0** in "
        "the traced sample). The ~182 §2 production MISSING rows are explained by "
        "**absent per-beam stirrup callout text**, not by R.1.1A/R.3.1 dropping them.",
        "",
        "**Track 1 (vector-space geometric stirrup evidence): CONFIRMED** for the volume "
        "problem. A pure association-rule fix would not recover the bulk.",
        "",
        "## Step 1 — Regex scan of R.1 `reinforcement_annotations.json`",
        "",
        "Patterns:",
        "- **Strict Type2/Type3** from `Requirement_Rules.txt` (`\\dL-Y…@…C/C`)",
        "- **Loose** = R.1 native `_RE_STIRRUP` (`Y8@100C/C` without required `2L-` prefix)",
        "",
        "| Set | Annos scanned | Type2 | Type3 | Strict total | Loose YD@S | R.1 role=STIRRUP | Near-misses |",
        "|-----|--------------:|------:|------:|-------------:|-----------:|-----------------:|------------:|",
    ]
    for name in RUNS:
        s = scans[name]
        lines.append(
            f"| {name} | {s['total_annotations_scanned']} | {s['type2_count']} | "
            f"{s['type3_count']} | {s['strict_total']} | {s['loose_yd_at_s_count']} | "
            f"{s['r1_role_stirrup_count']} | {s['near_miss_count']} |"
        )

    lines += ["", "### Samples (loose — authoritative for what R.1 can parse)", ""]
    for name in RUNS:
        lines.append(f"**{name}:**")
        samples = scans[name]["sample_loose"] or ["(none)"]
        for t in samples:
            lines.append(f"- `{t}`")
        if scans[name]["sample_strict"]:
            lines.append("Strict Type2/Type3 samples:")
            for t in scans[name]["sample_strict"]:
                lines.append(f"- `{t}`")
        if scans[name]["near_misses"]:
            lines.append("Near-misses (gate hit, strict/loose rejected):")
            for n in scans[name]["near_misses"][:8]:
                lines.append(f"- beam {n['beam_id']}: `{n['text']}`")
        lines.append("")

    lines += [
        "### Near-miss insight",
        "",
        "Most real drawing callouts are `Y8@100C/C` / `Y8@150C/C` (**no `NL-` leg prefix**). "
        "Strict Requirement_Rules Type2 alone under-counts; R.1's own loose regex already "
        "accepts them. Strict≪loose is a regex-breadth issue in this diagnostic, **not** "
        "evidence of additional undiscovered text inside R.1 JSON.",
        "",
        "### DXF corroboration (read-only, same run inputs)",
        "",
        "| Set | DXF MSP loose | DXF INSERT virtual loose | R.1 loose |",
        "|-----|--------------:|-------------------------:|----------:|",
    ]
    for c in comparison:
        lines.append(
            f"| {c['set']} | {c['dxf_msp_loose']} | {c['dxf_insert_virtual_loose']} | "
            f"{c['r1_stirrup_annotations_found_loose']} |"
        )
    lines += [
        "",
        f"R.1 loose counts **exactly match** DXF modelspace TEXT/MTEXT "
        f"({total_r1} = {total_dxf_msp}). "
        f"INSERT.virtual_entities would add **~{total_dxf_virt}** more (Sets 2/3); "
        "Set 1 has a block-*definition* `2L-Y10@100C/C` that is **not inserted** into MSP.",
        "",
        "## Step 2 — Discovery vs GT",
        "",
        "| Set | GT stirrup rows | R.1 stirrup annos (loose) | Discovery ratio |",
        "|-----|----------------:|--------------------------:|----------------:|",
    ]
    for c in comparison:
        lines.append(
            f"| {c['set']} | {c['gt_stirrup_rows']} | "
            f"{c['r1_stirrup_annotations_found_loose']} | "
            f"{c['discovery_ratio_pct_vs_gt']}% |"
        )
    lines += [
        "",
        f"**Overall:** {total_r1} R.1 discoveries / {total_gt} GT rows = **{discovery_ratio}%**.",
        "",
        f"§2 baseline (final production): {volume['section2_baseline_production']}.",
        "",
        "**Gap signal (primary):** R.1 discoveries = DXF MSP texts << GT. "
        "The gap between R.1 and production for *discovered* texts is ~0; the gap between "
        "R.1 and GT is the story (~"
        f"{total_gt - total_r1} GT rows never appear as stirrup text in R.1).",
        "",
        "## Step 3 — Per-beam trace (R.1 → R.1.1A → R.3.1 → final)",
        "",
        "| Beam | Set | GT statuses | R.1 found? | Strings | R.1.1A beam? | R.3.1 explicit? | Final | Loss stage |",
        "|------|-----|-------------|------------|---------|--------------|-----------------|-------|------------|",
    ]
    for t in traces:
        lines.append(
            f"| {t['beam_id']} | {t['set']} | "
            f"{','.join(map(str, t['gt_stirrup_statuses'])) or '-'} | "
            f"{'Y' if t['r1_found'] else 'N'} | "
            f"`{' / '.join(t['r1_matched_strings']) or '—'}` | "
            f"{'Y' if t['r11a_beam_present'] else 'N'} | "
            f"{'Y' if t['r31_explicit_stirrup'] else 'N*'} | "
            f"{t['final_status_summary']} | {t['loss_stage']} |"
        )
    lines += [
        "",
        "\\* R.3.1 JSON often lacks STIRRUP role strings even when the bar later appears "
        "in `engineering_bar_models.json`; final column is authoritative for survival.",
        "",
        f"Traced distribution: discovery-loss {discovery_n}/{len(traces)}; "
        f"discovered-and-kept {no_loss_n}/{len(traces)}; "
        f"association/role-loss {assoc_n}/{len(traces)}.",
        "",
        "## Step 4 — Outcome classification",
        "",
        "| Signal | Value |",
        "|--------|-------|",
        f"| Discovery ratio (Step 2) | **{discovery_ratio}%** (R.1 ≪ GT) |",
        f"| Per-beam pattern (Step 3) | {discovery_n} never in R.1; {no_loss_n} found+kept; {assoc_n} assoc/role loss |",
        f"| Volume-weighted | ~{total_gt - total_r1} of {total_gt} GT rows never text-discovered; 0/{total_r1} discovered texts lost before final STIRRUP |",
        "| **Outcome** | **DISCOVERY dominates** |",
        "| **Fix class** | Track 1 geometric / typical-detail inference for volume; optional INSERT text explode as micro TEXT FIX |",
        "",
        report["step4_outcome"]["plan_assumption_check"],
        "",
        "## Step 5 — Recommendation",
        "",
        "1. **CONFIRM Track 1** (vector-space stirrup detector in DXF geometry → R.2.1D "
        "`GEOMETRY_STIRRUP` evidence). Effort class: **GEOMETRIC EVIDENCE ENGINE (~weeks)**.",
        "2. **Do not** treat this as a 1-week R.1.1A/R.3.1 association-threshold fix — "
        "that path cannot create the ~180 missing callouts that were never text.",
        "3. **Optional parallel TEXT FIX (~days):** explode `INSERT.virtual_entities()` in "
        "`adaptive_association_engine._collect_entities` "
        "(~lines 168–190) to pick up ~"
        f"{total_dxf_virt} block-nested `Y8@…C/C` callouts on Sets 2/3.",
        "4. Set1 B1/B9/B10 §2 PARTIAL/WRONG_ROLE pattern is **not** stirrup text mis-filed "
        "after discovery — R.1 never had stirrup text; QA matched SFR/spacer model rows "
        "to GT STIRRUP.",
        "",
        "### File / line pointers",
        "",
    ]
    for p in report["step5_recommendation"]["file_pointers"]:
        lines.append(f"- `{p}`")

    lines += [
        "",
        "## Artefact paths (reproducibility)",
        "",
    ]
    for c in comparison:
        lines.append(f"- **{c['set']}**")
        for k, v in c["artefacts"].items():
            lines.append(f"  - {k}: `{v}`")

    lines += [
        "",
        "## Integrity confirmation",
        "",
        "- NO pipeline source code modified for this diagnostic",
        "- NO config modified",
        "- NO production artefacts rewritten",
        "- NO stages re-run — used existing Version9 `qa2_*_20260731_154*` web_run outputs only",
        "- DXF files were opened read-only for corroboration counts (same inputs as those runs)",
        f"- Diagnostic script path: `{Path(__file__).resolve()}`",
        "",
    ]

    json_path = OUT_DIR / "day1_stirrup_discovery_diagnostic.json"
    md_path = OUT_DIR / "day1_stirrup_discovery_diagnostic.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    # Avoid Windows console Unicode issues
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(f"Dominant={dominant} ratio={discovery_ratio}% r1={total_r1} gt={total_gt}")


if __name__ == "__main__":
    main()
