"""
Metrics and evidence recall for P2.5.0.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

MODEL_VERSION = "10.6.0"


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 2) if d else 0.0


def per_beam_recall(evidence: Dict[str, Any], qa: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pipeline evidence coverage (deterministic owned evidence captured in package).
    GT-verified recall is computed separately when GT annotation/bar lists exist.
    """
    counts = evidence.get("counts") or {}
    inclusion = qa.get("inclusion") or {}
    ann_n = int(counts.get("annotations") or 0)
    ldr_n = int(counts.get("leaders") or 0)
    bar_n = int(counts.get("reinforcement") or 0)
    return {
        "pipeline_annotation_coverage_pct": _pct(inclusion.get("annotations_in_window", 0), ann_n)
        if ann_n
        else None,
        "pipeline_leader_coverage_pct": _pct(inclusion.get("leaders_in_window", 0), ldr_n)
        if ldr_n
        else None,
        "pipeline_reinforcement_coverage_pct": _pct(inclusion.get("bars_in_window", 0), bar_n)
        if bar_n
        else None,
        "denominator_source": "pipeline_owned_evidence",
        "annotation_denom": ann_n,
        "leader_denom": ldr_n,
        "reinforcement_denom": bar_n,
    }


def gt_verified_recall(
    *,
    evidence: Dict[str, Any],
    gt_bar_count: int,
    gt_roles: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    GT-verified reinforcement evidence recall where GT supports a denominator.
    Annotation/leader GT IDs are generally unavailable — report UNKNOWN rather
    than inventing 100%.
    """
    bars = evidence.get("reinforcement") or []
    # Presence of any physical reinforcement evidence when GT has bars
    if gt_bar_count <= 0:
        return {
            "gt_reinforcement_recall_pct": None,
            "gt_annotation_recall_pct": None,
            "gt_leader_recall_pct": None,
            "note": "no_gt_bars_for_beam",
        }
    # Conservative: captured if we have at least one reinforcement object
    # Full bar-level GT geometry matching is out of scope for P2.5.0
    captured = 1.0 if bars else 0.0
    return {
        "gt_reinforcement_evidence_present": bool(bars),
        "gt_bar_count": gt_bar_count,
        "gt_reinforcement_recall_pct": round(100.0 * captured, 2) if bars else 0.0,
        "gt_annotation_recall_pct": None,
        "gt_leader_recall_pct": None,
        "note": (
            "GT annotation/leader IDs unavailable in estimator workbook; "
            "only reinforcement presence vs GT bar existence is reported."
        ),
        "gt_roles": gt_roles or [],
    }


def aggregate_metrics(beam_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(beam_rows)
    render_ok = sum(1 for r in beam_rows if r.get("render_success"))
    render_fail = n - render_ok
    qa_pass = sum(1 for r in beam_rows if r.get("crop_qa_overall") == "PASS")
    qa_partial = sum(1 for r in beam_rows if r.get("crop_qa_overall") == "PARTIAL")
    qa_fail = sum(1 for r in beam_rows if r.get("crop_qa_overall") == "FAIL")

    beam_present = sum(1 for r in beam_rows if r.get("beam_present"))
    reinf = sum(1 for r in beam_rows if r.get("reinforcement_present"))
    ann = sum(1 for r in beam_rows if r.get("annotation_present"))
    ldr = sum(1 for r in beam_rows if r.get("leader_present"))
    chain = sum(1 for r in beam_rows if r.get("leader_chain_complete"))
    expanded = sum(1 for r in beam_rows if r.get("expanded"))
    clipped = sum(1 for r in beam_rows if r.get("evidence_clipped"))
    neighbour = sum(1 for r in beam_rows if r.get("neighbour_ambiguity"))

    gate_fail_freq: Counter = Counter()
    for r in beam_rows:
        for g in r.get("hard_fails") or []:
            gate_fail_freq[g] += 1
        for g in r.get("soft_fails") or []:
            gate_fail_freq[g] += 1

    # Pipeline coverage averages (ignore None)
    def avg(key: str) -> Optional[float]:
        vals = [r.get(key) for r in beam_rows if r.get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    gt_reinf_present = sum(1 for r in beam_rows if r.get("gt_reinforcement_evidence_present"))
    gt_with_bars = sum(1 for r in beam_rows if int(r.get("gt_bar_count") or 0) > 0)

    return {
        "model_version": MODEL_VERSION,
        "beams_processed": n,
        "successful_renders": render_ok,
        "failed_renders": render_fail,
        "crop_qa_pass_pct": _pct(qa_pass, n),
        "crop_qa_partial_pct": _pct(qa_partial, n),
        "crop_qa_fail_pct": _pct(qa_fail, n),
        "crop_qa_pass": qa_pass,
        "crop_qa_partial": qa_partial,
        "crop_qa_fail": qa_fail,
        "beam_presence_pct": _pct(beam_present, n),
        "reinforcement_evidence_coverage_pct": _pct(reinf, n),
        "annotation_evidence_coverage_pct": _pct(ann, n),
        "leader_evidence_coverage_pct": _pct(ldr, n),
        "leader_chain_completeness_pct": _pct(chain, n),
        "beams_requiring_crop_expansion": expanded,
        "clipped_evidence_cases": clipped,
        "neighbor_ambiguity_cases": neighbour,
        "rendering_failures": render_fail,
        "top_crop_evidence_failure_causes": gate_fail_freq.most_common(12),
        "avg_pipeline_annotation_coverage_pct": avg("pipeline_annotation_coverage_pct"),
        "avg_pipeline_leader_coverage_pct": avg("pipeline_leader_coverage_pct"),
        "avg_pipeline_reinforcement_coverage_pct": avg(
            "pipeline_reinforcement_coverage_pct"
        ),
        "gt_verified": {
            "beams_with_gt_bars": gt_with_bars,
            "beams_with_reinforcement_evidence": gt_reinf_present,
            "gt_reinforcement_presence_pct": _pct(gt_reinf_present, gt_with_bars),
            "note": (
                "GT annotation/leader recall not claimed — estimator GT lacks "
                "annotation/leader entity IDs."
            ),
        },
    }
