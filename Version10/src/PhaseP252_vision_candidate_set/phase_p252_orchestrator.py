"""
P2.5.2 orchestrator — Vision Candidate Set + Visual Evidence Package.

Consumes P2.5.1 QuantityIntent + P2.5.0 evidence packages.
No Claude. No engineering mutations.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PhaseP24_fourth_set_bar_failure_audit.artefacts import (  # noqa: E402
    load_fourth_set_bundle,
)
from PhaseP252_vision_candidate_set.config import (  # noqa: E402
    CLAUDE,
    ENGINEERING_CHANGES,
    GOLDEN_DEV_NOTE,
    GOLDEN_OCR_SAMPLE,
    GOLDEN_SFR_NOTE,
    MODE,
    MODEL_VERSION,
    OUTCOME_CANDIDATE,
    OUTCOME_DEFERRED,
    OUTCOME_EXCLUDED,
    OUTPUT_DIRNAME,
    P250_OUTPUT,
    P251_OUTPUT,
    PHASE_ID,
    PHASE_NAME,
    REASON_DEFER_ENGINEERING_RULE,
    REASON_OCR_CORRUPTION,
    REASON_SEMANTIC_CONTEXT_REQUIRED,
    SCOPE,
)
from PhaseP252_vision_candidate_set.metrics import compute_metrics  # noqa: E402
from PhaseP252_vision_candidate_set.packager import package_candidate  # noqa: E402
from PhaseP252_vision_candidate_set.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP252_vision_candidate_set.report_builder import write_reports  # noqa: E402
from PhaseP252_vision_candidate_set.selector import select_candidates  # noqa: E402
from PhaseP252_vision_candidate_set.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_intents(v10: Path) -> List[Dict[str, Any]]:
    path = v10 / "data" / "output" / P251_OUTPUT / "quantity_intent_matrix.json"
    if not path.exists():
        raise FileNotFoundError(f"P2.5.1 output not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprint(manifests: List[Dict[str, Any]], selections: List[Dict[str, Any]]) -> str:
    payload = {
        "selections": [
            {
                "candidate_id": s.get("candidate_id"),
                "outcome": s.get("outcome"),
                "priority": s.get("candidate_priority"),
                "reasons": s.get("candidate_reason_codes"),
                "raw_text": s.get("raw_text"),
            }
            for s in selections
        ],
        "manifests": [
            {
                "candidate_id": m.get("candidate_id"),
                "outcome": m.get("outcome"),
                "priority": m.get("candidate_priority"),
                "reasons": m.get("candidate_reason_codes"),
                "crop_bounds": m.get("crop_bounds"),
                "crop_qa_status": m.get("crop_qa_status"),
                "vision_status": m.get("future_vision_status"),
                "raw_text": m.get("raw_text"),
            }
            for m in manifests
        ],
    }
    return _stable_hash(payload)


def _golden(selections: List[Dict[str, Any]], manifests: List[Dict[str, Any]]) -> Dict[str, Any]:
    # B97A 4-Y25 explicit — should be EXCLUDED
    b97 = next(
        (
            s
            for s in selections
            if s.get("beam_id") == "B97A" and s.get("annotation_id") == "ANN-d7128f62"
        ),
        None,
    )
    b97_ok = bool(
        b97
        and b97.get("outcome") == OUTCOME_EXCLUDED
        and (b97.get("raw_text") or "").replace(" ", "") == "4-Y25"
    )

    # OCR stirrup
    ocr = next(
        (s for s in selections if (s.get("raw_text") or "") == GOLDEN_OCR_SAMPLE),
        None,
    )
    ocr_m = next(
        (m for m in manifests if (m.get("raw_text") or "") == GOLDEN_OCR_SAMPLE),
        None,
    )
    ocr_ok = bool(
        ocr
        and ocr.get("outcome") == OUTCOME_CANDIDATE
        and REASON_OCR_CORRUPTION in (ocr.get("candidate_reason_codes") or [])
        and ocr.get("raw_text") == GOLDEN_OCR_SAMPLE
    )

    # Development note
    dev = next((s for s in selections if (s.get("raw_text") or "") == GOLDEN_DEV_NOTE), None)
    if not dev:
        dev = next(
            (
                s
                for s in selections
                if (s.get("raw_text") or "").startswith("Ld")
                and REASON_DEFER_ENGINEERING_RULE in (s.get("candidate_reason_codes") or [])
            ),
            None,
        )
    dev_ok = bool(dev and dev.get("outcome") == OUTCOME_DEFERRED)

    # SFR — semantic candidate, or deferred if visual evidence unusable; never a quantity parse
    sfr = next(
        (s for s in selections if (s.get("raw_text") or "") == GOLDEN_SFR_NOTE),
        None,
    )
    sfr_ok = bool(
        sfr
        and REASON_SEMANTIC_CONTEXT_REQUIRED in (sfr.get("candidate_reason_codes") or [])
        and sfr.get("outcome") in (OUTCOME_CANDIDATE, OUTCOME_DEFERRED)
        and "quantity" not in str(sfr.get("candidate_reason_text") or "").lower()[:20]
    )

    # Extreme crop regression on any packaged B97A/B98A
    extreme = False
    for m in manifests:
        if m.get("beam_id") in ("B97A", "B98A"):
            h = (m.get("crop_dimensions_mm") or {}).get("h_mm") or 0
            if float(h) >= 40000:
                extreme = True
            if ((m.get("crop_qa") or {}).get("gates") or {}).get("NO_REJECTED_PHYSICAL_BAR") == "FAIL":
                extreme = True

    return {
        "b97a": {
            "pass": b97_ok and not extreme,
            "candidate_status": (b97 or {}).get("outcome"),
            "reason": (b97 or {}).get("candidate_reason_codes"),
            "selection": b97,
            "extreme_expansion": extreme,
        },
        "ocr_stirrup": {
            "pass": ocr_ok,
            "candidate_status": (ocr or {}).get("outcome"),
            "raw_text_preserved": (ocr or {}).get("raw_text") == GOLDEN_OCR_SAMPLE,
            "reason": (ocr or {}).get("candidate_reason_codes"),
            "crop_qa": (ocr_m or {}).get("crop_qa_status"),
            "manifest": ocr_m,
        },
        "development_note": {
            "pass": dev_ok,
            "classification": (dev or {}).get("outcome"),
            "reasons": (dev or {}).get("candidate_reason_codes"),
            "quantity_interpretation_attempted": False,
            "selection": dev,
        },
        "sfr_note": {
            "pass": sfr_ok,
            "classification": (sfr or {}).get("outcome"),
            "reasons": (sfr or {}).get("candidate_reason_codes"),
            "quantity_interpretation_attempted": False,
            "selection": sfr,
        },
    }


def run_phase_p252(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    candidates_root = out_root / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)
    p250_beams = v10 / "data" / "output" / P250_OUTPUT / "beams"

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {MODE}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES} CLAUDE: {CLAUDE}")
    _log(f"  output: {out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "diagnostics" / "unit_tests.json", unit)
        _log(f"  Unit tests: {unit['passed']}/{unit['total']}")
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            _log(f"  FAIL: {failed[:5]}")
            return {"success": False, "unit_tests": unit, "output_root": str(out_root)}

    bundle = load_fourth_set_bundle(v10)
    fp_paths = fingerprint_paths(v10, bundle.paths)
    fp_before = capture_fingerprints(fp_paths)

    intents = _load_intents(v10)
    _log(f"  P2.5.1 intents loaded: {len(intents)}")
    selections = select_candidates(intents)
    _log(
        f"  Selection: candidates="
        f"{sum(1 for s in selections if s.get('outcome')==OUTCOME_CANDIDATE)} "
        f"deferred={sum(1 for s in selections if s.get('outcome')==OUTCOME_DEFERRED)} "
        f"excluded={sum(1 for s in selections if s.get('outcome')==OUTCOME_EXCLUDED)}"
    )

    # Package Vision candidates + deferred SFR/dev for review index completeness?
    # Spec: package every selected candidate. Deferred can still get metadata-only package.
    to_package = [
        s
        for s in selections
        if s.get("outcome") in (OUTCOME_CANDIDATE, OUTCOME_DEFERRED)
    ]
    manifests: List[Dict[str, Any]] = []
    for sel in to_package:
        man = package_candidate(
            selection=sel,
            p250_beams_root=p250_beams,
            candidates_root=candidates_root,
        )
        manifests.append(man)
        # sync outcome back if packager deferred due to missing visual
        for s in selections:
            if s.get("candidate_id") == man.get("candidate_id"):
                s["outcome"] = man.get("outcome")
                s["candidate_reason_codes"] = man.get("candidate_reason_codes")
                s["candidate_priority"] = man.get("candidate_priority")
                break

    manifests.sort(key=lambda m: (m.get("candidate_id") or ""))
    hash1 = _fingerprint(manifests, selections)

    # Determinism pass 2
    selections2 = select_candidates(intents)
    manifests2: List[Dict[str, Any]] = []
    # clear and rebuild candidate dirs deterministically
    for sel in [
        s
        for s in selections2
        if s.get("outcome") in (OUTCOME_CANDIDATE, OUTCOME_DEFERRED)
    ]:
        man = package_candidate(
            selection=sel,
            p250_beams_root=p250_beams,
            candidates_root=candidates_root,
        )
        manifests2.append(man)
        for s in selections2:
            if s.get("candidate_id") == man.get("candidate_id"):
                s["outcome"] = man.get("outcome")
                s["candidate_reason_codes"] = man.get("candidate_reason_codes")
                s["candidate_priority"] = man.get("candidate_priority")
                break
    manifests2.sort(key=lambda m: (m.get("candidate_id") or ""))
    hash2 = _fingerprint(manifests2, selections2)
    determinism = {
        "determinism_status": "PASS" if hash1 == hash2 else "FAIL",
        "hash1": hash1,
        "hash2": hash2,
    }
    _log(f"  Determinism: {determinism['determinism_status']}")

    # Use pass-2 as final artefacts
    selections = selections2
    manifests = manifests2

    metrics = compute_metrics(
        selections=selections,
        manifests=manifests,
        eligible_intent_count=len(intents),
    )
    golden = _golden(selections, manifests)
    _log(
        f"  Golden B97A={golden['b97a']['pass']} OCR={golden['ocr_stirrup']['pass']} "
        f"Ld={golden['development_note']['pass']} SFR={golden['sfr_note']['pass']}"
    )

    fp_after = capture_fingerprints(fp_paths)
    regression = compare_fingerprints(fp_before, fp_after)
    soft = [c for c in (regression.get("changed") or []) if str(c).startswith("p252")]
    hard = [c for c in (regression.get("changed") or []) if c not in soft]
    regression = {
        **regression,
        "changed": hard,
        "soft_changed": soft,
        "unchanged": len(hard) == 0,
    }

    extreme_on_active = sum(
        1
        for m in manifests
        if m.get("outcome") == OUTCOME_CANDIDATE
        and (
            "NO_EXTREME_EXPANSION" in ((m.get("crop_qa") or {}).get("hard_fails") or [])
            or any(
                str(f).startswith("EXTREME_CROP")
                for f in ((m.get("crop_qa") or {}).get("flags") or [])
            )
        )
    )
    rejected_included = int(metrics.get("REJECTED_EVIDENCE_INCLUDED_COUNT") or 0)
    acceptance = {
        "pass": bool(
            unit.get("success")
            and determinism.get("determinism_status") == "PASS"
            and regression.get("unchanged")
            and golden["b97a"]["pass"]
            and golden["ocr_stirrup"]["pass"]
            and golden["development_note"]["pass"]
            and golden["sfr_note"]["pass"]
            and extreme_on_active == 0
            and rejected_included == 0
            and int(metrics.get("VISION_CANDIDATE_COUNT") or 0) > 0
            and all(m.get("future_vision_status") == "PENDING" for m in manifests)
        ),
        "extreme_count_active_candidates": extreme_on_active,
        "extreme_count_all_packaged": int(metrics.get("EXTREME_CROP_COUNT") or 0),
        "rejected_included": rejected_included,
    }
    decision = "READY_FOR_P2.5.3" if acceptance["pass"] else "BLOCKED"

    meta = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "mode": MODE,
        "engineering_changes": ENGINEERING_CHANGES,
        "claude": CLAUDE,
        "claude_calls": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_reports(
        out_root=out_root,
        meta=meta,
        selections=selections,
        manifests=manifests,
        metrics=metrics,
        golden=golden,
        regression=regression,
        determinism=determinism,
        unit_tests=unit,
        decision=decision,
    )
    _dump(out_root / "diagnostics" / "acceptance.json", acceptance)
    _dump(
        out_root / "RunSummary.json",
        {
            "meta": meta,
            "decision": decision,
            "metrics": metrics,
            "golden": golden,
            "determinism": determinism,
            "regression": regression,
            "acceptance": acceptance,
            "claude_calls": 0,
        },
    )
    _log(f"  vision_candidates={metrics.get('VISION_CANDIDATE_COUNT')} decision={decision}")
    return {
        "success": bool(acceptance["pass"]),
        "decision": decision,
        "meta": meta,
        "metrics": metrics,
        "golden": golden,
        "determinism": determinism,
        "regression": regression,
        "unit_tests": unit,
        "acceptance": acceptance,
        "output_root": str(out_root),
        "claude_calls": 0,
    }
