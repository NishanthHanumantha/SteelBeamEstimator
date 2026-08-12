"""Metrics for P2.5.2 Vision candidate selection / crop QA."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Sequence

from .config import (
    OUTCOME_CANDIDATE,
    OUTCOME_DEFERRED,
    OUTCOME_EXCLUDED,
    P0,
    P1,
    P2,
    P3,
)


def compute_metrics(
    *,
    selections: Sequence[Dict[str, Any]],
    manifests: Sequence[Dict[str, Any]],
    eligible_intent_count: int,
) -> Dict[str, Any]:
    unresolved = sum(
        1
        for s in selections
        if (s.get("deterministic_intent") or {}).get("quantity_status") == "UNRESOLVED"
    )
    ambiguous = sum(
        1
        for s in selections
        if "AMBIGUOUS_QUANTITY" in (s.get("candidate_reason_codes") or [])
    )
    ocr = sum(
        1
        for s in selections
        if "OCR_CORRUPTION" in (s.get("candidate_reason_codes") or [])
    )
    candidates = [s for s in selections if s.get("outcome") == OUTCOME_CANDIDATE]
    # manifests may update outcome after packaging
    final_candidates = [m for m in manifests if m.get("outcome") == OUTCOME_CANDIDATE]
    deferred = [m for m in manifests if m.get("outcome") == OUTCOME_DEFERRED]
    # also count deferred from selection that weren't packaged as candidates
    deferred_sel = [s for s in selections if s.get("outcome") == OUTCOME_DEFERRED]
    excluded = [s for s in selections if s.get("outcome") == OUTCOME_EXCLUDED]

    pri = Counter(m.get("candidate_priority") for m in final_candidates)
    reason_counter: Counter = Counter()
    for m in manifests:
        for r in m.get("candidate_reason_codes") or []:
            reason_counter[r] += 1
    # also count excluded/deferred reasons from selections
    for s in selections:
        if s.get("outcome") != OUTCOME_CANDIDATE:
            for r in s.get("candidate_reason_codes") or []:
                reason_counter[r] += 0  # don't double-count; use dedicated tallies below

    reason_all: Counter = Counter()
    for s in selections:
        for r in s.get("candidate_reason_codes") or []:
            reason_all[r] += 1

    qa_pass = sum(1 for m in final_candidates if m.get("crop_qa_status") == "PASS")
    qa_partial = sum(1 for m in final_candidates if m.get("crop_qa_status") == "PARTIAL")
    qa_fail = sum(1 for m in final_candidates if m.get("crop_qa_status") == "FAIL")
    n_cand = len(final_candidates)

    def pct(n: int, d: int) -> float:
        return round(100.0 * n / d, 2) if d else 0.0

    extreme = sum(
        1
        for m in manifests
        if "NO_EXTREME_EXPANSION" in ((m.get("crop_qa") or {}).get("hard_fails") or [])
        or any(
            str(f).startswith("EXTREME_CROP")
            for f in ((m.get("crop_qa") or {}).get("flags") or [])
        )
    )
    missing_beam = sum(
        1
        for m in manifests
        if ((m.get("crop_qa") or {}).get("gates") or {}).get("TARGET_BEAM_PRESENT")
        == "FAIL"
    )
    missing_ann = sum(
        1
        for m in manifests
        if ((m.get("crop_qa") or {}).get("gates") or {}).get("TARGET_ANNOTATION_PRESENT")
        == "FAIL"
    )
    rejected_included = sum(
        1
        for m in manifests
        if ((m.get("crop_qa") or {}).get("gates") or {}).get("NO_REJECTED_PHYSICAL_BAR")
        == "FAIL"
    )
    with_local = sum(1 for m in manifests if m.get("crop_local_path"))
    with_ctx = sum(1 for m in manifests if m.get("crop_beam_context_path"))
    rejected_ok = sum(
        1
        for m in manifests
        if ((m.get("crop_qa") or {}).get("gates") or {}).get("NO_REJECTED_PHYSICAL_BAR")
        == "PASS"
    )

    return {
        "TOTAL_ELIGIBLE_INTENTS": eligible_intent_count,
        "UNRESOLVED_COUNT": unresolved,
        "AMBIGUOUS_COUNT": ambiguous,
        "OCR_CORRUPTED_COUNT": ocr,
        "VISION_CANDIDATE_COUNT": n_cand,
        "DEFERRED_COUNT": len(deferred) + len(
            [s for s in deferred_sel if s.get("candidate_id") not in {m.get("candidate_id") for m in deferred}]
        ),
        "EXCLUDED_COUNT": len(excluded),
        "P0_COUNT": pri.get(P0, 0),
        "P1_COUNT": pri.get(P1, 0),
        "P2_COUNT": pri.get(P2, 0),
        "P3_COUNT": pri.get(P3, 0),
        "VISION_CANDIDATE_RATE": pct(n_cand, eligible_intent_count),
        "CROP_QA_PASS_RATE": pct(qa_pass, n_cand),
        "CROP_QA_PARTIAL_RATE": pct(qa_partial, n_cand),
        "CROP_QA_FAIL_RATE": pct(qa_fail, n_cand),
        "REJECTED_EVIDENCE_EXCLUSION_RATE": pct(rejected_ok, max(len(manifests), 1)),
        "EXTREME_CROP_COUNT": extreme,
        "MISSING_TARGET_BEAM_COUNT": missing_beam,
        "MISSING_TARGET_ANNOTATION_COUNT": missing_ann,
        "REJECTED_EVIDENCE_INCLUDED_COUNT": rejected_included,
        "CANDIDATES_WITH_LOCAL_CROP": with_local,
        "CANDIDATES_WITH_BEAM_CONTEXT_CROP": with_ctx,
        "reason_code_counts": dict(reason_all),
        "selection_outcome_counts": {
            OUTCOME_CANDIDATE: len(candidates),
            OUTCOME_DEFERRED: len(deferred_sel),
            OUTCOME_EXCLUDED: len(excluded),
            "VISION_CANDIDATE_AFTER_PACKAGING": n_cand,
        },
    }
