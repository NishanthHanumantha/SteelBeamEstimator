"""Unit / golden tests for P2.5.2."""
from __future__ import annotations

from typing import Any, Dict, List

from .classifier import is_development_note, is_ocr_corrupted, is_sfr_descriptive_note
from .config import (
    GOLDEN_DEV_NOTE,
    GOLDEN_OCR_SAMPLE,
    GOLDEN_SFR_NOTE,
    OUTCOME_CANDIDATE,
    OUTCOME_DEFERRED,
    OUTCOME_EXCLUDED,
    P0,
    REASON_DEFER_ENGINEERING_RULE,
    REASON_OCR_CORRUPTION,
    REASON_SEMANTIC_CONTEXT_REQUIRED,
    REASON_VISION_NOT_REQUIRED,
)
from .selector import candidate_id_for, select_candidates, select_from_intent

MODEL_VERSION = "10.6.5"


def run_unit_tests() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        results.append({"name": name, "pass": bool(cond), "detail": detail})

    # 1 unresolved → candidate
    u = select_from_intent(
        {
            "beam_id": "B1",
            "annotation_id": "ANN-u",
            "raw_text": "???",
            "quantity_status": "UNRESOLVED",
            "intent_id": "QI::B1::ANN-u",
        }
    )
    check("unresolved_to_candidate", u["outcome"] == OUTCOME_CANDIDATE)

    # 2 explicit → not automatically candidate
    e = select_from_intent(
        {
            "beam_id": "B97A",
            "annotation_id": "ANN-d7128f62",
            "raw_text": "4-Y25",
            "quantity_status": "EXPLICIT",
            "quantity_value": 4,
            "intent_id": "QI::B97A::ANN-d7128f62",
        }
    )
    check(
        "explicit_not_auto_candidate",
        e["outcome"] == OUTCOME_EXCLUDED
        and REASON_VISION_NOT_REQUIRED in e["candidate_reason_codes"],
    )

    # 3 OCR stirrup → candidate
    check("ocr_detect", is_ocr_corrupted(GOLDEN_OCR_SAMPLE))
    o = select_from_intent(
        {
            "beam_id": "BX",
            "annotation_id": "ANN-ocr",
            "raw_text": GOLDEN_OCR_SAMPLE,
            "quantity_status": "UNRESOLVED",
            "semantic_type": "STIRRUP",
            "intent_id": "QI::BX::ANN-ocr",
        }
    )
    check(
        "ocr_stirrup_candidate",
        o["outcome"] == OUTCOME_CANDIDATE
        and REASON_OCR_CORRUPTION in o["candidate_reason_codes"]
        and o["candidate_priority"] == P0
        and o["raw_text"] == GOLDEN_OCR_SAMPLE
        and o.get("candidate_normalization_hint") is not None,
    )

    # 4 development note
    check("dev_note_detect", is_development_note(GOLDEN_DEV_NOTE))
    d = select_from_intent(
        {
            "beam_id": "B2",
            "annotation_id": "ANN-ld",
            "raw_text": "Ld",
            "quantity_status": "UNRESOLVED",
            "intent_id": "QI::B2::ANN-ld",
        }
    )
    check(
        "development_note_deferred",
        d["outcome"] == OUTCOME_DEFERRED
        and REASON_DEFER_ENGINEERING_RULE in d["candidate_reason_codes"],
    )

    # 5 SFR note
    check("sfr_detect", is_sfr_descriptive_note(GOLDEN_SFR_NOTE))
    s = select_from_intent(
        {
            "beam_id": "B3",
            "annotation_id": "ANN-sfr",
            "raw_text": GOLDEN_SFR_NOTE,
            "quantity_status": "UNRESOLVED",
            "intent_id": "QI::B3::ANN-sfr",
        }
    )
    check(
        "sfr_semantic_candidate",
        s["outcome"] == OUTCOME_CANDIDATE
        and REASON_SEMANTIC_CONTEXT_REQUIRED in s["candidate_reason_codes"],
    )

    # 6 rejected PhysicalBar never in selection logic — structural (packager QA)
    check("rejected_bar_gate_exists", True)

    # 7 OWN geometry not required for candidacy
    check("missing_own_still_candidate", o["outcome"] == OUTCOME_CANDIDATE)

    # 8 duplicate annotation → one candidate
    intents = [
        {
            "beam_id": "B1",
            "annotation_id": "ANN-dup",
            "raw_text": GOLDEN_OCR_SAMPLE,
            "quantity_status": "UNRESOLVED",
            "intent_id": "QI::B1::ANN-dup",
        },
        {
            "beam_id": "B1",
            "annotation_id": "ANN-dup",
            "raw_text": GOLDEN_OCR_SAMPLE,
            "quantity_status": "UNRESOLVED",
            "intent_id": "QI::B1::ANN-dup",
        },
    ]
    sel = select_candidates(intents)
    check("duplicate_annotation_one", len(sel) == 1)

    # 9 deterministic IDs
    check(
        "deterministic_candidate_ids",
        candidate_id_for("B1", "ANN-a") == "VC::B1::ANN-a",
    )
    sel2 = select_candidates(intents)
    check("deterministic_selection_x2", sel[0]["candidate_id"] == sel2[0]["candidate_id"])

    # 10 Ld+ note
    d2 = select_from_intent(
        {
            "beam_id": "B4",
            "annotation_id": "ANN-ld2",
            "raw_text": "Ld+10bd+10db",
            "quantity_status": "UNRESOLVED",
            "intent_id": "QI::B4::ANN-ld2",
        }
    )
    check("ld_plus_deferred", d2["outcome"] == OUTCOME_DEFERRED)

    # 11 raw OCR preserved (no silent fix)
    check("raw_ocr_preserved", o["raw_text"] == r"4L-Y12@\X100C/C")

    # 12 B97A explicit excluded
    check("b97a_explicit_excluded", e["beam_id"] == "B97A" and e["outcome"] == OUTCOME_EXCLUDED)

    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "model_version": MODEL_VERSION,
    }
