"""
QA.4.1 orchestrator — Dropped Entity Recovery Audit (diagnostic only).
MODEL_VERSION: 10.5.0
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from PhaseQA31_pipeline_diagnostics.artefact_locator import (
    PRIORITY_FOURTH_BEAMS,
    ArtefactLocator,
)

from .audit_engine import enrich_and_audit_all
from .baseline import derive_dropped_population, load_qa34_bundle, validate_baseline
from .patterns import (
    build_priority_matrix,
    build_recommendations,
    cluster_patterns,
    select_representatives,
)
from .qa_validator import validate_qa41
from .regression import run_regression
from .report_builder import write_all, write_execution_summary
from .visualizer import generate_all_visuals

MODEL_VERSION = "10.5.0"
PHASE_ID = "QA.4.1"


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_annotation_graph(output_root: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not output_root:
        return None
    path = Path(output_root) / "PhaseT17_annotation_graph" / "AnnotationGraph.json"
    return _load_json(path)


def _count_excluded_sets(qa34: Dict[str, Any], priority_beams: Sequence[str]) -> Dict[str, int]:
    """Count Fifth/Sixth entities seen in shared registries but excluded from QA.4.1."""
    fifth = sixth = 0
    registry = qa34.get("OwnershipCompetitionRegistry") or {}
    for e in registry.get("entities") or registry.get("identities") or []:
        ds = str(e.get("drawing_set") or e.get("set_key") or "").lower()
        if "fifth" in ds:
            fifth += 1
        elif "sixth" in ds:
            sixth += 1
    # Competition matrix beams outside priority Fourth list are not Fifth/Sixth
    # unless labelled; DroppedEntities for this phase is Fourth-only already.
    return {"fifth_set_entities_excluded": fifth, "sixth_set_entities_excluded": sixth}


class PhaseQA41Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        qa30_root: Optional[Path] = None,
        qa33_root: Optional[Path] = None,
        qa34_root: Optional[Path] = None,
        set_key: str = "Fourth",
        beam_ids: Optional[Sequence[str]] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root
            / "data"
            / "output"
            / "PhaseQA41_dropped_entity_recovery_audit"
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
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - Dropped Entity Recovery Audit")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Engine        : {self.engine_root}")
        print(f"Set           : {self.set_key}")
        print(f"Beams         : {', '.join(self.beam_ids)}")
        print("Mode          : DIAGNOSTIC ONLY (no recovery / no ownership changes)")
        print("=" * 72)
        t0 = time.perf_counter()

        # --- STEP 1/2: Rebuild + validate baseline from QA.3.4 ---
        print(f"\n[{PHASE_ID}] Loading QA.3.4 artefacts from {self.qa34_root}")
        qa34 = load_qa34_bundle(self.qa34_root)
        if not qa34.get("DroppedEntities"):
            raise FileNotFoundError(
                f"Missing DroppedEntities.json under {self.qa34_root}"
            )

        population = derive_dropped_population(
            qa34,
            priority_beams=self.beam_ids,
            drawing_set="Fourth Set Drawings",
            set_key=self.set_key,
        )
        excluded = _count_excluded_sets(qa34, self.beam_ids)
        baseline_validation = validate_baseline(population)
        baseline_validation["priority_beams"] = list(self.beam_ids)
        baseline_validation["priority_beam_count"] = len(self.beam_ids)
        baseline_validation["rejected"] = (population.get("qa34_statistics") or {}).get(
            "rejected"
        )
        baseline_validation["owned_elsewhere"] = (
            population.get("qa34_statistics") or {}
        ).get("owned_elsewhere")
        baseline_validation["dropped"] = (population.get("qa34_statistics") or {}).get(
            "dropped"
        )
        baseline_validation["audit_population"] = population.get("audit_population")
        baseline_validation["fifth_set_entities_excluded"] = excluded[
            "fifth_set_entities_excluded"
        ]
        baseline_validation["sixth_set_entities_excluded"] = excluded[
            "sixth_set_entities_excluded"
        ]
        baseline_validation["duplicates_detected"] = population.get(
            "duplicates_detected"
        )
        baseline_validation["category_counts_raw"] = population.get(
            "category_counts_raw"
        )

        print(
            f"[{PHASE_ID}] baseline status={baseline_validation.get('status')} "
            f"audit_population={population.get('audit_population')} "
            f"rejected={baseline_validation.get('rejected')} "
            f"owned_elsewhere={baseline_validation.get('owned_elsewhere')} "
            f"dropped={baseline_validation.get('dropped')}"
        )

        # Always write baseline validation first
        (self.output_root / "QA41BaselineValidation.json").write_text(
            json.dumps(baseline_validation, indent=2, default=str),
            encoding="utf-8",
        )

        if not baseline_validation.get("proceed_to_audit"):
            print(f"[{PHASE_ID}] BASELINE_MISMATCH — stopping before recovery analysis")
            elapsed = round(time.perf_counter() - t0, 3)
            fail_report = {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "status": "FAIL",
                "overall_pass": False,
                "reason": "BASELINE_MISMATCH",
                "baseline_validation": baseline_validation,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            (self.output_root / "PASS_FAIL_REPORT.json").write_text(
                json.dumps(fail_report, indent=2, default=str), encoding="utf-8"
            )
            return {
                "success": False,
                "output_root": str(self.output_root),
                "status": "FAIL",
                "baseline_validation": baseline_validation,
                "elapsed_s": elapsed,
            }

        # --- Load Fourth Set production artefacts (read-only) ---
        locator = ArtefactLocator(self.engine_root, self.qa30_root)
        art = locator.locate_set(self.set_key)
        bundle = locator.load_bundle(art)
        graph_doc = _load_annotation_graph(art.output_root)
        print(f"[{PHASE_ID}] run_root={art.run_root}")
        print(f"[{PHASE_ID}] beam_ownership={'YES' if bundle.get('beam_ownership') else 'NO'}")
        print(f"[{PHASE_ID}] AnnotationGraph={'YES' if graph_doc else 'NO'}")

        scores_path = self.qa33_root / "OwnershipScores.json"
        traces_path = self.qa33_root / "EntityDecisionTrace.json"
        ownership_scores = _load_json(scores_path)
        decision_traces = _load_json(traces_path)
        print(f"[{PHASE_ID}] qa33 OwnershipScores={'YES' if ownership_scores else 'NO'}")
        print(f"[{PHASE_ID}] qa33 EntityDecisionTrace={'YES' if decision_traces else 'NO'}")

        # --- STEPS 3-10: Audit ---
        print(f"[{PHASE_ID}] Auditing {len(population['records'])} dropped entities ...")
        audit_result = enrich_and_audit_all(
            population["records"],
            beam_ownership=bundle.get("beam_ownership") or {},
            graph_doc=graph_doc,
            migration=qa34.get("OwnershipMigration"),
            priority_beams=self.beam_ids,
        )
        audits = audit_result["audits"]
        print(
            f"[{PHASE_ID}] categories={audit_result.get('category_counts')} "
            f"potentials={audit_result.get('potential_counts')}"
        )

        # --- STEPS 11-13: Patterns / representatives / priority ---
        clustered = cluster_patterns(audits)
        for a in audits:
            stamp = (clustered.get("pattern_of") or {}).get(a["stable_key"]) or {}
            a["pattern_id"] = stamp.get("pattern_id")
            a["pattern_description"] = stamp.get("pattern_description")

        representatives = select_representatives(audits)
        matrix = build_priority_matrix(audits, clustered.get("patterns") or [])
        recommendations = build_recommendations(audits, matrix, representatives)
        recommendations["answers"]["7_dominant_patterns"] = [
            p.get("pattern_id") for p in (clustered.get("patterns") or [])[:8]
        ]

        # --- Visuals ---
        vis_dir = self.output_root / "Visualisations"
        visual_paths = generate_all_visuals(
            out_dir=vis_dir,
            audits=audits,
            patterns=clustered.get("patterns") or [],
            matrix=matrix,
            representatives=representatives,
        )

        # --- STEP 16: Regression ---
        regression = run_regression(
            qa33_scores=ownership_scores,
            qa33_traces=decision_traces,
            qa34_migration=qa34.get("OwnershipMigration"),
            qa34_dropped=qa34.get("DroppedEntities"),
            qa34_regression=qa34.get("RegressionReport"),
        )
        print(f"[{PHASE_ID}] regression={regression.get('regression_status')}")

        # --- Validate ---
        validation = validate_qa41(
            baseline_validation=baseline_validation,
            audits=audits,
            regression=regression,
            category_counts=audit_result.get("category_counts") or {},
            potential_counts=audit_result.get("potential_counts") or {},
            patterns=clustered,
            representatives=representatives,
            matrix=matrix,
            priority_beams=self.beam_ids,
        )

        meta = {
            "engine_root": str(self.engine_root),
            "drawing_set": "Fourth Set Drawings",
            "set_key": self.set_key,
            "run_root": str(art.run_root) if art.run_root else None,
            "qa33_root": str(self.qa33_root),
            "qa34_root": str(self.qa34_root),
            "beam_ids": list(self.beam_ids),
            "production_regenerated": False,
            "engineering_modules_modified": False,
            "ownership_decisions_mutated": False,
            "recovery_applied": False,
            "read_only": True,
            "annotation_graph_loaded": graph_doc is not None,
        }

        paths = write_all(
            self.output_root,
            baseline_validation=baseline_validation,
            audits=audits,
            envelope_audits=audit_result.get("envelope_audits") or [],
            leader_audits=audit_result.get("leader_audits") or [],
            geometry_audits=audit_result.get("geometry_audits") or [],
            evidence_rows=audit_result.get("evidence_rows") or [],
            patterns=clustered,
            representatives=representatives,
            matrix=matrix,
            recommendations=recommendations,
            regression=regression,
            category_counts=audit_result.get("category_counts") or {},
            potential_counts=audit_result.get("potential_counts") or {},
            visual_paths=visual_paths,
            meta=meta,
        )

        elapsed = round(time.perf_counter() - t0, 3)
        write_execution_summary(
            self.output_root,
            baseline_validation=baseline_validation,
            category_counts=audit_result.get("category_counts") or {},
            potential_counts=audit_result.get("potential_counts") or {},
            matrix=matrix,
            recommendations=recommendations,
            regression=regression,
            validation=validation,
            elapsed=elapsed,
        )

        pass_fail = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "status": "PASS" if validation.get("overall_pass") else "FAIL",
            "overall_pass": bool(validation.get("overall_pass")),
            "validation": validation,
            "baseline_status": baseline_validation.get("status"),
            "regression_status": regression.get("regression_status"),
            "category_counts": audit_result.get("category_counts"),
            "potential_counts": audit_result.get("potential_counts"),
            "evidence_driven_p1": matrix.get("evidence_driven_p1"),
            "fourth_set_entities_in_scope": baseline_validation.get(
                "fourth_set_entities_in_scope"
            ),
            "fifth_set_entities_excluded": baseline_validation.get(
                "fifth_set_entities_excluded"
            ),
            "sixth_set_entities_excluded": baseline_validation.get(
                "sixth_set_entities_excluded"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": elapsed,
        }
        (self.output_root / "PASS_FAIL_REPORT.json").write_text(
            json.dumps(pass_fail, indent=2, default=str), encoding="utf-8"
        )
        paths["PASS_FAIL_REPORT.json"] = str(self.output_root / "PASS_FAIL_REPORT.json")

        print(f"\n[{PHASE_ID}] STATUS={pass_fail['status']} elapsed={elapsed}s")
        print(f"[{PHASE_ID}] output={self.output_root}")
        if not validation.get("overall_pass"):
            print(f"[{PHASE_ID}] failed_checks={validation.get('failed_checks')}")

        return {
            "success": bool(validation.get("overall_pass")),
            "output_root": str(self.output_root),
            "status": pass_fail["status"],
            "baseline_validation": baseline_validation,
            "category_counts": audit_result.get("category_counts"),
            "potential_counts": audit_result.get("potential_counts"),
            "evidence_driven_p1": matrix.get("evidence_driven_p1"),
            "validation_overall_pass": validation.get("overall_pass"),
            "regression_status": regression.get("regression_status"),
            "paths": paths,
            "elapsed_s": elapsed,
        }
