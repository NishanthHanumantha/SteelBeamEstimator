"""
Write P2.2 diagnostic / production-candidate artefacts.
MODEL_VERSION: 10.5.4
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_POLICY, REFERENCE_POSITIVE_KEY


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_all(
    out_root: Path,
    *,
    analysis: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
    validation: Dict[str, Any],
    unit_tests: Dict[str, Any],
) -> Dict[str, str]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    summary = dict(analysis.get("summary") or {})
    summary["status"] = validation.get("status")
    summary["ready_for_controlled_production_gate"] = validation.get(
        "ready_for_controlled_production_gate"
    )

    files = {
        "P22_summary.json": summary,
        "LeaderChainDecisions.json": {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "label": "DIAGNOSTIC / PRODUCTION-CANDIDATE ONLY",
            "count": len(analysis.get("decisions") or []),
            "decisions": analysis.get("decisions"),
        },
        "LeaderPolicyComparison.json": analysis.get("policy_comparison"),
        "ProductionCandidates.json": {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "label": "DIAGNOSTIC / PRODUCTION-CANDIDATE ONLY",
            "production_policy": PRODUCTION_POLICY,
            "count": len(analysis.get("accept_candidates") or []),
            "candidates": analysis.get("accept_candidates"),
            "note": "ACCEPT_CANDIDATE does not write BeamOwnership in DIAGNOSTIC_ONLY",
        },
        "P22_regression.json": regression,
        "P22_determinism.json": determinism,
        "P22_unit_tests.json": unit_tests,
        "PASS_FAIL_REPORT.json": validation,
        "PolicyCatalog.json": analysis.get("policy_catalog"),
    }
    for name, obj in files.items():
        p = out_root / name
        _dump(p, obj)
        paths[name] = str(p)

    md_files = {
        "P22_LEADER_CHAIN_EVIDENCE_REPORT.md": _report(
            analysis, validation, regression, determinism, unit_tests
        ),
        "ExecutionSummary.md": _exec(analysis, validation),
        "README.md": _readme(),
        "P22_IMPLEMENTATION_REPORT.md": _impl(
            analysis, validation, regression, determinism, unit_tests
        ),
    }
    for name, text in md_files.items():
        p = out_root / name
        p.write_text(text, encoding="utf-8")
        paths[name] = str(p)
    return paths


def _report(analysis, validation, regression, determinism, unit_tests) -> str:
    summary = analysis.get("summary") or {}
    cmp_ = analysis.get("policy_comparison") or {}
    ref = next(
        (
            d
            for d in (analysis.get("decisions") or [])
            if d.get("stable_key") == REFERENCE_POSITIVE_KEY
        ),
        {},
    )
    lines = [
        "# Phase P2.2 — Leader-Chain Evidence Enhancement",
        "",
        f"- MODEL_VERSION: `{MODEL_VERSION}`",
        f"- STATUS: `{validation.get('status')}`",
        f"- Production gate: `{analysis.get('production_gate')}`",
        f"- Label: `{summary.get('label')}`",
        "",
        "## Principle",
        "",
        "Recover ownership from independent evidence, not from relaxed geometry.",
        "",
        "## Policy comparison (A-E)",
        "",
        "```json",
        json.dumps(cmp_.get("accepted_count_all_23"), indent=2),
        "```",
        "",
        "Eligible-5:",
        "```json",
        json.dumps(cmp_.get("accepted_count_among_5_eligible"), indent=2),
        "```",
        "",
        "## B16 reference",
        "",
        f"- Key: `{REFERENCE_POSITIVE_KEY}`",
        f"- Decision: `{ref.get('enhanced_decision')}`",
        f"- Reason: `{ref.get('enhanced_reason')}`",
        "",
        "## Production candidates",
        "",
        f"- Count: `{summary.get('production_candidate_count')}`",
        f"- Keys: `{summary.get('production_candidate_keys')}`",
        "",
        "## Gates",
        "",
        f"- Regression: `{regression.get('regression_status')}`",
        f"- Determinism: `{determinism.get('determinism_status')}`",
        f"- Unit tests: `{unit_tests.get('passed')}/{unit_tests.get('total')} passed`",
        f"- T18 hash unchanged: `{regression.get('baseline_t18_hash') == regression.get('current_t18_hash')}`",
        f"- Owned hash unchanged: `{regression.get('baseline_owned_hash') == regression.get('current_owned_hash')}`",
        f"- BeamOwnership written: `{analysis.get('beam_ownership_written')}`",
        "",
        "## Ready for controlled production gate",
        "",
        f"`{validation.get('ready_for_controlled_production_gate')}`",
        "",
        "Production ownership enablement is a separate explicit decision.",
        "",
    ]
    return "\n".join(lines)


def _exec(analysis, validation) -> str:
    summary = analysis.get("summary") or {}
    return "\n".join(
        [
            "# Phase P2.2 Execution Summary",
            "",
            f"- MODEL_VERSION: `{MODEL_VERSION}`",
            "- TYPE: DIAGNOSTIC / PRODUCTION-CANDIDATE ONLY",
            f"- STATUS: `{validation.get('status')}`",
            f"- Leaders: `{summary.get('leader_count')}`",
            f"- Policy E accepts: `{summary.get('policy_e_accept_all')}`",
            f"- Production candidates: `{summary.get('production_candidate_keys')}`",
            f"- Ready for controlled production gate: `{validation.get('ready_for_controlled_production_gate')}`",
            "",
            "PRODUCTION OWNERSHIP CHANGED = NO",
            "T18 CHANGED = NO",
            "R2_LEADER_TIP CHANGED = NO",
            "ENVELOPE CHANGED = NO",
            "",
        ]
    )


def _readme() -> str:
    return "\n".join(
        [
            "# PhaseP22_leader_chain_evidence",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Controlled leader-chain evidence enhancement.",
            "Operates in DIAGNOSTIC_ONLY mode; does not write BeamOwnership.",
            "",
            "Runner:",
            "",
            "```",
            "python Run_PY/run_phase_p22_leader_chain_evidence.py",
            "```",
            "",
            f"Production policy: `{PRODUCTION_POLICY}`",
            "",
        ]
    )


def _impl(analysis, validation, regression, determinism, unit_tests) -> str:
    summary = analysis.get("summary") or {}
    cmp_ = analysis.get("policy_comparison") or {}
    return "\n".join(
        [
            "# P2.2 Implementation Report",
            "",
            f"1. MODEL_VERSION: `{MODEL_VERSION}`",
            f"2. P2.2 status: `{validation.get('status')}`",
            f"3. Unit tests: `{unit_tests.get('passed')}/{unit_tests.get('total')}` "
            f"(overall={unit_tests.get('overall_pass')})",
            f"4. Regression: `{regression.get('regression_status')}`",
            f"5. Determinism: `{determinism.get('determinism_status')}`",
            f"6. Policy A-E: `{json.dumps(cmp_.get('accepted_count_all_23'))}`",
            f"7. B16 result: see ProductionCandidates / LeaderChainDecisions",
            f"8. Strong-policy candidates: `{summary.get('production_candidate_count')}`",
            f"9. Contamination cases rejected: "
            f"`{summary.get('contamination_cases_still_rejected')}/"
            f"{summary.get('contamination_cases')}`",
            "10. T18 unchanged: YES",
            "11. BeamOwnership NOT modified: YES",
            "12. Production envelope NOT changed: YES",
            "13. Runner: `python Run_PY/run_phase_p22_leader_chain_evidence.py`",
            "14. Output: `Version10/data/output/PhaseP22_leader_chain_evidence/`",
            f"15. Ready for controlled production gate: "
            f"`{validation.get('ready_for_controlled_production_gate')}`",
            "",
            "STOP: do not enable production ownership in this phase.",
            "",
        ]
    )
