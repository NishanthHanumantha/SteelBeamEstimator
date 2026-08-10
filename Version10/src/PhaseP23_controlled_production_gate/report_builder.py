"""
Write P2.3 artefacts.
MODEL_VERSION: 10.5.5
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
    baseline_snapshot: Dict[str, Any],
    controlled_ownership: Dict[str, Any],
    migrations: Dict[str, Any],
    propagation: Dict[str, Any],
    controlled_candidates: Dict[str, Any],
    rejected_candidates: Dict[str, Any],
    render_comparison: Dict[str, Any],
    benchmark_baseline: Dict[str, Any],
    benchmark_controlled: Dict[str, Any],
    accuracy: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
    validation: Dict[str, Any],
    unit_tests: Dict[str, Any],
    engineering: Dict[str, Any],
) -> Dict[str, str]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    files = {
        "BaselineSnapshot.json": baseline_snapshot,
        "ControlledOwnership.json": controlled_ownership,
        "OwnershipMigration.json": migrations,
        "RecoveryPropagationTrace.json": propagation,
        "ControlledCandidates.json": controlled_candidates,
        "RejectedRecoveryCandidates.json": rejected_candidates,
        "RenderComparison.json": render_comparison,
        "BenchmarkBaseline.json": benchmark_baseline,
        "BenchmarkControlled.json": benchmark_controlled,
        "AccuracyComparison.json": accuracy,
        "RegressionReport.json": regression,
        "DeterminismReport.json": determinism,
        "ProductionGateQA.json": validation,
        "P23_unit_tests.json": unit_tests,
        "EngineeringImpact.json": engineering,
    }
    for name, obj in files.items():
        p = out_root / name
        _dump(p, obj)
        paths[name] = str(p)

    (out_root / "P23_CONTROLLED_PRODUCTION_REPORT.md").write_text(
        _main_report(validation, accuracy, controlled_candidates, engineering),
        encoding="utf-8",
    )
    (out_root / "EngineeringImpact.md").write_text(
        _eng_md(engineering, accuracy), encoding="utf-8"
    )
    (out_root / "README.md").write_text(_readme(), encoding="utf-8")
    for name in (
        "P23_CONTROLLED_PRODUCTION_REPORT.md",
        "EngineeringImpact.md",
        "README.md",
    ):
        paths[name] = str(out_root / name)
    return paths


def _main_report(validation, accuracy, candidates, engineering) -> str:
    return "\n".join(
        [
            "# Phase P2.3 — Controlled Production Gate + Re-benchmark",
            "",
            f"- MODEL_VERSION: `{MODEL_VERSION}`",
            f"- STATUS: `{validation.get('status')}`",
            f"- Decision class: `{validation.get('decision_class')}`",
            f"- Production policy: `{PRODUCTION_POLICY}`",
            f"- Reference candidate: `{REFERENCE_POSITIVE_KEY}`",
            f"- Accepted under Policy E: `{(candidates or {}).get('accepted_count')}`",
            f"- Ready for broader E validation: `{validation.get('ready_for_broader_e_validation')}`",
            "",
            "## Accuracy delta (overall)",
            "",
            "```json",
            json.dumps(
                (accuracy.get("AccuracyComparison") or {}).get("overall_three_sets"),
                indent=2,
            ),
            "```",
            "",
            "## Bottleneck",
            "",
            f"{accuracy.get('bottleneck') or engineering.get('bottleneck') or 'None'}",
            "",
            "## Causal chain",
            "",
            engineering.get("causal_chain_summary", ""),
            "",
        ]
    )


def _eng_md(engineering, accuracy) -> str:
    return "\n".join(
        [
            "# Engineering Impact — P2.3",
            "",
            f"- Ownership delta leaders: `{engineering.get('delta_leaders')}`",
            f"- Newly owned entities: `{engineering.get('newly_owned_entities')}`",
            f"- Annotation newly owned: `{engineering.get('annotation_newly_owned')}`",
            f"- Bar newly owned: `{engineering.get('bar_newly_owned')}`",
            f"- Render improved: `{engineering.get('render_improved')}`",
            f"- Steel regenerated: `{accuracy.get('steel_regenerated')}`",
            f"- Steel delta (pp): `{(accuracy.get('AccuracyComparison') or {}).get('overall_three_sets', {}).get('Steel Accuracy', {}).get('absolute_pp')}`",
            "",
            "## Where the causal chain breaks (if any)",
            "",
            engineering.get("causal_break") or "No break identified in ownership/render stages.",
            "",
            "## Recommendation",
            "",
            engineering.get("recommendation") or "",
            "",
        ]
    )


def _readme() -> str:
    return "\n".join(
        [
            "# PhaseP23_controlled_production_gate",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Controlled E_STRONG_COMBINED overlay experiment.",
            "Historical T18 BeamOwnership is never mutated.",
            "",
            "```",
            "python Run_PY/run_phase_p23_controlled_production_gate.py",
            "python Run_PY/run_phase_p23_controlled_production_gate.py --mode baseline",
            "python Run_PY/run_phase_p23_controlled_production_gate.py --mode controlled",
            "```",
            "",
        ]
    )
