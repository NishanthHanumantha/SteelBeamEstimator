"""
P2.2 orchestrator — Leader-Chain Evidence Enhancement.
MODEL_VERSION: 10.5.4
"""
from __future__ import annotations

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

from .analysis import run_analysis
from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID, P22Config
from .qa_validator import validate_p22
from .regression import compare_determinism, run_regression
from .report_builder import write_all
from .unit_tests import run_unit_tests


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_graph(output_root: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not output_root:
        return None
    return _load_json(Path(output_root) / "PhaseT17_annotation_graph" / "AnnotationGraph.json")


class PhaseP22Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        qa30_root: Optional[Path] = None,
        qa33_root: Optional[Path] = None,
        qa34_root: Optional[Path] = None,
        qa41_root: Optional[Path] = None,
        qa42_root: Optional[Path] = None,
        qa43_root: Optional[Path] = None,
        p21_root: Optional[Path] = None,
        set_key: str = "Fourth",
        beam_ids: Optional[Sequence[str]] = None,
        config: Optional[P22Config] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root / "data" / "output" / "PhaseP22_leader_chain_evidence"
        )
        self.qa30_root = qa30_root
        base = self.engine_root / "data" / "output"
        self.qa33_root = Path(qa33_root) if qa33_root else base / "PhaseQA33_ownership_explainability"
        self.qa34_root = Path(qa34_root) if qa34_root else base / "PhaseQA34_ownership_competition_validation"
        self.qa41_root = Path(qa41_root) if qa41_root else base / "PhaseQA41_dropped_entity_recovery_audit"
        self.qa42_root = Path(qa42_root) if qa42_root else base / "PhaseQA42_candidate_search_envelope_recovery"
        self.qa43_root = Path(qa43_root) if qa43_root else base / "PhaseQA43_p2_leader_recovery"
        self.p21_root = Path(p21_root) if p21_root else base / "PhaseP21_leader_tip_chain_analysis"
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.config = config or DEFAULT_CONFIG
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _once(self, artefacts: Dict[str, Any]) -> Dict[str, Any]:
        analysis = run_analysis(
            population=artefacts["population"],
            beam_ownership=artefacts["beam_ownership"] or {},
            graph=artefacts["graph"] or {},
            priority_beams=self.beam_ids,
            config=self.config,
        )
        regression = run_regression(
            qa33_scores=artefacts["qa33_scores"],
            qa33_traces=artefacts["qa33_traces"],
            qa34_migration=artefacts["qa34_migration"],
            qa34_dropped=artefacts["qa34_dropped"],
            beam_ownership=artefacts["beam_ownership"],
            priority_beams=self.beam_ids,
            qa41_pass=artefacts["qa41_pass"],
            qa42_summary=artefacts["qa42_summary"],
            qa43_summary=artefacts["qa43_summary"],
            p21_pass=artefacts["p21_pass"],
            analysis_result=analysis,
        )
        return {"analysis": analysis, "regression": regression}

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - Leader-Chain Evidence Enhancement")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Mode          : {self.config.production_gate.value}")
        print(f"Label         : {self.config.label}")
        print("=" * 72)
        t0 = time.perf_counter()

        print(f"[{PHASE_ID}] Running unit tests ...")
        unit_tests = run_unit_tests()
        print(
            f"[{PHASE_ID}] unit_tests="
            f"{unit_tests.get('passed')}/{unit_tests.get('total')} "
            f"pass={unit_tests.get('overall_pass')}"
        )
        if not unit_tests.get("overall_pass"):
            print(f"[{PHASE_ID}] failed_unit_tests={unit_tests.get('failed_ids')}")

        inputs = load_inputs(
            qa43_root=self.qa43_root,
            qa41_root=self.qa41_root,
            qa42_root=self.qa42_root,
        )
        if not (inputs.get("qa43_audit") or {}).get("rows"):
            raise FileNotFoundError(
                f"Missing QA.4.3 leader_recovery_audit.json under {self.qa43_root}"
            )
        population = derive_leader_rows(inputs, priority_beams=self.beam_ids)
        print(
            f"[{PHASE_ID}] leaders={population['leader_count']} "
            f"eligible={population['eligible_count']}"
        )

        locator = ArtefactLocator(self.engine_root, self.qa30_root)
        art = locator.locate_set(self.set_key)
        bundle = locator.load_bundle(art)
        graph = _load_graph(art.output_root)

        artefacts = {
            "population": population,
            "beam_ownership": bundle.get("beam_ownership"),
            "graph": graph,
            "qa33_scores": _load_json(self.qa33_root / "OwnershipScores.json"),
            "qa33_traces": _load_json(self.qa33_root / "EntityDecisionTrace.json"),
            "qa34_migration": _load_json(self.qa34_root / "OwnershipMigration.json"),
            "qa34_dropped": _load_json(self.qa34_root / "DroppedEntities.json"),
            "qa41_pass": _load_json(self.qa41_root / "PASS_FAIL_REPORT.json"),
            "qa42_summary": inputs.get("qa42_summary"),
            "qa43_summary": inputs.get("qa43_summary"),
            "p21_pass": _load_json(self.p21_root / "PASS_FAIL_REPORT.json"),
        }

        print(f"[{PHASE_ID}] Analysis pass 1 ...")
        run1 = self._once(artefacts)
        print(f"[{PHASE_ID}] Analysis pass 2 (determinism) ...")
        run2 = self._once(artefacts)
        determinism = compare_determinism(run1["regression"], run2["regression"])
        print(f"[{PHASE_ID}] determinism={determinism.get('determinism_status')}")

        analysis = run1["analysis"]
        regression = run1["regression"]
        validation = validate_p22(
            population=population,
            analysis=analysis,
            regression=regression,
            determinism=determinism,
            unit_test_result=unit_tests,
        )
        # Reflect readiness into summary before write
        analysis["summary"]["ready_for_controlled_production_gate"] = validation.get(
            "ready_for_controlled_production_gate"
        )
        analysis["summary"]["status"] = validation.get("status")

        paths = write_all(
            self.output_root,
            analysis=analysis,
            regression=regression,
            determinism=determinism,
            validation={
                **validation,
                "generated_at": None,
                "elapsed_s": round(time.perf_counter() - t0, 3),
            },
            unit_tests=unit_tests,
        )
        elapsed = round(time.perf_counter() - t0, 3)
        summary = analysis.get("summary") or {}
        print(f"\n[{PHASE_ID}] STATUS={validation.get('status')} elapsed={elapsed}s")
        print(
            f"[{PHASE_ID}] policy_E_accepts={summary.get('policy_e_accept_all')} "
            f"candidates={summary.get('production_candidate_keys')}"
        )
        print(
            f"[{PHASE_ID}] ready_for_controlled_production_gate="
            f"{validation.get('ready_for_controlled_production_gate')}"
        )
        print(f"[{PHASE_ID}] output={self.output_root}")
        if not validation.get("overall_pass"):
            print(f"[{PHASE_ID}] failed_gates={validation.get('failed_gates')}")

        return {
            "success": bool(validation.get("overall_pass")),
            "status": validation.get("status"),
            "model_version": MODEL_VERSION,
            "output_root": str(self.output_root),
            "leader_count": analysis.get("leader_count"),
            "eligible_count": analysis.get("eligible_count"),
            "summary": summary,
            "validation": validation,
            "determinism": determinism,
            "unit_tests": unit_tests,
            "paths": paths,
            "elapsed_s": elapsed,
            "ready_for_controlled_production_gate": validation.get(
                "ready_for_controlled_production_gate"
            ),
        }
