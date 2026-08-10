"""
P2.3 orchestrator — Controlled Production Gate + Re-benchmark.
MODEL_VERSION: 10.5.5
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from PhaseP21_leader_tip_chain_analysis.population import (
    derive_leader_rows,
    load_inputs,
)
from PhaseQA31_pipeline_diagnostics.artefact_locator import (
    PRIORITY_FOURTH_BEAMS,
    ArtefactLocator,
)

from .baseline import snapshot_baseline
from .benchmark import build_benchmark_comparison
from .candidate_gate import load_p22_candidates, select_controlled_candidates
from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID, PRODUCTION_POLICY, P23Config
from .overlay import apply_overlay, ownership_counts, rebuild_scoped
from .qa_validator import validate_p23
from .regression import compare_determinism, run_regression
from .render_compare import run_render_comparisons
from .report_builder import write_all
from .unit_tests import run_unit_tests


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _file_hash(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_graph(output_root: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not output_root:
        return None
    return _load_json(Path(output_root) / "PhaseT17_annotation_graph" / "AnnotationGraph.json")


class PhaseP23Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        mode: str = "controlled",
        set_key: str = "Fourth",
        beam_ids: Optional[Sequence[str]] = None,
        p22_root: Optional[Path] = None,
        config: Optional[P23Config] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root / "data" / "output" / "PhaseP23_controlled_production_gate"
        )
        self.mode = mode.upper()
        if self.mode == "OFF":
            self.mode = "BASELINE"
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.config = config or DEFAULT_CONFIG
        base = self.engine_root / "data" / "output"
        self.p22_root = Path(p22_root) if p22_root else base / "PhaseP22_leader_chain_evidence"
        self.qa33_root = base / "PhaseQA33_ownership_explainability"
        self.qa34_root = base / "PhaseQA34_ownership_competition_validation"
        self.qa41_root = base / "PhaseQA41_dropped_entity_recovery_audit"
        self.qa42_root = base / "PhaseQA42_candidate_search_envelope_recovery"
        self.qa43_root = base / "PhaseQA43_p2_leader_recovery"
        self.p21_root = base / "PhaseP21_leader_tip_chain_analysis"
        self.qa30_root = base / "PhaseQA30_unseen_benchmark"
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _build_analysis(self, artefacts: Dict[str, Any]) -> Dict[str, Any]:
        recovery_enabled = self.mode == "CONTROLLED" and self.config.leader_chain_recovery_enabled
        gate = select_controlled_candidates(
            p22_production=artefacts["p22"]["production_candidates"],
            p22_decisions=artefacts["p22"]["decisions"],
            recovery_enabled=recovery_enabled,
        )

        historical = artefacts["beam_ownership"]
        hist_path = artefacts["ownership_path"]
        hist_hash_before = _file_hash(hist_path)

        baseline_snap = snapshot_baseline(
            ownership=historical,
            scoped=artefacts.get("beam_scoped"),
            beam_ids=self.beam_ids,
            qa30_report=artefacts.get("qa30_report"),
            p22_candidates=gate,
            ownership_path=hist_path,
        )

        # Baseline mode ownership (exact)
        base_ov = apply_overlay(
            baseline_ownership=historical,
            graph=artefacts["graph"] or {},
            accepted_candidates=gate["accepted"],
            mode="BASELINE",
        )
        # Controlled overlay
        ctrl_ov = apply_overlay(
            baseline_ownership=historical,
            graph=artefacts["graph"] or {},
            accepted_candidates=gate["accepted"] if recovery_enabled else [],
            mode="CONTROLLED" if recovery_enabled else "BASELINE",
        )

        baseline_equal = (
            ownership_counts(base_ov["ownership"], self.beam_ids)
            == ownership_counts(historical, self.beam_ids)
            and not base_ov["migrations"]
        )

        # Rebuild scoped for affected beams
        affected = sorted(
            {
                m["beam_id"]
                for m in ctrl_ov["migrations"]
                if m.get("beam_id")
            }
            | ({"B16"} if recovery_enabled else set())
        )
        base_scoped = rebuild_scoped(
            historical, artefacts["graph"] or {}, beam_ids=affected or ["B16"]
        )
        # Use full historical scoped where available for baseline node sets
        if artefacts.get("beam_scoped"):
            for bid in affected or ["B16"]:
                existing = (artefacts["beam_scoped"].get("by_beam") or {}).get(bid)
                if existing:
                    base_scoped["by_beam"][bid] = existing

        ctrl_scoped = rebuild_scoped(
            ctrl_ov["ownership"], artefacts["graph"] or {}, beam_ids=affected or ["B16"]
        )

        render_dir = self.output_root / "RenderComparison"
        t182_dir = None
        if artefacts.get("run_output_root"):
            t182_dir = (
                Path(artefacts["run_output_root"])
                / "PhaseT182_adaptive_render_extent"
                / "RenderedBeams"
            )
        render_cmp = run_render_comparisons(
            engine_root=self.engine_root,
            run_root=artefacts["run_root"],
            output_root=artefacts["run_output_root"],
            affected_beams=affected or ["B16"],
            baseline_scoped_doc=base_scoped,
            controlled_scoped_doc=ctrl_scoped,
            render_root=render_dir,
            baseline_render_dir=t182_dir,
        )

        accuracy = build_benchmark_comparison(
            qa30_report=artefacts.get("qa30_report"),
            baseline_ownership=historical,
            controlled_ownership=ctrl_ov["ownership"],
            beam_ids=self.beam_ids,
            migration_count=len(ctrl_ov["migrations"]),
            render_result=render_cmp,
            steel_regenerated=False,
            controlled_qa30=None,
        )

        hist_hash_after = _file_hash(hist_path)
        assert hist_hash_before == hist_hash_after, "Historical T18 mutated unexpectedly"

        newly_owned = [m["entity_id"] for m in ctrl_ov["migrations"]]
        ann_new = [m for m in ctrl_ov["migrations"] if m.get("entity_type") == "Annotation"]
        bar_new = [
            m
            for m in ctrl_ov["migrations"]
            if str(m.get("entity_type") or "").startswith("Physical")
            or str(m.get("entity_id") or "").startswith("BAR")
        ]
        b16_row = next(
            (r for r in (render_cmp.get("rows") or []) if r.get("beam_id") == "B16"),
            {},
        )
        causal_break = None
        if ctrl_ov["migrations"] and not ann_new:
            causal_break = (
                "Leader (+ARR/LTGT) recovered into effective ownership, but linked "
                "annotation ANN-62d4cbc2 / bars were already T18-accepted — steel "
                "estimation path likely unchanged without Excel regeneration."
            )
        engineering = {
            "delta_leaders": ownership_counts(ctrl_ov["ownership"], self.beam_ids)[
                "accepted_leaders"
            ]
            - ownership_counts(historical, self.beam_ids)["accepted_leaders"],
            "newly_owned_entities": newly_owned,
            "annotation_newly_owned": [m["entity_id"] for m in ann_new],
            "bar_newly_owned": [m["entity_id"] for m in bar_new],
            "render_improved": bool(b16_row.get("questions", {}).get("did_crop_improve")),
            "b16_questions": b16_row.get("questions"),
            "bottleneck": accuracy.get("bottleneck"),
            "causal_break": causal_break,
            "causal_chain_summary": (
                "P2.2 E candidate -> effective ownership overlay -> graph ARR/LTGT "
                "propagation -> adaptive render comparison. Steel Excel not regenerated."
            ),
            "recommendation": (
                "Do not broaden Policy E yet. Ownership/render recovery is safe for "
                "B16::LDR::7A1FFD68. Next step: regenerate Estimation_Output.xlsx under "
                "controlled ownership to measure steel accuracy, or investigate whether "
                "already-owned annotation already feeds estimation."
            ),
        }

        analysis = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "mode": self.mode,
            "beam_ids": list(self.beam_ids),
            "gate": gate,
            "baseline_snapshot": baseline_snap,
            "baseline_ownership": historical,
            "controlled_ownership": ctrl_ov["ownership"],
            "migrations": ctrl_ov["migrations"],
            "propagation": ctrl_ov["propagation"],
            "added_entity_ids": ctrl_ov["added_entity_ids"],
            "render_comparison": render_cmp,
            "accuracy_comparison": accuracy,
            "baseline_mode_equal": baseline_equal,
            "engineering": engineering,
            "historical_t18_hash_before": hist_hash_before,
            "historical_t18_hash_after": hist_hash_after,
            "affected_beams": affected or ["B16"],
        }
        return analysis

    def _once(self, artefacts: Dict[str, Any]) -> Dict[str, Any]:
        analysis = self._build_analysis(artefacts)
        regression = run_regression(
            qa33_scores=artefacts["qa33_scores"],
            qa33_traces=artefacts["qa33_traces"],
            qa34_migration=artefacts["qa34_migration"],
            qa34_dropped=artefacts["qa34_dropped"],
            historical_beam_ownership=artefacts["beam_ownership"],
            priority_beams=self.beam_ids,
            qa41_pass=artefacts["qa41_pass"],
            qa42_summary=artefacts["qa42_summary"],
            qa43_summary=artefacts["qa43_summary"],
            p21_pass=artefacts["p21_pass"],
            p22_pass=artefacts["p22_pass"],
            baseline_snapshot=analysis["baseline_snapshot"],
            historical_ownership_path_hash=analysis["historical_t18_hash_before"],
            post_run_historical_hash=analysis["historical_t18_hash_after"],
            analysis_result=analysis,
        )
        return {"analysis": analysis, "regression": regression}

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - Controlled Production Gate + Re-benchmark")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Mode          : {self.mode}")
        print(f"Policy        : {PRODUCTION_POLICY}")
        print("=" * 72)
        t0 = time.perf_counter()

        print(f"[{PHASE_ID}] Running unit tests ...")
        unit_tests = run_unit_tests()
        print(
            f"[{PHASE_ID}] unit_tests="
            f"{unit_tests.get('passed')}/{unit_tests.get('total')} "
            f"pass={unit_tests.get('overall_pass')}"
        )

        p22 = load_p22_candidates(self.p22_root)
        inputs = load_inputs(
            qa43_root=self.qa43_root,
            qa41_root=self.qa41_root,
            qa42_root=self.qa42_root,
        )
        population = derive_leader_rows(inputs, priority_beams=self.beam_ids)

        locator = ArtefactLocator(self.engine_root, self.qa30_root)
        art = locator.locate_set(self.set_key)
        bundle = locator.load_bundle(art)
        graph = _load_graph(art.output_root)
        ownership = bundle.get("beam_ownership")
        if not ownership:
            raise FileNotFoundError("BeamOwnership.json missing for Fourth Set")
        ownership_path = Path(
            art.paths.get("beam_ownership")
            or (Path(art.output_root) / "PhaseT18_beam_ownership" / "BeamOwnership.json")
        )

        artefacts = {
            "p22": p22,
            "population": population,
            "beam_ownership": ownership,
            "beam_scoped": bundle.get("beam_scoped"),
            "graph": graph,
            "ownership_path": ownership_path,
            "run_root": Path(art.run_root) if art.run_root else None,
            "run_output_root": Path(art.output_root) if art.output_root else None,
            "qa33_scores": _load_json(self.qa33_root / "OwnershipScores.json"),
            "qa33_traces": _load_json(self.qa33_root / "EntityDecisionTrace.json"),
            "qa34_migration": _load_json(self.qa34_root / "OwnershipMigration.json"),
            "qa34_dropped": _load_json(self.qa34_root / "DroppedEntities.json"),
            "qa41_pass": _load_json(self.qa41_root / "PASS_FAIL_REPORT.json"),
            "qa42_summary": inputs.get("qa42_summary"),
            "qa43_summary": inputs.get("qa43_summary"),
            "p21_pass": _load_json(self.p21_root / "PASS_FAIL_REPORT.json"),
            "p22_pass": _load_json(self.p22_root / "PASS_FAIL_REPORT.json"),
            "qa30_report": _load_json(self.qa30_root / "Generalization_Benchmark_Report.json"),
        }
        if not artefacts["run_root"]:
            raise FileNotFoundError("Fourth Set web_run root not found")

        print(f"[{PHASE_ID}] Analysis pass 1 ...")
        run1 = self._once(artefacts)
        print(f"[{PHASE_ID}] Analysis pass 2 (determinism) ...")
        run2 = self._once(artefacts)
        determinism = compare_determinism(run1["regression"], run2["regression"])
        print(f"[{PHASE_ID}] determinism={determinism.get('determinism_status')}")

        analysis = run1["analysis"]
        regression = run1["regression"]
        validation = validate_p23(
            population_leader_count=int(population.get("leader_count") or 0),
            gate=analysis["gate"],
            baseline_mode_equal=bool(analysis["baseline_mode_equal"]),
            migrations=analysis["migrations"],
            analysis=analysis,
            regression=regression,
            determinism=determinism,
            unit_tests=unit_tests,
            render_comparison=analysis["render_comparison"],
            accuracy=analysis["accuracy_comparison"],
            mode=self.mode,
        )

        # Persist controlled ownership + scoped under P2.3 (never overwrite T18)
        ctrl_dir = self.output_root / "controlled_effective"
        ctrl_dir.mkdir(parents=True, exist_ok=True)
        (ctrl_dir / "BeamOwnership.json").write_text(
            json.dumps(analysis["controlled_ownership"], indent=2, default=str),
            encoding="utf-8",
        )
        scoped_ctrl = rebuild_scoped(
            analysis["controlled_ownership"],
            artefacts["graph"] or {},
            beam_ids=self.beam_ids,
        )
        (ctrl_dir / "BeamScopedAnnotations.json").write_text(
            json.dumps(scoped_ctrl, indent=2, default=str),
            encoding="utf-8",
        )

        paths = write_all(
            self.output_root,
            baseline_snapshot=analysis["baseline_snapshot"],
            controlled_ownership={
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "label": "CONTROLLED EFFECTIVE OWNERSHIP — NOT HISTORICAL T18",
                "mode": self.mode,
                "ownership": analysis["controlled_ownership"],
            },
            migrations={
                "phase_id": PHASE_ID,
                "count": len(analysis["migrations"]),
                "rows": analysis["migrations"],
            },
            propagation={
                "phase_id": PHASE_ID,
                "count": len(analysis["propagation"]),
                "rows": analysis["propagation"],
            },
            controlled_candidates={
                "phase_id": PHASE_ID,
                "accepted_count": analysis["gate"]["accepted_count"],
                "accepted_keys": analysis["gate"]["accepted_keys"],
                "accepted": analysis["gate"]["accepted"],
            },
            rejected_candidates={
                "phase_id": PHASE_ID,
                "rejected_count": analysis["gate"]["rejected_count"],
                "rejected": analysis["gate"]["rejected"],
            },
            render_comparison=analysis["render_comparison"],
            benchmark_baseline=analysis["accuracy_comparison"]["BenchmarkBaseline"],
            benchmark_controlled=analysis["accuracy_comparison"]["BenchmarkControlled"],
            accuracy=analysis["accuracy_comparison"],
            regression=regression,
            determinism=determinism,
            validation={
                **validation,
                "elapsed_s": round(time.perf_counter() - t0, 3),
            },
            unit_tests=unit_tests,
            engineering=analysis["engineering"],
        )

        elapsed = round(time.perf_counter() - t0, 3)
        print(f"\n[{PHASE_ID}] STATUS={validation.get('status')} elapsed={elapsed}s")
        print(f"[{PHASE_ID}] decision={validation.get('decision_class')}")
        print(
            f"[{PHASE_ID}] accepted_E={analysis['gate']['accepted_count']} "
            f"migrations={len(analysis['migrations'])}"
        )
        print(f"[{PHASE_ID}] output={self.output_root}")
        if validation.get("failed_gates"):
            print(f"[{PHASE_ID}] failed_gates={validation.get('failed_gates')}")

        return {
            "success": bool(validation.get("overall_pass")),
            "status": validation.get("status"),
            "decision_class": validation.get("decision_class"),
            "model_version": MODEL_VERSION,
            "mode": self.mode,
            "output_root": str(self.output_root),
            "gate": analysis["gate"],
            "migrations": analysis["migrations"],
            "validation": validation,
            "determinism": determinism,
            "unit_tests": unit_tests,
            "accuracy": analysis["accuracy_comparison"],
            "engineering": analysis["engineering"],
            "paths": paths,
            "elapsed_s": elapsed,
        }
