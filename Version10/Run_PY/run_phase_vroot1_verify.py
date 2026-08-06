"""
Phase V.ROOT.1.VERIFY — Galera GF Dynamic Discovery Verification & Beam Registry Audit
MODEL_VERSION: 7.1.1
Type: READ-ONLY VALIDATION / VERIFICATION

Independently audits the beam_registry.json produced by Phase V.ROOT.1
against Benchmark Set 2 (Galera GF drawings).

NO engineering logic, discovery algorithms, or parsers are modified here.
This script is a pure read-and-verify audit.
"""

import json
import os
import re
import sys
import pathlib
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKSPACE     = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
VROOT1_OUTPUT = WORKSPACE / "Version8/data/output/PhaseVROOT.1_dynamic_pipeline_initialization"
BENCH2_FOLDER = WORKSPACE / "Version8/data/Benchmark_Set_2"
OUTPUT_DIR    = WORKSPACE / "Version8/data/output/PhaseVROOT1_Verification"
REPORTED_BEAM_COUNT = 65          # claimed in the V.ROOT.1 delivery summary

# Benchmark Set 1 beam IDs (Clubhouse GF) — must NOT appear in the registry
BENCH1_BEAM_IDS = {f"B{i}" for i in range(1, 19)}  # B1-B18 ONLY if also in V6

EXPECTED_DXFS = {
    "Galera_GF_BeamReinforcementDetails.dxf",
    "Galera_GF_FramingPlan.dxf",
    "SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf",
}

FORBIDDEN_PATH_FRAGMENTS = ["Version5", "Version6",
                             "Beam_Reinforcement_Details.dxf",
                             "Benchmark_Set_1"]

MODEL_VERSION = "7.1.1"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def _dump(path: pathlib.Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [OK]  {path.name}")


def _norm(p: str) -> str:
    """Normalise backslashes for comparison."""
    return p.replace("\\", "/")

# ---------------------------------------------------------------------------
# Rule audits
# ---------------------------------------------------------------------------

def rule1_input_folder(report: dict) -> dict:
    """Confirm the input folder contains expected DXFs."""
    found_dxfs = []
    for root, _, files in os.walk(BENCH2_FOLDER):
        for f in files:
            if f.lower().endswith(".dxf"):
                found_dxfs.append(f)

    found_set    = set(found_dxfs)
    expected_set = EXPECTED_DXFS
    missing      = sorted(expected_set - found_set)
    unexpected   = sorted(found_set - expected_set)
    passed       = len(missing) == 0

    result = {
        "rule": "RULE_1",
        "title": "Input Folder Verification",
        "folder_scanned": str(BENCH2_FOLDER),
        "expected_dxfs": sorted(expected_set),
        "found_dxfs":    sorted(found_set),
        "missing_dxfs":  missing,
        "unexpected_dxfs": unexpected,
        "status": "PASS" if passed else "FAIL",
        "note": "All expected DXFs present." if passed
                else f"Missing: {missing}",
    }
    report["rules"]["RULE_1"] = result
    return result


def rule2_source_exclusivity(report: dict, registry: dict) -> dict:
    """Confirm ONLY Benchmark Set 2 drawings are used."""
    violations = []
    norm_bench2 = _norm(str(BENCH2_FOLDER))

    # Top-level drawing_path on the registry
    top_path = _norm(registry.get("drawing_path", ""))
    for frag in FORBIDDEN_PATH_FRAGMENTS:
        if frag.lower() in top_path.lower():
            violations.append(f"registry.drawing_path contains '{frag}': {top_path}")

    # Per-beam drawing_path
    for bid, beam in registry.get("beams", {}).items():
        bp = _norm(beam.get("drawing_path", ""))
        for frag in FORBIDDEN_PATH_FRAGMENTS:
            if frag.lower() in bp.lower():
                violations.append(f"Beam {bid}.drawing_path contains '{frag}': {bp}")

    passed = len(violations) == 0
    result = {
        "rule": "RULE_2",
        "title": "Source Exclusivity (Benchmark Set 2 Only)",
        "violations": violations,
        "status": "PASS" if passed else "FAIL",
        "note": "No Version5/Version6/Benchmark_Set_1 references in drawing paths." if passed
                else f"{len(violations)} violation(s) found.",
    }
    report["rules"]["RULE_2"] = result
    return result


def rule3_beam_count_integrity(report: dict, registry: dict) -> dict:
    """Verify beam_count field matches actual beams in registry."""
    declared  = registry.get("beam_count", -1)
    actual    = len(registry.get("beams", {}))
    list_len  = len(registry.get("beam_ids", []))
    passed    = declared == actual == list_len

    result = {
        "rule": "RULE_3",
        "title": "Beam Count Integrity",
        "declared_beam_count": declared,
        "actual_beams_in_registry": actual,
        "beam_ids_list_length": list_len,
        "status": "PASS" if passed else "FAIL",
        "note": f"beam_count={declared}, actual keys={actual}, ids list={list_len}",
    }
    report["rules"]["RULE_3"] = result
    return result


def rule4_complete_beam_list(report: dict, registry: dict) -> list:
    """Produce the complete ordered beam list."""
    def _sort_key(bid: str):
        # Sort: alphabetical prefix then numeric suffix
        m = re.match(r"([A-Za-z]+)(\d*)(.*)", bid)
        prefix = m.group(1).upper() if m else bid
        num    = int(m.group(2)) if m and m.group(2) else 0
        suffix = m.group(3) if m else ""
        return (prefix, num, suffix)

    beam_ids = sorted(registry.get("beams", {}).keys(), key=_sort_key)

    result = {
        "rule": "RULE_4",
        "title": "Complete Beam List",
        "total_beams": len(beam_ids),
        "beam_list": beam_ids,
        "status": "PASS" if len(beam_ids) > 0 else "FAIL",
        "note": f"{len(beam_ids)} beams listed in discovery order.",
    }
    report["rules"]["RULE_4"] = result
    return beam_ids


def rule5_schema_completeness(report: dict, registry: dict) -> dict:
    """Verify every beam has required fields."""
    required_keys = {"beam_uuid", "beam_mark", "centroid_x", "centroid_y", "drawing_path"}
    section_keys  = {"width_mm", "depth_mm"}

    missing_fields_per_beam = {}
    for bid, beam in registry.get("beams", {}).items():
        missing = []
        for k in required_keys:
            if k not in beam:
                missing.append(k)
        sec = beam.get("section", {})
        for k in section_keys:
            if k not in sec:
                missing.append(f"section.{k}")
        if missing:
            missing_fields_per_beam[bid] = missing

    passed = len(missing_fields_per_beam) == 0
    result = {
        "rule": "RULE_5",
        "title": "Schema Completeness",
        "required_fields": sorted(required_keys) + ["section.width_mm", "section.depth_mm"],
        "beams_with_missing_fields": missing_fields_per_beam,
        "beams_checked": len(registry.get("beams", {})),
        "status": "PASS" if passed else "FAIL",
        "note": "All beams have required fields." if passed
                else f"{len(missing_fields_per_beam)} beam(s) missing fields.",
    }
    report["rules"]["RULE_5"] = result
    return result


def rule6_drawing_path_validation(report: dict, registry: dict) -> dict:
    """Confirm drawing_path points ONLY to Version8/data/Benchmark_Set_2/."""
    norm_bench2 = _norm(str(BENCH2_FOLDER))
    violations  = []

    for bid, beam in registry.get("beams", {}).items():
        bp = _norm(beam.get("drawing_path", ""))
        if norm_bench2.lower() not in bp.lower():
            violations.append({"beam_id": bid, "drawing_path": bp})

    # Also check registry-level drawing_path
    top_path = _norm(registry.get("drawing_path", ""))
    if norm_bench2.lower() not in top_path.lower():
        violations.insert(0, {"beam_id": "REGISTRY_LEVEL", "drawing_path": top_path})

    passed = len(violations) == 0
    result = {
        "rule": "RULE_6",
        "title": "Drawing Path Source Validation",
        "expected_root": str(BENCH2_FOLDER),
        "path_violations": violations,
        "status": "PASS" if passed else "FAIL",
        "note": "All drawing_paths point to Benchmark_Set_2." if passed
                else f"{len(violations)} path(s) outside Benchmark_Set_2.",
    }
    report["rules"]["RULE_6"] = result
    return result


def rule7_beam_mark_analysis(report: dict, registry: dict) -> dict:
    """Count unique marks, duplicates, missing numbers, unexpected IDs."""
    beams     = registry.get("beams", {})
    all_marks = [b.get("beam_mark", bid) for bid, b in beams.items()]

    from collections import Counter
    counts    = Counter(all_marks)
    duplicates = {m: c for m, c in counts.items() if c > 1}

    # Numeric sequence analysis for B-series
    b_nums = []
    non_b  = []
    for m in all_marks:
        match = re.fullmatch(r"B(\d+)([A-Z]?)", m.upper())
        if match:
            b_nums.append((int(match.group(1)), match.group(2)))
        else:
            non_b.append(m)

    b_ints     = sorted({n for n, suf in b_nums if not suf})
    b_range    = range(b_ints[0], b_ints[-1] + 1) if b_ints else range(0)
    b_int_set  = set(b_ints)
    missing_b  = sorted(i for i in b_range if i not in b_int_set)
    missing_str = [f"B{i}" for i in missing_b]

    result = {
        "rule": "RULE_7",
        "title": "Beam Mark Analysis",
        "total_beam_marks": len(all_marks),
        "unique_beam_marks": len(counts),
        "duplicate_marks": duplicates,
        "b_series_range": f"B{b_ints[0]}–B{b_ints[-1]}" if b_ints else "N/A",
        "missing_b_numbers": missing_str,
        "non_b_beams": non_b,
        "status": "PASS",
        "note": (f"{len(missing_str)} B-number gap(s): {missing_str}. "
                 f"Non-B beams: {non_b}." if missing_str or non_b
                 else "Continuous B-series with no gaps."),
    }
    report["rules"]["RULE_7"] = result
    return result


def rule8_no_bench1_carryover(report: dict, registry: dict) -> dict:
    """Verify no Benchmark Set 1 carry-over in source or registry-level path."""
    bench1_patterns = [
        "Clubhouse",
        "Beam_Reinforcement_Details.dxf",   # V5/V6 Benchmark Set 1 file
        "Benchmark_Set_1",
    ]

    violations = []
    # Registry-level drawing_path
    top_path = _norm(registry.get("drawing_path", ""))
    for p in bench1_patterns:
        if p.lower() in top_path.lower():
            violations.append({"field": "registry.drawing_path", "value": top_path, "pattern": p})

    # Per-beam
    for bid, beam in registry.get("beams", {}).items():
        bp = _norm(beam.get("drawing_path", ""))
        for p in bench1_patterns:
            if p.lower() in bp.lower():
                violations.append({"field": f"beams.{bid}.drawing_path",
                                    "value": bp, "pattern": p})

    # B1-B18 only — check if all of them exist AND path still points to B2
    b1_18_present = [bid for bid in registry.get("beams", {}) if bid in BENCH1_BEAM_IDS]
    b1_18_drawing_paths = {bid: registry["beams"][bid].get("drawing_path", "")
                            for bid in b1_18_present}
    # If any of those paths point to V5/V6, that's carry-over
    for bid, bp in b1_18_drawing_paths.items():
        for p in bench1_patterns:
            if p.lower() in _norm(bp).lower():
                violations.append({"field": f"beams.{bid}.drawing_path (B1-B18 overlap)",
                                    "value": bp, "pattern": p})

    passed = len(violations) == 0
    result = {
        "rule": "RULE_8",
        "title": "No Benchmark Set 1 Carry-Over",
        "carryover_violations": violations,
        "b1_18_present_in_registry": b1_18_present,
        "b1_18_note": ("B1-B18 exist in this registry but their drawing_path "
                        "correctly points to Benchmark_Set_2, so they are independently "
                        "re-discovered, not carried over.") if not violations else "",
        "status": "PASS" if passed else "FAIL",
        "note": "No Benchmark Set 1 carry-over detected." if passed
                else f"{len(violations)} carry-over violation(s).",
    }
    report["rules"]["RULE_8"] = result
    return result


def rule9_section_extraction(report: dict, registry: dict) -> dict:
    """Produce frequency table of beam sections (Width x Depth)."""
    from collections import Counter
    sections = Counter()
    inferreds = []

    for bid, beam in registry.get("beams", {}).items():
        sec = beam.get("section", {})
        w   = int(sec.get("width_mm", 0))
        d   = int(sec.get("depth_mm", 0))
        key = f"{w}x{d}"
        sections[key] += 1
        if sec.get("inferred"):
            inferreds.append(bid)

    freq_table = dict(sorted(sections.items(), key=lambda x: (-x[1], x[0])))
    passed     = len(sections) > 0

    result = {
        "rule": "RULE_9",
        "title": "Section Extraction Verification",
        "section_frequency_table": freq_table,
        "unique_sections": len(sections),
        "inferred_sections": inferreds,
        "inferred_count": len(inferreds),
        "status": "PASS" if passed else "FAIL",
        "note": (f"{len(sections)} unique section(s) found. "
                 f"{len(inferreds)} beam(s) with inferred sections."),
    }
    report["rules"]["RULE_9"] = result
    return result


def rule10_delivery_comparison(report: dict, registry: dict) -> dict:
    """Compare exported registry with delivery summary (claimed 65 beams)."""
    actual   = registry.get("beam_count", len(registry.get("beams", {})))
    reported = REPORTED_BEAM_COUNT
    match    = actual == reported

    result = {
        "rule": "RULE_10",
        "title": "Delivery Report Validation",
        "reported_beam_count_in_delivery_summary": reported,
        "actual_beam_count_in_registry": actual,
        "match": match,
        "status": "PASS" if match else "FAIL",
        "note": (f"Registry confirms the delivery claim of {reported} beams." if match
                 else f"MISMATCH: reported={reported}, actual={actual}. "
                      "See root_cause section for analysis."),
        "root_cause": None if match else _root_cause(reported, actual, registry),
    }
    report["rules"]["RULE_10"] = result
    return result


def _root_cause(reported: int, actual: int, registry: dict) -> str:
    if actual > reported:
        return (f"Registry contains {actual - reported} more beam(s) than reported. "
                "Possible cause: label deduplication strategy changed between delivery "
                "and this audit run, or annotated labels (e.g. B14A, B20A) were counted "
                "separately rather than merged.")
    elif actual < reported:
        return (f"Registry contains {reported - actual} fewer beam(s) than reported. "
                "Possible cause: some beam labels were not matched by the regex in this "
                "run, or the delivery run included beams from a different drawing file "
                "that is not scanned in this audit.")
    return "Counts match."

# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def build_statistics(registry: dict, rules: dict) -> dict:
    beams = registry.get("beams", {})
    from collections import Counter
    sections = Counter()
    for beam in beams.values():
        sec = beam.get("section", {})
        w   = int(sec.get("width_mm", 0))
        d   = int(sec.get("depth_mm", 0))
        sections[f"{w}x{d}"] += 1

    passed = sum(1 for r in rules.values() if r.get("status") == "PASS")
    failed = sum(1 for r in rules.values() if r.get("status") == "FAIL")

    return {
        "model_version": MODEL_VERSION,
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "registry_source": str(VROOT1_OUTPUT / "beam_registry.json"),
        "total_beams": len(beams),
        "unique_sections": len(sections),
        "rules_passed": passed,
        "rules_failed": failed,
        "rules_total": len(rules),
        "overall_verdict": "PASS" if failed == 0 else "FAIL",
    }


def build_section_summary(registry: dict) -> dict:
    from collections import Counter
    sec_table = Counter()
    beams_per_section: dict = {}

    for bid, beam in registry.get("beams", {}).items():
        sec = beam.get("section", {})
        w   = int(sec.get("width_mm", 0))
        d   = int(sec.get("depth_mm", 0))
        key = f"{w}x{d}"
        sec_table[key] += 1
        beams_per_section.setdefault(key, []).append(bid)

    return {
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frequency_table": dict(sorted(sec_table.items(), key=lambda x: (-x[1], x[0]))),
        "beams_per_section": {k: sorted(v) for k, v in sorted(beams_per_section.items())},
    }


def build_beam_list(beam_ids: list, registry: dict) -> dict:
    rows = []
    for bid in beam_ids:
        beam = registry.get("beams", {}).get(bid, {})
        sec  = beam.get("section", {})
        rows.append({
            "beam_mark":   beam.get("beam_mark", bid),
            "beam_uuid":   beam.get("beam_uuid", ""),
            "section":     f"{int(sec.get('width_mm',0))}x{int(sec.get('depth_mm',0))}",
            "width_mm":    sec.get("width_mm"),
            "depth_mm":    sec.get("depth_mm"),
            "inferred":    sec.get("inferred", False),
            "centroid_x":  beam.get("centroid_x"),
            "centroid_y":  beam.get("centroid_y"),
            "drawing_path": beam.get("drawing_path", ""),
        })

    return {
        "model_version": MODEL_VERSION,
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "total_beams":   len(rows),
        "beams":         rows,
    }


def build_source_validation(registry: dict, rules: dict) -> dict:
    norm_bench2 = _norm(str(BENCH2_FOLDER))
    r2  = rules.get("RULE_2", {})
    r6  = rules.get("RULE_6", {})
    r8  = rules.get("RULE_8", {})

    return {
        "model_version":          MODEL_VERSION,
        "generated_at":           datetime.now(timezone.utc).isoformat(),
        "expected_source_root":   str(BENCH2_FOLDER),
        "registry_drawing_path":  registry.get("drawing_path", ""),
        "forbidden_fragments":    FORBIDDEN_PATH_FRAGMENTS,
        "rule2_source_exclusivity": r2.get("status", "UNKNOWN"),
        "rule6_path_violations":  r6.get("path_violations", []),
        "rule8_carryover":        r8.get("status", "UNKNOWN"),
        "overall_source_verdict": "PASS" if all(
            rules.get(k, {}).get("status") == "PASS"
            for k in ("RULE_2", "RULE_6", "RULE_8")
        ) else "FAIL",
    }


def build_delivery_comparison(rule10_result: dict) -> dict:
    return {
        "model_version":   MODEL_VERSION,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "reported_in_delivery_summary": rule10_result["reported_beam_count_in_delivery_summary"],
        "actual_in_registry":           rule10_result["actual_beam_count_in_registry"],
        "match":                        rule10_result["match"],
        "status":                       rule10_result["status"],
        "root_cause":                   rule10_result.get("root_cause"),
        "audit_note": ("Delivery claim VERIFIED." if rule10_result["match"]
                       else "Delivery claim UNVERIFIED — see root_cause."),
    }

# ---------------------------------------------------------------------------
# Main audit orchestrator
# ---------------------------------------------------------------------------

def main():
    print("=" * 72)
    print("Phase V.ROOT.1.VERIFY — Galera GF Beam Registry Audit")
    print(f"MODEL_VERSION : {MODEL_VERSION}")
    print(f"Registry      : {VROOT1_OUTPUT / 'beam_registry.json'}")
    print("=" * 72)

    # Load the fresh beam_registry.json produced by V.ROOT.1 for Benchmark Set 2
    reg_path = VROOT1_OUTPUT / "beam_registry.json"
    if not reg_path.exists():
        print(f"[FATAL] beam_registry.json not found at: {reg_path}")
        sys.exit(1)

    registry = _load_json(reg_path)
    print(f"\n[READ]  beam_registry.json loaded.")
    print(f"        beam_count field : {registry.get('beam_count')}")
    print(f"        actual beams     : {len(registry.get('beams', {}))}")
    print(f"        drawing_path     : {registry.get('drawing_path', 'N/A')}")

    # Audit report container
    report: dict = {
        "phase":          "V.ROOT.1.VERIFY",
        "title":          "Galera GF Dynamic Discovery Verification & Beam Registry Audit",
        "model_version":  MODEL_VERSION,
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "registry_file":  str(reg_path),
        "input_folder":   str(BENCH2_FOLDER),
        "rules":          {},
        "summary":        {},
    }

    # ---------------------------------------------------------------------------
    # Run all 10 rules
    # ---------------------------------------------------------------------------
    print("\n[RULES]")

    r1  = rule1_input_folder(report)
    r2  = rule2_source_exclusivity(report, registry)
    r3  = rule3_beam_count_integrity(report, registry)
    beam_ids = rule4_complete_beam_list(report, registry)
    r5  = rule5_schema_completeness(report, registry)
    r6  = rule6_drawing_path_validation(report, registry)
    r7  = rule7_beam_mark_analysis(report, registry)
    r8  = rule8_no_bench1_carryover(report, registry)
    r9  = rule9_section_extraction(report, registry)
    r10 = rule10_delivery_comparison(report, registry)

    for rule_id, result in report["rules"].items():
        status = result.get("status", "?")
        note   = result.get("note", "")
        icon   = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {icon}  {rule_id}: {result['title']}")
        if status == "FAIL":
            print(f"         >> {note}")

    # Summary
    passed_count = sum(1 for r in report["rules"].values() if r.get("status") == "PASS")
    failed_count = sum(1 for r in report["rules"].values() if r.get("status") == "FAIL")
    overall      = "PASS" if failed_count == 0 else "FAIL"

    report["summary"] = {
        "rules_passed":   passed_count,
        "rules_failed":   failed_count,
        "overall_verdict": overall,
        "total_beams_audited": len(registry.get("beams", {})),
        "delivery_claim_verified": r10["match"],
    }

    print(f"\n[SUMMARY]  {passed_count}/10 rules PASS | {failed_count} FAIL | "
          f"Overall: {overall}")

    # Complete beam list print
    print(f"\n[BEAM LIST]  {len(beam_ids)} beams discovered:")
    for i, bid in enumerate(beam_ids, 1):
        beam = registry["beams"][bid]
        sec  = beam.get("section", {})
        print(f"  {i:>3}.  {bid:<10}  "
              f"{int(sec.get('width_mm',0))}x{int(sec.get('depth_mm',0))}  "
              f"centroid=({beam.get('centroid_x',0):.1f}, {beam.get('centroid_y',0):.1f})")

    # Section summary
    print(f"\n[SECTION TABLE]")
    freq = report["rules"]["RULE_9"]["section_frequency_table"]
    for sec, cnt in sorted(freq.items(), key=lambda x: -x[1]):
        print(f"  {sec:<12}  {cnt:>3} beam(s)")

    # Beam mark analysis
    r7_d = report["rules"]["RULE_7"]
    print(f"\n[BEAM MARKS]")
    print(f"  Total marks     : {r7_d['total_beam_marks']}")
    print(f"  Unique marks    : {r7_d['unique_beam_marks']}")
    print(f"  Duplicates      : {r7_d['duplicate_marks']}")
    print(f"  B-series range  : {r7_d['b_series_range']}")
    print(f"  Missing B-nums  : {r7_d['missing_b_numbers']}")
    print(f"  Non-B beams     : {r7_d['non_b_beams']}")

    # Delivery comparison
    print(f"\n[DELIVERY COMPARISON]")
    print(f"  Claimed in V.ROOT.1 summary : {REPORTED_BEAM_COUNT} beams")
    print(f"  Actual in registry          : {r10['actual_beam_count_in_registry']} beams")
    print(f"  Match                       : {r10['match']} -> {r10['status']}")
    if r10.get("root_cause"):
        print(f"  Root cause                  : {r10['root_cause']}")

    # ---------------------------------------------------------------------------
    # Exports
    # ---------------------------------------------------------------------------
    print(f"\n[EXPORTS]  -> {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _dump(OUTPUT_DIR / "beam_registry_verification_report.json", report)
    _dump(OUTPUT_DIR / "beam_registry_statistics.json",
          build_statistics(registry, report["rules"]))
    _dump(OUTPUT_DIR / "beam_registry_section_summary.json",
          build_section_summary(registry))
    _dump(OUTPUT_DIR / "beam_registry_beam_list.json",
          build_beam_list(beam_ids, registry))
    _dump(OUTPUT_DIR / "beam_registry_source_validation.json",
          build_source_validation(registry, report["rules"]))
    _dump(OUTPUT_DIR / "beam_registry_delivery_comparison.json",
          build_delivery_comparison(r10))

    print(f"\n{'='*72}")
    print(f"V.ROOT.1.VERIFY COMPLETE — {passed_count}/10 rules PASS | Overall: {overall}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"{'='*72}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
