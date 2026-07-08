"""Engineering Object Recovery Expansion orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.engineering_recovery_expansion.candidate_classifier import CandidateClassifier
from src.engineering_recovery_expansion.candidate_loader import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    CandidateLoader,
    default_paths,
)
from src.engineering_recovery_expansion.eligibility_engine import EligibilityEngine
from src.engineering_recovery_expansion.engineering_gap_detector import EngineeringGapDetector
from src.engineering_recovery_expansion.engineering_similarity import EngineeringSimilarity
from src.engineering_recovery_expansion.expansion_builder import ExpansionBuilder
from src.engineering_recovery_expansion.export import EXPORT_FILES, ExpansionExporter
from src.engineering_recovery_expansion.production_integrator import ProductionIntegrator
from src.engineering_recovery_expansion.statistics import ExpansionStatistics
from src.engineering_recovery_expansion.validation import ExpansionValidator


class ExpansionEngine:
    """Run deterministic engineering object recovery expansion."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = CandidateLoader(self._project_root).collect()
        gaps = EngineeringGapDetector.detect(snapshot)

        classifier = CandidateClassifier()
        similarity_engine = EngineeringSimilarity()
        eligibility_engine = EligibilityEngine()
        builder = ExpansionBuilder()

        classifications: Dict[str, str] = {}
        similarities: Dict[str, dict[str, Any]] = {}
        eligibility_results: List[dict[str, Any]] = []

        for gap in gaps.get("candidate_pool") or []:
            discovery_id = str(gap.get("discovery_id") or "")
            inventory = gap.get("inventory") or {}
            expansion_class = classifier.classify(gap, snapshot)
            classifications[discovery_id] = expansion_class
            similarity = similarity_engine.score(inventory, snapshot)
            similarities[discovery_id] = similarity
            eligibility_results.append(
                eligibility_engine.evaluate(gap, expansion_class, similarity, snapshot)
            )

        candidates = builder.build_candidates(gaps, classifications, similarities, eligibility_results)
        decisions = builder.build_decisions(eligibility_results)
        approved = [item for item in eligibility_results if item.get("recover")]
        approved = [
            item
            for item in approved
            if str(item.get("discovery_id")) not in set(snapshot.get("expansion_recovered_ids") or [])
        ]

        existing_registry_entries = list(snapshot.get("expansion_registry_entries") or [])
        production_integration: dict[str, Any] = {"status": "SKIPPED", "reason": "No approved expansion recoveries"}
        recovered_objects: List[dict[str, Any]] = []
        normalized_bars: List[dict[str, Any]] = []
        registry_entries: List[dict[str, Any]] = list(existing_registry_entries)

        if approved:
            recovery_decisions = builder.to_recovery_decisions(approved)
            production_integration = ProductionIntegrator(self._project_root).integrate(
                snapshot,
                approved,
                recovery_decisions,
            )
            recovered_objects = production_integration.get("recovered_objects") or []
            normalized_bars = production_integration.get("normalized_bars") or []
            new_entries, _ = builder.build_registry_entries(
                recovered_objects,
                approved,
                normalized_bars,
                snapshot.get("id_counters") or {},
            )
            registry_entries = existing_registry_entries + new_entries
        elif existing_registry_entries:
            recovered_objects = self._recovered_objects_from_registry(existing_registry_entries, snapshot)
            production_integration = ProductionIntegrator(self._project_root).integrate(snapshot, [], [])

        traceability = builder.build_traceability(candidates, registry_entries, recovered_objects)
        statistics = ExpansionStatistics.build(
            candidates,
            decisions,
            recovered_objects,
            snapshot,
            registry_count=len(registry_entries),
        )
        health = ExpansionStatistics.build_health(statistics)
        summary = ExpansionStatistics.build_summary(statistics, health, {"status": "PENDING"})

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "load_status": snapshot.get("load_status"),
            "gaps": gaps,
            "candidates": candidates,
            "decisions": decisions,
            "recovered_objects": recovered_objects,
            "expansion_registry": {
                "registry_count": len(registry_entries),
                "entries": registry_entries,
            },
            "traceability": traceability,
            "statistics": statistics,
            "health": health,
            "summary": summary,
            "production_integration": production_integration,
        }

        validator = ExpansionValidator()
        result["validation"] = validator.validate(result, snapshot)
        result["summary"] = ExpansionStatistics.build_summary(statistics, health, result["validation"])

        output_dir = self._paths["output_dir"]
        ExpansionExporter.export_all(output_dir, result)
        result["export_validation"] = validator.validate_exports(output_dir, EXPORT_FILES)
        ExpansionExporter.print_summary(result)
        return result

    @staticmethod
    def _recovered_objects_from_registry(
        registry_entries: List[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> List[dict[str, Any]]:
        inventory_by_id = snapshot.get("inventory_by_id") or {}
        objects: List[dict[str, Any]] = []
        for entry in registry_entries:
            discovery_id = str(entry.get("discovery_id") or "")
            inventory = inventory_by_id.get(discovery_id, {})
            objects.append(
                {
                    "recovered_object_id": entry.get("recovered_object_id"),
                    "recovery_id": entry.get("recovery_id"),
                    "source_discovery_id": discovery_id,
                    "beam": entry.get("beam_id"),
                    "role": inventory.get("role"),
                    "diameter_mm": inventory.get("diameter_mm"),
                    "quantity": inventory.get("quantity"),
                    "specification_id": entry.get("specification_id"),
                    "context_id": entry.get("context_id"),
                    "recovery_source": "Phase J.2",
                    "recovery_confidence": entry.get("confidence"),
                    "recovery_version": "5.28.0",
                    "original_suppression_reason": entry.get("original_rejection_reason"),
                    "recovery_justification": entry.get("recovery_reason"),
                    "expansion_class": entry.get("expansion_class"),
                }
            )
        return objects
