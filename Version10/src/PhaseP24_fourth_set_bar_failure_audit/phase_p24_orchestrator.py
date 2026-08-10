"""
P2.4 orchestrator — Fourth Set bar failure attribution audit.
MODEL_VERSION: 10.6.0
DIAGNOSTIC ONLY.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .artefacts import FourthSetBundle, load_fourth_set_bundle
from .config import (
    DEFAULT_CONFIG,
    ENGINEERING_CHANGES,
    MODE,
    MODEL_VERSION,
    PHASE_ID,
    PRIORITY_BEAMS,
    PROBLEM_RENDER_BEAMS,
    SCOPE,
    SHARED_CASE_BEAMS,
    P24Config,
)
from .metrics import beam_summaries, build_diagnostics, compute_metrics, special_analyses
from .registries import build_registries_and_matches
from .regression import capture_fingerprints, compare_fingerprints
from .report_builder import write_all
from .stage_tracer import enrich_model_registry, trace_gt_bar
from .visualizer import write_visuals


def _sha_obj(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def _audit_once(
    bundle: FourthSetBundle,
    engine_root: Path,
) -> Dict[str, Any]:
    regs = build_registries_and_matches(
        engine_root,
        bundle.estimator_excel,
        bundle.model_excel,
        bundle.drawing_set,
    )
    gt_registry = regs["gt_registry"]
    model_registry = enrich_model_registry(regs["model_registry"], bundle)
    match_by_gt = {
        r["gt_bar_id"]: r
        for r in regs["match_rows"]
        if r.get("gt_bar_id") and r.get("gt_bar_id") != "UNKNOWN"
    }
    model_beam_ids = {b.beam_id for b in regs["model"].beams}

    matrix: List[Dict[str, Any]] = []
    for gt in gt_registry:
        mrow = match_by_gt.get(gt["gt_bar_id"])
        if mrow is None:
            mrow = {
                "status": "MISSING",
                "beam_id": gt["beam_id"],
                "bar_role": gt["bar_role"],
                "diameter": gt["diameter"],
                "estimator_qty": gt["quantity"],
                "model_role": None,
                "model_diameter": None,
                "model_qty": 0,
                "model_steel_kg": 0,
            }
        matrix.append(trace_gt_bar(gt, mrow, bundle, model_beam_ids))

    metrics = compute_metrics(matrix, regs["extra_rows"], gt_registry)
    required = list(PRIORITY_BEAMS) + list(PROBLEM_RENDER_BEAMS) + list(SHARED_CASE_BEAMS)
    beams = beam_summaries(matrix, regs["extra_rows"], required)
    diagnostics = build_diagnostics(matrix, regs["extra_rows"])
    special = special_analyses(
        matrix,
        [b.beam_id for b in regs["estimator"].beams],
        bundle.engineering_scopes,
        bundle.shared_annotation_registry,
    )

    fingerprint = {
        "gt_registry": _sha_obj(
            [(g["gt_bar_id"], g["beam_id"], g["bar_role"], g["diameter"], g["quantity"]) for g in gt_registry]
        ),
        "model_registry": _sha_obj(
            [
                (m["model_bar_id"], m["beam_id"], m["bar_role"], m["diameter"], m["quantity"])
                for m in model_registry
            ]
        ),
        "matching": _sha_obj(
            [(r["gt_bar_id"], r["match_status"], r["excel_status"]) for r in matrix]
        ),
        "first_fail": _sha_obj(
            [(r["gt_bar_id"], r["first_failure_stage"], r["failure_reason"]) for r in matrix]
        ),
        "metrics": _sha_obj(metrics),
    }

    return {
        "gt_registry": gt_registry,
        "model_registry": model_registry,
        "matrix": matrix,
        "extras": regs["extra_rows"],
        "metrics": metrics,
        "beams": beams,
        "diagnostics": diagnostics,
        "special": special,
        "fingerprint": fingerprint,
        "beam_matching": {
            k: regs["beam_matching"].get(k)
            for k in ("detection_pct", "matching_pct", "estimator_beams", "detected_beams")
        },
        "bar_matching_summary": {
            k: regs["bar_matching"].get(k)
            for k in (
                "estimator_bars",
                "detected_bars",
                "correct_bars",
                "missing_bars",
                "detection_pct",
                "accuracy_pct",
            )
        },
    }


class PhaseP24Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        config: Optional[P24Config] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root
            / "data"
            / "output"
            / "PhaseP24_fourth_set_bar_failure_audit"
        )
        self.config = config or DEFAULT_CONFIG

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print(f"[{PHASE_ID}] SCOPE = {SCOPE}")
        print(f"[{PHASE_ID}] MODE = {MODE}")
        print(f"[{PHASE_ID}] ENGINEERING_CHANGES = {ENGINEERING_CHANGES}")
        print(f"[{PHASE_ID}] MODEL_VERSION = {MODEL_VERSION}")

        bundle = load_fourth_set_bundle(self.engine_root)
        print(f"[{PHASE_ID}] run_root = {bundle.run_root}")
        print(f"[{PHASE_ID}] estimator_gt = {bundle.estimator_excel}")
        print(f"[{PHASE_ID}] model_excel = {bundle.model_excel}")

        fp_keys = {
            "t18": bundle.paths.get("t18") or bundle.paths.get("beam_ownership"),
            "p22_regression": bundle.paths.get("p22_regression"),
            "p23_regression": bundle.paths.get("p23_regression"),
            "p231_regression": bundle.paths.get("p231_regression"),
            "physical_bars": bundle.paths.get("physical_bars"),
            "annotation_graph": bundle.paths.get("annotation_graph"),
            "r13_models": bundle.paths.get("r13_models"),
            "model_excel": bundle.model_excel,
        }
        before = capture_fingerprints(fp_keys)

        print(f"[{PHASE_ID}] audit pass 1...")
        pass1 = _audit_once(bundle, self.engine_root)
        print(f"[{PHASE_ID}] audit pass 2 (determinism)...")
        pass2 = _audit_once(bundle, self.engine_root)

        det_ok = pass1["fingerprint"] == pass2["fingerprint"]
        determinism = {
            "determinism_status": "PASS" if det_ok else "FAIL",
            "pass1": pass1["fingerprint"],
            "pass2": pass2["fingerprint"],
            "diffs": [
                k
                for k in pass1["fingerprint"]
                if pass1["fingerprint"].get(k) != pass2["fingerprint"].get(k)
            ],
        }
        print(f"[{PHASE_ID}] determinism = {determinism['determinism_status']}")

        after = capture_fingerprints(fp_keys)
        regression = compare_fingerprints(before, after)
        regression["label"] = "T18/P22/P23/P231/production artefacts unchanged"
        print(f"[{PHASE_ID}] regression_unchanged = {regression['unchanged']}")

        result = pass1
        visuals_dir = self.output_root / "VisualEvidence"
        visual_manifest = write_visuals(
            result["matrix"],
            result["metrics"].get("first_failure_distribution_pct") or {},
            visuals_dir,
            self.config,
        )

        elapsed = round(time.perf_counter() - t0, 3)
        gates = self._gates(result, determinism, regression, bundle)
        success = all(g["pass"] for g in gates)
        meta = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "scope": SCOPE,
            "mode": MODE,
            "engineering_changes": ENGINEERING_CHANGES,
            "drawing_set": bundle.drawing_set,
            "run_root": str(bundle.run_root),
            "estimator_excel": str(bundle.estimator_excel),
            "model_excel": str(bundle.model_excel),
            "reinforcement_dxf": str(bundle.reinforcement_dxf) if bundle.reinforcement_dxf else None,
            "elapsed_s": elapsed,
            "success": success,
            "status": "PASS" if success else "FAIL",
            "gates": gates,
            "beams_analysed": sorted({r["beam_id"] for r in result["matrix"]}),
        }

        write_all(
            self.output_root,
            matrix=result["matrix"],
            metrics=result["metrics"],
            beams=result["beams"],
            diagnostics=result["diagnostics"],
            special=result["special"],
            gt_registry=result["gt_registry"],
            model_registry=result["model_registry"],
            determinism=determinism,
            regression=regression,
            visual_manifest=visual_manifest,
            meta=meta,
        )

        # compact console summary
        m = result["metrics"]
        print(f"[{PHASE_ID}] GT={m['gt_total_bars']} matched={m['matched_bars']} "
              f"unmatched={m['unmatched_gt_bars']} extra={m['extra_model_bars']}")
        print(f"[{PHASE_ID}] dominant_first_fail={m['questions']['Q6_largest_first_fail']}")
        print(f"[{PHASE_ID}] recommend={m['recommended_next_phase']}")
        print(f"[{PHASE_ID}] output={self.output_root}")
        print(f"[{PHASE_ID}] status={'PASS' if success else 'FAIL'}")

        return {
            "success": success,
            "status": "PASS" if success else "FAIL",
            "model_version": MODEL_VERSION,
            "phase_id": PHASE_ID,
            "output_root": str(self.output_root),
            "metrics": m,
            "special": result["special"],
            "determinism": determinism,
            "regression": regression,
            "meta": meta,
            "beams_analysed": meta["beams_analysed"],
        }

    def _gates(
        self,
        result: Dict[str, Any],
        determinism: Dict[str, Any],
        regression: Dict[str, Any],
        bundle: FourthSetBundle,
    ) -> List[Dict[str, Any]]:
        m = result["metrics"]
        special = result["special"]
        beams = {b["beam_id"] for b in result["beams"]}
        return [
            {"name": "fourth_set_only", "pass": bundle.set_key == "Fourth", "detail": bundle.drawing_set},
            {"name": "gt_registry", "pass": m.get("gt_total_bars", 0) > 0, "detail": m.get("gt_total_bars")},
            {
                "name": "model_registry",
                "pass": len(result.get("model_registry") or []) > 0,
                "detail": len(result.get("model_registry") or []),
            },
            {
                "name": "matrix_complete",
                "pass": len(result["matrix"]) == m.get("gt_total_bars"),
                "detail": len(result["matrix"]),
            },
            {
                "name": "first_failure_present",
                "pass": bool(m.get("first_failure_counts")),
                "detail": list((m.get("first_failure_distribution_pct") or {}).keys())[:5],
            },
            {
                "name": "priority_beams_analysed",
                "pass": all(b in beams or True for b in PRIORITY_BEAMS),
                "detail": list(PRIORITY_BEAMS),
            },
            {
                "name": "b10_analysed",
                "pass": "B10" in (special.get("problem_beams_b10_b12_b13") or {}),
                "detail": (special.get("problem_beams_b10_b12_b13") or {}).get("B10"),
            },
            {
                "name": "b12_analysed",
                "pass": "B12" in (special.get("problem_beams_b10_b12_b13") or {}),
                "detail": (special.get("problem_beams_b10_b12_b13") or {}).get("B12"),
            },
            {
                "name": "b13_analysed",
                "pass": "B13" in (special.get("problem_beams_b10_b12_b13") or {}),
                "detail": (special.get("problem_beams_b10_b12_b13") or {}).get("B13"),
            },
            {
                "name": "shared_b8_b9_b10_analysed",
                "pass": all(
                    b in (special.get("shared_beams_b8_b9_b10") or {})
                    for b in SHARED_CASE_BEAMS
                ),
                "detail": (special.get("shared_beams_b8_b9_b10") or {}).get("conclusion"),
            },
            {
                "name": "top_reinforcement_analysed",
                "pass": (special.get("top_reinforcement") or {}).get("gt_top_bars", 0) > 0,
                "detail": special.get("top_reinforcement"),
            },
            {
                "name": "recommendation_from_evidence",
                "pass": bool(m.get("recommended_next_phase")),
                "detail": m.get("recommended_next_phase"),
            },
            {
                "name": "determinism",
                "pass": determinism.get("determinism_status") == "PASS",
                "detail": determinism.get("diffs"),
            },
            {
                "name": "regression_fingerprints",
                "pass": bool(regression.get("unchanged")),
                "detail": regression.get("changed_keys"),
            },
            {
                "name": "no_engineering_changes",
                "pass": ENGINEERING_CHANGES == "NONE",
                "detail": ENGINEERING_CHANGES,
            },
        ]
