"""
P2.5.4 orchestrator — Semantic Reinforcement Vision Benchmark & Shadow Resolver.

Claude output is shadow evidence only — no production writes.
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

from PhaseP24_fourth_set_bar_failure_audit.artefacts import load_fourth_set_bundle  # noqa: E402

from PhaseP254_semantic_reinforcement_vision_benchmark.benchmark_builder import (  # noqa: E402
    build_benchmark,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.config import (  # noqa: E402
    ENGINEERING_CHANGES,
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
from PhaseP254_semantic_reinforcement_vision_benchmark.contact_sheet import (  # noqa: E402
    write_contact_sheets,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.metrics import (  # noqa: E402
    compute_metrics,
    decide_recommendation,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.pilot_runner import (  # noqa: E402
    run_one_candidate,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.report_builder import (  # noqa: E402
    write_reports,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _stable_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_phase_p254(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    run_claude: bool = True,
    prior_pipeline_fingerprint: Optional[str] = None,
    evidence_mode: str = PRIMARY_EVIDENCE_MODE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    candidates_root = out_root / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)
    bench_root = out_root / "benchmark"
    bench_root.mkdir(parents=True, exist_ok=True)

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
    fw = firewall_check(v10)

    # Deterministic preparation twice
    bench1 = build_benchmark(v10)
    bench2 = build_benchmark(v10)
    prep_match = bench1["fingerprint"] == bench2["fingerprint"]
    pipeline_fp = bench1["fingerprint"]

    candidates = bench1["candidates"]
    gt_map = bench1["ground_truth"]
    public_manifest = []
    for c in candidates:
        pub = dict(c)
        pub.pop("ground_truth", None)
        public_manifest.append(pub)
    _dump(bench_root / "benchmark_manifest.json", public_manifest)
    _dump(bench_root / "ground_truth_reference.json", gt_map)

    _log(f"  Benchmark size: {len(candidates)}")
    _log(f"  Class distribution: {bench1.get('class_distribution')}")
    _log(f"  Deterministic prep match: {prep_match}")

    results: List[Dict[str, Any]] = []
    if run_claude:
        for c in candidates:
            _log(f"  Claude Vision: {c.get('candidate_id')} ({c.get('raw_text')}) [{c.get('semantic_class')}] ...")
            r = run_one_candidate(
                candidate=c,
                ground_truth=gt_map[c["candidate_id"]],
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
                f"status={st} eval={ev} cmp={(r.get('comparison') or {}).get('class')}"
            )
    else:
        _log("  run_claude=False — deterministic preparation only")

    fp_after = capture_fingerprints(fp_paths)
    reg = compare_fingerprints(fp_before, fp_after)
    metrics = compute_metrics(results) if results else compute_metrics([])
    if not run_claude:
        decision = "PREP_ONLY"
    else:
        decision = decide_recommendation(
            metrics, firewall_ok=bool(fw.get("ok")), regression_ok=bool(reg.get("unchanged"))
        )

    usage = metrics.get("token_usage") or {}
    est_cost = round(
        (float(usage.get("input_tokens") or 0) / 1_000_000.0) * 3.0
        + (float(usage.get("output_tokens") or 0) / 1_000_000.0) * 15.0,
        4,
    )

    det = {
        "pipeline_fingerprint": pipeline_fp,
        "pipeline_determinism_status": (
            "PASS"
            if prep_match
            and (prior_pipeline_fingerprint is None or prior_pipeline_fingerprint == pipeline_fp)
            else "FAIL"
        ),
        "deterministic_preparation_twice": prep_match,
        "claude_variability_test": "NOT_RUN",
        "claude_variability_reason": (
            "Cost control: single LOCAL_PLUS_CONTEXT Claude pass; "
            "deterministic candidate/evidence/prompt fingerprints compared instead."
        ),
        "note": "Candidate/evidence/prompt fingerprints are deterministic; Claude text may vary.",
        "response_fingerprints": [
            (r.get("claude_call") or {}).get("response_fingerprint") for r in results
        ],
    }
    _dump(out_root / "determinism_report.json", det)

    claude_model = next(
        (
            (r.get("claude_call") or {}).get("model")
            for r in results
            if (r.get("claude_call") or {}).get("model")
        ),
        None,
    )
    temperature = next(
        (
            (r.get("claude_call") or {}).get("temperature")
            for r in results
            if (r.get("claude_call") or {}).get("temperature") is not None
        ),
        0,
    )

    api_ok_rate = metrics.get("CLAUDE_SUCCESS_RATE", 0) if results else 0
    hard_fail = (
        not reg.get("unchanged", False)
        or det["pipeline_determinism_status"] == "FAIL"
        or not fw.get("ok")
        or not unit.get("success")
        or (
            run_claude
            and (
                api_ok_rate < 50
                or metrics.get("CLAUDE_CALL_COUNT") != len(candidates)
                or decision == "PILOT_BLOCKED"
            )
        )
    )
    pass_fail = "FAIL" if hard_fail else "PASS"

    failed = [
        r.get("candidate_id")
        for r in results
        if (r.get("evaluation") or {}).get("evaluation")
        in ("INCORRECT", "HALLUCINATION", "INVALID_RESPONSE", "API_ERROR")
        or not (r.get("claude_call") or {}).get("success")
    ]

    if results:
        try:
            write_contact_sheets(
                version10_root=v10, out_root=out_root, candidates=candidates, results=results
            )
        except Exception as exc:  # noqa: BLE001
            _log(f"  Contact sheet skipped: {exc}")

    summary = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "pass_fail": pass_fail,
        "decision": decision,
        "claude_model": claude_model,
        "temperature": temperature,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "evidence_mode": evidence_mode,
        "class_distribution": bench1.get("class_distribution"),
        "tag_distribution": bench1.get("tag_distribution"),
        "metrics": metrics,
        "determinism": det,
        "regression": {
            "unchanged": reg.get("unchanged"),
            "changed_keys": reg.get("changed_keys"),
        },
        "firewall": fw,
        "engineering_changes": ENGINEERING_CHANGES,
        "production_output_changes": "NONE",
        "estimated_api_cost_usd": est_cost,
        "estimated_cost_note": (
            "Approx Claude Sonnet list rates $3/MTok in + $15/MTok out; "
            "actual Anthropic billing may differ"
        ),
        "failed_or_incorrect_candidates": failed,
        "unit_tests": unit,
        "benchmark_count": len(candidates),
    }
    write_reports(out_root=out_root, summary=summary, results=results)
    _dump(out_root / "diagnostics" / "determinism.json", det)

    _log(f"  PASS/FAIL: {pass_fail}")
    _log(f"  Decision: {decision}")
    return {
        "success": pass_fail == "PASS",
        "pass_fail": pass_fail,
        "decision": decision,
        "output_root": str(out_root),
        "metrics": metrics,
        "determinism": det,
        "regression": summary["regression"],
        "firewall": fw,
        "claude_model": claude_model,
        "pipeline_fingerprint": pipeline_fp,
        "failed_or_incorrect_candidates": failed,
        "results": results,
        "meta": {"model_version": MODEL_VERSION, "phase_id": PHASE_ID},
        "unit_tests": unit,
        "benchmark_count": len(candidates),
        "class_distribution": bench1.get("class_distribution"),
    }


__all__ = ["run_phase_p254"]
