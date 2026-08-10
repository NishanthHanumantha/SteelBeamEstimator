"""
QA.4.3 orchestrator — P2 Leader Recovery.
MODEL_VERSION: 10.5.2
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
from PhaseQA42_candidate_search_envelope_recovery.contamination import (
    build_owned_elsewhere_index,
)

from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID, LeaderRecoveryConfig
from .population import derive_leader_population, load_qa41_bundle, load_qa42_summary
from .qa_validator import validate_qa43
from .reconciliation import build_reconciliation
from .recovery_engine import run_leader_recovery
from .regression import compare_determinism, run_regression
from .report_builder import build_summary, write_all
from .tests_gate import run_test_cases


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_annotation_graph(output_root: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not output_root:
        return None
    return _load_json(Path(output_root) / "PhaseT17_annotation_graph" / "AnnotationGraph.json")


class PhaseQA43Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        qa30_root: Optional[Path] = None,
        qa33_root: Optional[Path] = None,
        qa34_root: Optional[Path] = None,
        qa41_root: Optional[Path] = None,
        qa42_root: Optional[Path] = None,
        set_key: str = "Fourth",
        beam_ids: Optional[Sequence[str]] = None,
        config: Optional[LeaderRecoveryConfig] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root / "data" / "output" / "PhaseQA43_p2_leader_recovery"
        )
        self.qa30_root = qa30_root
        self.qa33_root = Path(qa33_root) if qa33_root else self.engine_root / "data" / "output" / "PhaseQA33_ownership_explainability"
        self.qa34_root = Path(qa34_root) if qa34_root else self.engine_root / "data" / "output" / "PhaseQA34_ownership_competition_validation"
        self.qa41_root = Path(qa41_root) if qa41_root else self.engine_root / "data" / "output" / "PhaseQA41_dropped_entity_recovery_audit"
        self.qa42_root = Path(qa42_root) if qa42_root else self.engine_root / "data" / "output" / "PhaseQA42_candidate_search_envelope_recovery"
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.config = config or DEFAULT_CONFIG
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _execute_once(self, artefacts: Dict[str, Any]) -> Dict[str, Any]:
        populations = artefacts["populations"]
        recovery = run_leader_recovery(
            leader_population=populations["leader_population"],
            beam_ownership=artefacts["beam_ownership"] or {},
            graph=artefacts["graph"] or {},
            migration_doc=artefacts["qa34_migration"],
            qa42_entity_keys=artefacts.get("qa42_keys") or set(),
            config=self.config,
            priority_beams=self.beam_ids,
        )
        reconciliation = build_reconciliation(
            original_dropped=populations["original_dropped"],
            leader_count=populations["leader_count"],
            high_count=populations["high_count"],
            medium_count=populations["medium_count"],
            low_count=populations["low_count"],
            unknown_count=populations["unknown_count"],
            audit_rows=recovery["audit_rows"],
            recovery_candidates=recovery["recovery_candidates"],
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
            qa42_summary=artefacts.get("qa42_summary"),
        )
        return {
            "recovery": recovery,
            "reconciliation": reconciliation,
            "regression": regression,
        }

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - P2 Leader Recovery")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Engine        : {self.engine_root}")
        print(f"Set           : {self.set_key}")
        print(f"Beams         : {', '.join(self.beam_ids)}")
        print("Mode          : APPEND-ONLY; T18 ownership remains authoritative")
        print("=" * 72)
        t0 = time.perf_counter()

        qa41 = load_qa41_bundle(self.qa41_root)
        if not qa41.get("DroppedEntityAudit"):
            raise FileNotFoundError(f"Missing DroppedEntityAudit.json under {self.qa41_root}")

        populations = derive_leader_population(
            qa41, config=self.config, priority_beams=self.beam_ids
        )
        print(
            f"[{PHASE_ID}] leaders={populations['leader_count']} "
            f"HIGH={populations['high_count']} MED={populations['medium_count']} "
            f"LOW={populations['low_count']} UNK={populations['unknown_count']}"
        )

        locator = ArtefactLocator(self.engine_root, self.qa30_root)
        art = locator.locate_set(self.set_key)
        bundle = locator.load_bundle(art)
        graph = _load_annotation_graph(art.output_root)

        qa42_summary = load_qa42_summary(self.qa42_root)
        qa42_cands = _load_json(self.qa42_root / "QA42_recovery_candidates.json") or {}
        qa42_keys = {
            str(c.get("stable_key") or "")
            for c in (qa42_cands.get("candidates") or [])
            if c.get("stable_key")
        }

        artefacts = {
            "populations": populations,
            "beam_ownership": bundle.get("beam_ownership"),
            "graph": graph,
            "qa33_scores": _load_json(self.qa33_root / "OwnershipScores.json"),
            "qa33_traces": _load_json(self.qa33_root / "EntityDecisionTrace.json"),
            "qa34_migration": _load_json(self.qa34_root / "OwnershipMigration.json"),
            "qa34_dropped": _load_json(self.qa34_root / "DroppedEntities.json"),
            "qa42_summary": qa42_summary,
            "qa42_keys": qa42_keys,
        }

        print(f"[{PHASE_ID}] Recovery pass 1 ...")
        run1 = self._execute_once(artefacts)
        print(f"[{PHASE_ID}] Recovery pass 2 (determinism) ...")
        run2 = self._execute_once(artefacts)
        determinism = compare_determinism(run1["regression"], run2["regression"])
        print(f"[{PHASE_ID}] determinism={determinism.get('determinism_status')}")

        recovery = run1["recovery"]
        reconciliation = run1["reconciliation"]
        regression = run1["regression"]
        contamination = recovery["contamination"]

        owned_elsewhere = build_owned_elsewhere_index(artefacts["qa34_migration"])
        tests = run_test_cases(
            audit_rows=recovery["audit_rows"],
            recovery_candidates=recovery["recovery_candidates"],
            populations=populations,
            contamination=contamination,
            determinism=determinism,
            regression=regression,
            owned_elsewhere_ids=owned_elsewhere,
        )
        print(f"[{PHASE_ID}] tests_pass={tests.get('all_pass')} failed={tests.get('failed')}")

        validation = validate_qa43(
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
        paths = write_all(
            self.output_root,
            recovery_candidates=recovery["recovery_candidates"],
            audit_rows=recovery["audit_rows"],
            summary=summary,
            reconciliation=reconciliation,
            regression=regression,
            contamination=contamination,
            tests=tests,
            determinism=determinism,
            validation={
                **validation,
                "summary": summary,
                "elapsed_s": round(time.perf_counter() - t0, 3),
            },
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
