"""
QA.4.2 orchestrator — P1 Candidate / Search Envelope Recovery.
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from PhaseQA31_pipeline_diagnostics.artefact_locator import (
    PRIORITY_FOURTH_BEAMS,
    ArtefactLocator,
)

from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID, CandidateRecoveryConfig
from .contamination import build_owned_elsewhere_index
from .population import derive_populations, load_qa41_bundle
from .qa_validator import validate_qa42
from .reconciliation import build_reconciliation
from .recovery_engine import run_recovery
from .regression import compare_determinism, run_regression
from .report_builder import (
    build_high_report,
    build_pattern_summary,
    build_summary,
    write_all,
)
from .tests_gate import run_test_cases

MODEL_VERSION_LOCAL = MODEL_VERSION


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_annotation_graph(output_root: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not output_root:
        return None
    return _load_json(Path(output_root) / "PhaseT17_annotation_graph" / "AnnotationGraph.json")


class PhaseQA42Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        qa30_root: Optional[Path] = None,
        qa33_root: Optional[Path] = None,
        qa34_root: Optional[Path] = None,
        qa41_root: Optional[Path] = None,
        set_key: str = "Fourth",
        beam_ids: Optional[Sequence[str]] = None,
        config: Optional[CandidateRecoveryConfig] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root
            / "data"
            / "output"
            / "PhaseQA42_candidate_search_envelope_recovery"
        )
        self.qa30_root = qa30_root
        self.qa33_root = (
            Path(qa33_root)
            if qa33_root
            else self.engine_root
            / "data"
            / "output"
            / "PhaseQA33_ownership_explainability"
        )
        self.qa34_root = (
            Path(qa34_root)
            if qa34_root
            else self.engine_root
            / "data"
            / "output"
            / "PhaseQA34_ownership_competition_validation"
        )
        self.qa41_root = (
            Path(qa41_root)
            if qa41_root
            else self.engine_root
            / "data"
            / "output"
            / "PhaseQA41_dropped_entity_recovery_audit"
        )
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.config = config or DEFAULT_CONFIG
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _execute_once(self, *, artefacts: Dict[str, Any]) -> Dict[str, Any]:
        populations = artefacts["populations"]
        recovery = run_recovery(
            high_population=populations["high_potential_population"],
            medium_population=populations["medium_population"],
            low_population=populations["low_population"],
            beam_ownership=artefacts["beam_ownership"] or {},
            graph=artefacts["graph"] or {},
            migration_doc=artefacts["qa34_migration"],
            config=self.config,
            priority_beams=self.beam_ids,
        )
        reconciliation = build_reconciliation(
            original_dropped=populations["original_dropped"],
            envelope_count=populations["envelope_count"],
            high_count=populations["high_count"],
            medium_count=populations["medium_count"],
            low_count=populations["low_count"],
            audit_rows=recovery["audit_rows"],
            recovery_candidates=recovery["recovery_candidates"],
            diagnostic_rows=recovery["diagnostic_medium_low"],
        )
        regression = run_regression(
            qa33_scores=artefacts["qa33_scores"],
            qa33_traces=artefacts["qa33_traces"],
            qa34_migration=artefacts["qa34_migration"],
            qa34_dropped=artefacts["qa34_dropped"],
            beam_ownership=artefacts["beam_ownership"],
            priority_beams=self.beam_ids,
            recovery_candidates=recovery["recovery_candidates"],
            audit_rows=recovery["audit_rows"],
            reconciliation=reconciliation,
        )
        return {
            "recovery": recovery,
            "reconciliation": reconciliation,
            "regression": regression,
        }

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - P1 Candidate / Search Envelope Recovery")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Engine        : {self.engine_root}")
        print(f"Set           : {self.set_key}")
        print(f"Beams         : {', '.join(self.beam_ids)}")
        print("Mode          : APPEND-ONLY recovery; existing ownership engine decides")
        print("=" * 72)
        t0 = time.perf_counter()

        print(f"\n[{PHASE_ID}] Loading QA.4.1 from {self.qa41_root}")
        qa41 = load_qa41_bundle(self.qa41_root)
        if not qa41.get("DroppedEntityAudit"):
            raise FileNotFoundError(
                f"Missing DroppedEntityAudit.json under {self.qa41_root}"
            )

        populations = derive_populations(
            qa41, config=self.config, priority_beams=self.beam_ids
        )
        print(
            f"[{PHASE_ID}] dropped={populations['original_dropped']} "
            f"envelope={populations['envelope_count']} "
            f"HIGH={populations['high_count']} "
            f"fifth={populations['fifth_set_recovery_population']} "
            f"sixth={populations['sixth_set_recovery_population']}"
        )

        locator = ArtefactLocator(self.engine_root, self.qa30_root)
        art = locator.locate_set(self.set_key)
        bundle = locator.load_bundle(art)
        graph = _load_annotation_graph(art.output_root)
        beam_ownership = bundle.get("beam_ownership")

        qa33_scores = _load_json(self.qa33_root / "OwnershipScores.json")
        qa33_traces = _load_json(self.qa33_root / "EntityDecisionTrace.json")
        qa34_migration = _load_json(self.qa34_root / "OwnershipMigration.json")
        qa34_dropped = _load_json(self.qa34_root / "DroppedEntities.json")

        print(f"[{PHASE_ID}] run_root={art.run_root}")
        print(f"[{PHASE_ID}] beam_ownership={'YES' if beam_ownership else 'NO'}")
        print(f"[{PHASE_ID}] AnnotationGraph={'YES' if graph else 'NO'}")

        artefacts = {
            "populations": populations,
            "beam_ownership": beam_ownership,
            "graph": graph,
            "qa33_scores": qa33_scores,
            "qa33_traces": qa33_traces,
            "qa34_migration": qa34_migration,
            "qa34_dropped": qa34_dropped,
        }

        print(f"[{PHASE_ID}] Recovery pass 1 ...")
        run1 = self._execute_once(artefacts=artefacts)
        print(f"[{PHASE_ID}] Recovery pass 2 (determinism) ...")
        run2 = self._execute_once(artefacts=artefacts)

        determinism = compare_determinism(run1["regression"], run2["regression"])
        print(f"[{PHASE_ID}] determinism={determinism.get('determinism_status')}")

        recovery = run1["recovery"]
        reconciliation = run1["reconciliation"]
        regression = run1["regression"]
        contamination = recovery["contamination"]

        owned_elsewhere = build_owned_elsewhere_index(qa34_migration)
        tests = run_test_cases(
            audit_rows=recovery["audit_rows"],
            diagnostic_rows=recovery["diagnostic_medium_low"],
            populations=populations,
            contamination=contamination,
            determinism=determinism,
            owned_elsewhere_ids=owned_elsewhere,
        )
        print(f"[{PHASE_ID}] tests_pass={tests.get('all_pass')} failed={tests.get('failed')}")

        validation = validate_qa42(
            populations=populations,
            reconciliation=reconciliation,
            audit_rows=recovery["audit_rows"],
            contamination=contamination,
            regression=regression,
            tests=tests,
            determinism=determinism,
        )

        summary = build_summary(
            populations=populations,
            reconciliation=reconciliation,
            contamination=contamination,
            regression=regression,
            determinism=determinism,
            validation=validation,
        )
        high_report = build_high_report(recovery["audit_rows"])
        pattern_summary = build_pattern_summary(
            recovery["audit_rows"], recovery["diagnostic_medium_low"]
        )

        paths = write_all(
            self.output_root,
            recovery_candidates=recovery["recovery_candidates"],
            audit_rows=recovery["audit_rows"],
            summary=summary,
            reconciliation=reconciliation,
            regression=regression,
            contamination=contamination,
            pattern_summary=pattern_summary,
            high_report=high_report,
            tests=tests,
            determinism=determinism,
            validation={
                **validation,
                "summary": summary,
                "elapsed_s": round(time.perf_counter() - t0, 3),
            },
            diagnostic_rows=recovery["diagnostic_medium_low"],
        )

        elapsed = round(time.perf_counter() - t0, 3)
        print(f"\n[{PHASE_ID}] STATUS={validation.get('status')} elapsed={elapsed}s")
        print(f"[{PHASE_ID}] output={self.output_root}")
        if not validation.get("overall_pass"):
            print(f"[{PHASE_ID}] failed_gates={validation.get('failed_gates')}")

        return {
            "success": bool(validation.get("overall_pass")),
            "status": validation.get("status"),
            "model_version": MODEL_VERSION,
            "output_root": str(self.output_root),
            "summary": summary,
            "reconciliation": reconciliation,
            "validation": validation,
            "determinism": determinism,
            "paths": paths,
            "elapsed_s": elapsed,
        }
