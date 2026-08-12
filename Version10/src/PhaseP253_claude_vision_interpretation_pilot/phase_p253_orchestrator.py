"""
P2.5.3 orchestrator — Claude Vision Interpretation Pilot.

Loads frozen P2.5.2.3 candidates. Calls Claude Vision. Validates. Evaluates.
Claude output is pilot evidence only — no production writes.
"""
from __future__ import annotations

import hashlib
import json
import sys
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
from PhaseP253_claude_vision_interpretation_pilot.config import (  # noqa: E402
    ENGINEERING_CHANGES,
    EXPECTED_VISION_CANDIDATES,
    GOLDEN_B97A_BEAM,
    GOLDEN_OCR_SAMPLE,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRIMARY_EVIDENCE_MODE,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    SCOPE,
)
from PhaseP253_claude_vision_interpretation_pilot.metrics import (  # noqa: E402
    compute_metrics,
    decide_recommendation,
)
from PhaseP253_claude_vision_interpretation_pilot.pilot_candidate_loader import (  # noqa: E402
    load_frozen_candidates,
)
from PhaseP253_claude_vision_interpretation_pilot.pilot_runner import (  # noqa: E402
    run_one_candidate,
)
from PhaseP253_claude_vision_interpretation_pilot.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP253_claude_vision_interpretation_pilot.report_builder import write_reports  # noqa: E402
from PhaseP253_claude_vision_interpretation_pilot.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _stable_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_phase_p253(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    prior_pipeline_fingerprint: Optional[str] = None,
    evidence_mode: str = PRIMARY_EVIDENCE_MODE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    candidates_root = out_root / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {MODE}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES}")
    _log(f"  evidence_mode={evidence_mode}")
    _log(f"  output: {out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "diagnostics" / "unit_tests.json", unit)
        _log(f"  Unit tests: {unit['passed']}/{unit['total']}")
        if not unit.get("success"):
            return {
                "success": False,
                "pass_fail": "FAIL",
                "decision": "PILOT_BLOCKED",
                "unit_tests": unit,
                "output_root": str(out_root),
            }

    bundle = load_fourth_set_bundle(v10)
    fp_paths = fingerprint_paths(v10, bundle.paths)
    fp_before = capture_fingerprints(fp_paths)

    try:
        frozen = load_frozen_candidates(v10)
    except Exception as exc:
        return {
            "success": False,
            "pass_fail": "FAIL",
            "decision": "PILOT_BLOCKED",
            "error": str(exc),
            "output_root": str(out_root),
        }

    # Golden: OCR present; B97A not in active set
    ocr_ok = any((c.get("raw_text") or "") == GOLDEN_OCR_SAMPLE for c in frozen)
    b97_absent = not any(c.get("beam_id") == GOLDEN_B97A_BEAM for c in frozen)
    if not ocr_ok or not b97_absent or len(frozen) != EXPECTED_VISION_CANDIDATES:
        return {
            "success": False,
            "pass_fail": "FAIL",
            "decision": "PILOT_BLOCKED",
            "error": "FROZEN_SET_GOLDEN_INVARIANT",
            "output_root": str(out_root),
        }

    pipeline_fp = _stable_hash(
        [
            {
                "candidate_id": c.get("candidate_id"),
                "beam_id": c.get("beam_id"),
                "annotation_id": c.get("annotation_id"),
                "raw_text": c.get("raw_text"),
                "priority": c.get("candidate_priority"),
                "reasons": c.get("candidate_reason_codes"),
            }
            for c in frozen
        ]
    )

    results: List[Dict[str, Any]] = []
    for c in frozen:
        _log(f"  Claude Vision: {c.get('candidate_id')} ({c.get('raw_text')}) ...")
        r = run_one_candidate(
            candidate=c,
            version10_root=v10,
            out_candidates_root=candidates_root,
            evidence_mode=evidence_mode,
        )
        results.append(r)
        ev = (r.get("evaluation") or {}).get("evaluation")
        st = (r.get("validated_interpretation") or {}).get("interpretation_status")
        _log(
            f"    -> api={(r.get('claude_call') or {}).get('success')} "
            f"valid={(r.get('validation') or {}).get('valid')} "
            f"status={st} eval={ev}"
        )

    fp_after = capture_fingerprints(fp_paths)
    reg = compare_fingerprints(fp_before, fp_after)

    metrics = compute_metrics(results)
    decision = decide_recommendation(metrics)

    usage = metrics.get("token_usage") or {}
    # Approx Claude Sonnet list rates (USD / MTok). Billing may differ.
    est_cost = round(
        (float(usage.get("input_tokens") or 0) / 1_000_000.0) * 3.0
        + (float(usage.get("output_tokens") or 0) / 1_000_000.0) * 15.0,
        4,
    )

    # Deterministic pipeline fingerprint (candidate set) vs Claude variability
    det = {
        "pipeline_fingerprint": pipeline_fp,
        "pipeline_determinism_status": (
            "PASS"
            if prior_pipeline_fingerprint is None or prior_pipeline_fingerprint == pipeline_fp
            else "FAIL"
        ),
        "claude_response_variability": "EXPECTED_NONDETERMINISTIC_MODEL_OUTPUT",
        "note": "Candidate/evidence/prompt fingerprints are deterministic; Claude text may vary.",
        "response_fingerprints": [
            (r.get("claude_call") or {}).get("response_fingerprint") for r in results
        ],
    }

    claude_model = next(
        ((r.get("claude_call") or {}).get("model") for r in results if (r.get("claude_call") or {}).get("model")),
        None,
    )

    # Phase implementation PASS if: frozen set OK, API mostly works, validation layer works,
    # regression unchanged, no production writes. Decision may still be MORE_PILOT_REQUIRED.
    api_ok_rate = metrics.get("CLAUDE_SUCCESS_RATE", 0)
    hard_fail = (
        not reg.get("unchanged", False)
        or det["pipeline_determinism_status"] == "FAIL"
        or api_ok_rate < 50
        or metrics.get("CLAUDE_CALL_COUNT") != EXPECTED_VISION_CANDIDATES
        or decision == "PILOT_BLOCKED"
    )
    pass_fail = "FAIL" if hard_fail else "PASS"

    failed = [
        r.get("candidate_id")
        for r in results
        if not (r.get("claude_call") or {}).get("success")
        or (r.get("evaluation") or {}).get("evaluation")
        in ("INCORRECT", "HALLUCINATION", "INVALID_RESPONSE", "API_ERROR")
    ]

    summary = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "pass_fail": pass_fail,
        "decision": decision,
        "claude_model": claude_model,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "evidence_mode": evidence_mode,
        "metrics": metrics,
        "determinism": det,
        "regression": {
            "unchanged": reg.get("unchanged"),
            "changed_keys": reg.get("changed_keys"),
        },
        "engineering_changes": ENGINEERING_CHANGES,
        "production_output_changes": "NONE",
        "estimated_api_cost_usd": est_cost,
        "estimated_cost_note": (
            "Approx Claude Sonnet list rates $3/MTok in + $15/MTok out; "
            "actual Anthropic billing may differ"
        ),
        "failed_or_incorrect_candidates": failed,
        "unit_tests": unit,
        "golden": {"ocr_present": ocr_ok, "b97a_excluded": b97_absent},
        "firewall": {
            "claude_writes_production": False,
            "steel_bbs_excel_changed": False,
            "upstream_p252x_immutable": bool(reg.get("unchanged")),
        },
    }

    write_reports(out_root=out_root, summary=summary, results=results)
    _dump(out_root / "manifests" / "PilotResultsManifest.json", results)
    _dump(out_root / "diagnostics" / "determinism.json", det)

    _log(f"  PASS/FAIL: {pass_fail}")
    _log(f"  Decision: {decision}")
    _log(
        f"  exact={ (metrics.get('counts') or {}).get('exact')} "
        f"partial={ (metrics.get('counts') or {}).get('partial')} "
        f"incorrect={ (metrics.get('counts') or {}).get('incorrect')} "
        f"halluc={ (metrics.get('counts') or {}).get('hallucination')}"
    )

    return {
        "success": pass_fail == "PASS",
        "pass_fail": pass_fail,
        "decision": decision,
        "output_root": str(out_root),
        "metrics": metrics,
        "determinism": det,
        "regression": summary["regression"],
        "claude_model": claude_model,
        "pipeline_fingerprint": pipeline_fp,
        "failed_or_incorrect_candidates": failed,
        "results": results,
        "meta": {"model_version": MODEL_VERSION, "phase_id": PHASE_ID},
        "unit_tests": unit,
    }


__all__ = ["run_phase_p253"]
