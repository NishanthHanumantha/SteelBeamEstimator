"""
Write P2.1 diagnostic artefacts.
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .config import MODEL_VERSION, PHASE_ID


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_all(
    out_root: Path,
    *,
    analysis: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
    validation: Dict[str, Any],
) -> Dict[str, str]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    root = analysis.get("root_cause") or {}

    files = {
        "LeaderTipAnalysis.json": {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "count": len(analysis.get("traces") or []),
            "leaders": analysis.get("traces"),
        },
        "LeaderEvidenceScorecard.json": {
            "phase_id": PHASE_ID,
            "count": len(analysis.get("scorecards") or []),
            "scorecards": analysis.get("scorecards"),
        },
        "LeaderCounterfactualResults.json": {
            "phase_id": PHASE_ID,
            "label": "COUNTERFACTUAL — NOT PRODUCTION OWNERSHIP",
            "focus_candidates": analysis.get("focus_candidates"),
            "all_leaders": analysis.get("policy_rows"),
        },
        "CounterfactualOwnership.json": {
            "phase_id": PHASE_ID,
            "label": "COUNTERFACTUAL — NOT PRODUCTION OWNERSHIP",
            "count": len(analysis.get("counterfactual_ownership") or []),
            "rows": analysis.get("counterfactual_ownership"),
        },
        "R2LeaderDecisionTrace.json": {
            "phase_id": PHASE_ID,
            "count": len(analysis.get("decision_traces") or []),
            "traces": analysis.get("decision_traces"),
        },
        "LeaderPolicyComparison.json": analysis.get("policy_comparison"),
        "ContaminationAnalysis.json": analysis.get("contamination"),
        "CandidateImpact.json": analysis.get("impact"),
        "RootCauseSummary.json": root,
        "ExcludedLeaderClassification.json": analysis.get("excluded"),
        "P21_regression.json": regression,
        "P21_determinism.json": determinism,
        "PASS_FAIL_REPORT.json": validation,
    }
    for name, obj in files.items():
        p = out_root / name
        _dump(p, obj)
        paths[name] = str(p)

    (out_root / "P21_LEADER_TIP_CHAIN_QA_REPORT.md").write_text(
        _qa_report(analysis, validation, root), encoding="utf-8"
    )
    (out_root / "P21_ARCHITECTURE_SUMMARY.md").write_text(_arch(), encoding="utf-8")
    (out_root / "P21_ENGINEERING_RECOMMENDATIONS.md").write_text(
        _recs(root, analysis), encoding="utf-8"
    )
    (out_root / "P21_DECISION_MATRIX.md").write_text(
        _matrix(analysis.get("focus_candidates") or []), encoding="utf-8"
    )
    (out_root / "ExecutionSummary.md").write_text(
        _exec(analysis, validation, root), encoding="utf-8"
    )
    (out_root / "README.md").write_text(_readme(), encoding="utf-8")
    for name in (
        "P21_LEADER_TIP_CHAIN_QA_REPORT.md",
        "P21_ARCHITECTURE_SUMMARY.md",
        "P21_ENGINEERING_RECOMMENDATIONS.md",
        "P21_DECISION_MATRIX.md",
        "ExecutionSummary.md",
        "README.md",
    ):
        paths[name] = str(out_root / name)
    return paths


def _qa_report(analysis, validation, root) -> str:
    ans = root.get("answers") or {}
    return "\n".join(
        [
            f"# P2.1 Leader Tip / Chain Acceptance QA Report",
            "",
            f"- MODEL_VERSION: `{MODEL_VERSION}`",
            f"- TYPE: DIAGNOSTIC / COUNTERFACTUAL ONLY",
            f"- STATUS: `{validation.get('status')}`",
            f"- PRODUCTION OWNERSHIP CHANGED: NO",
            f"- T18 CHANGED: NO",
            "",
            "## Population",
            f"- Leaders analysed: `{analysis.get('leader_count')}`",
            f"- Recovery-eligible (QA.4.3): `{analysis.get('eligible_count')}`",
            "",
            "## Root answers",
            f"1. R2 too strict? `{ans.get('1_is_r2_leader_tip_too_strict')}`",
            f"2. Problem is tip rule? `{ans.get('2_is_problem_the_leader_tip_rule')}`",
            f"3. Problem is production envelope? `{ans.get('3_is_problem_the_production_envelope')}`",
            f"4. Chain evidence safely recovers any of 5? `{ans.get('4_can_chain_evidence_safely_recover_any_of_5')}`",
            f"5. Best policy: `{ans.get('5_best_policy_without_contamination')}`",
            f"6. Leaders per policy: `{ans.get('6_additional_leaders_each_policy')}`",
            f"7. Annotations reachable: `{ans.get('7_additional_annotations_reachable')}`",
            "",
            f"Recommended next phase: `{(root.get('recommended_next_phase') or {}).get('option')}`",
            "",
            f"Failed gates: `{validation.get('failed_gates')}`",
            "",
        ]
    )


def _arch() -> str:
    return "\n".join(
        [
            "# P2.1 Architecture Summary",
            "",
            "```",
            "QA.4.3 dropped leaders (23)",
            "  ↓",
            "Graph + T18 envelope (read-only)",
            "  ↓",
            "tip_in_envelope / evaluate_leader replay",
            "  ↓",
            "Evidence scorecard A–J",
            "  ↓",
            "Counterfactual policies A–E (diagnostic)",
            "  ↓",
            "Contamination SAFE / AMBIGUOUS / UNSAFE",
            "  ↓",
            "Root-cause + recommendation",
            "  ↓",
            "Regression / determinism gate",
            "```",
            "",
            "No production artefacts are written.",
            "T18 ownership rules are not modified.",
            "",
        ]
    )


def _recs(root, analysis) -> str:
    ans = root.get("answers") or {}
    return "\n".join(
        [
            "# P2.1 Engineering Recommendations",
            "",
            "DIAGNOSTIC ONLY — do not implement production rule changes in this phase.",
            "",
            f"Recommended option: `{(root.get('recommended_next_phase') or {}).get('option')}`",
            "",
            (root.get("recommended_next_phase") or {}).get("rationale") or "",
            "",
            "## Incorporate later (if production phase approved)",
            *[f"- {x}" for x in (ans.get("8_evidence_to_incorporate_in_future_rule") or [])],
            "",
            "## Do NOT use alone",
            *[f"- {x}" for x in (ans.get("9_evidence_not_to_use_alone") or [])],
            "",
            "## Case taxonomy (5 eligible)",
            json.dumps(root.get("case_taxonomy_for_5_candidates") or [], indent=2),
            "",
        ]
    )


def _matrix(focus: List[Dict[str, Any]]) -> str:
    lines = [
        "# P2.1 Decision Matrix — 5 Recovery Candidates",
        "",
        "| Beam | Leader | Dist mm | A | B | C | D | E | Contam | Case |",
        "|------|--------|---------|---|---|---|---|---|--------|------|",
    ]
    for f in focus:
        lines.append(
            f"| {f.get('beam_id')} | {f.get('leader_id')} | {f.get('distance_mm')} | "
            f"{f.get('policy_A')} | {f.get('policy_B')} | {f.get('policy_C')} | "
            f"{f.get('policy_D')} | {f.get('policy_E')} | {f.get('contamination_risk')} | "
            f"{(f.get('current_rejection_reason') or '')[:28]} |"
        )
    lines += ["", "A=CURRENT T18, B–E=counterfactual diagnostic policies only.", ""]
    return "\n".join(lines)


def _exec(analysis, validation, root) -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} Execution Summary",
            "",
            f"- MODEL_VERSION: `{MODEL_VERSION}`",
            f"- TYPE: DIAGNOSTIC / COUNTERFACTUAL ONLY",
            f"- STATUS: `{validation.get('status')}`",
            f"- Leaders: `{analysis.get('leader_count')}`",
            f"- Eligible focus: `{analysis.get('eligible_count')}`",
            f"- Recommended next: `{(root.get('recommended_next_phase') or {}).get('option')}`",
            "",
            "PRODUCTION OWNERSHIP CHANGED = NO",
            "T18 CHANGED = NO",
            "QA.4 BASELINES CHANGED = NO",
            "",
            "No production fix was implemented.",
            "",
        ]
    )


def _readme() -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} — Leader Tip / Chain Acceptance Analysis",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Diagnostic counterfactual analysis of R2_LEADER_TIP vs leader-chain evidence.",
            "",
            "`python Run_PY/run_phase_p21_leader_tip_chain_analysis.py`",
            "",
        ]
    )
