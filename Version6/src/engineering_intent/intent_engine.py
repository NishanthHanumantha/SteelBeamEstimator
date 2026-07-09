"""Engineering Intent Reconstruction orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.engineering_intent.anchorage_engine import AnchorageEngine
from src.engineering_intent.continuity_engine import ContinuityEngine
from src.engineering_intent.curtailment_engine import CurtailmentEngine
from src.engineering_intent.development_length_engine import DevelopmentLengthEngine
from src.engineering_intent.engineering_context import EngineeringContext
from src.engineering_intent.export import EXPORT_FILES, IntentExporter
from src.engineering_intent.hook_engine import HookEngine
from src.engineering_intent.intent_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    IntentCollector,
    default_paths,
)
from src.engineering_intent.intent_rules import EngineeringIntentType
from src.engineering_intent.intent_validator import IntentValidator
from src.engineering_intent.production_integrator import ProductionIntegrator
from src.engineering_intent.reconstruction_builder import ReconstructionBuilder
from src.engineering_intent.reporting import IntentReporting
from src.engineering_intent.statistics import IntentStatistics
from src.engineering_intent.validation import IntentValidation


class IntentEngine:
    """Run deterministic engineering intent reconstruction."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = IntentCollector(self._project_root).collect()
        context_builder = EngineeringContext(snapshot)
        engines = [
            DevelopmentLengthEngine(),
            AnchorageEngine(),
            HookEngine(),
            ContinuityEngine(),
            CurtailmentEngine(),
        ]

        candidates: List[dict[str, Any]] = []
        for bar in snapshot.get("native_bars") or []:
            context = context_builder.build_for_bar(bar)
            for engine in engines:
                candidates.extend(engine.evaluate(context, snapshot))
            candidates.extend(self._evaluate_support_bar(context, snapshot))
            candidates.extend(self._evaluate_termination(context, snapshot))

        validator = IntentValidator()
        eligibility = validator.validate_all(candidates)
        eligibility_by_key = {str(item.get("intent_key")): item for item in eligibility}

        decisions: List[dict[str, Any]] = []
        for candidate in candidates:
            eligibility_result = eligibility_by_key.get(str(candidate.get("intent_key")), {})
            decisions.append(
                {
                    "intent_key": candidate.get("intent_key"),
                    "intent_type": candidate.get("intent_type"),
                    "source_bar_id": candidate.get("source_bar_id"),
                    "decision": eligibility_result.get("decision", "REJECT"),
                    "eligible": eligibility_result.get("eligible", False),
                    "checks": eligibility_result.get("checks", []),
                    "engineering_rule": candidate.get("engineering_rule"),
                    "engineering_justification": candidate.get("engineering_justification"),
                }
            )

        approved_candidates = [
            candidate
            for candidate in candidates
            if eligibility_by_key.get(str(candidate.get("intent_key")), {}).get("decision") == "APPROVE"
        ]
        approved_candidates = [
            candidate
            for candidate in approved_candidates
            if str(candidate.get("intent_key")) not in snapshot.get("existing_intent_ids", set())
        ]

        existing_registry = list(snapshot.get("intent_registry_entries") or [])
        intent_objects: List[dict[str, Any]] = []
        traceability: List[dict[str, Any]] = []
        normalized_bars: List[dict[str, Any]] = []
        normalized_groups: List[dict[str, Any]] = []
        registry_entries = list(existing_registry)
        production_integration: dict[str, Any] = {"status": "SKIPPED", "reason": "No approved intent reconstructions"}

        if approved_candidates:
            builder = ReconstructionBuilder(dict(snapshot.get("id_counters") or {}))
            built = builder.build_all(
                approved_candidates,
                snapshot.get("contexts_by_beam") or {},
                snapshot.get("project_workspace") or {},
            )
            normalized_bars, normalized_groups, registry = builder.normalize_reconstructed(
                built.get("specifications") or [],
                built.get("contexts") or [],
            )
            built["registry"] = registry
            new_entries = ReconstructionBuilder.patch_registry_bar_ids(
                built.get("registry_entries") or [],
                normalized_bars,
            )
            registry_entries = existing_registry + new_entries
            intent_objects = built.get("intent_objects") or []
            traceability = built.get("intent_traces") or []
            production_integration = ProductionIntegrator(self._project_root).integrate(
                snapshot,
                built,
                normalized_bars,
                normalized_groups,
            )
        elif existing_registry:
            intent_objects = self._objects_from_registry(existing_registry, snapshot)
            traceability = self._traceability_from_registry(existing_registry)
            production_integration = ProductionIntegrator(self._project_root).integrate(
                snapshot, {}, [], []
            )

        statistics = IntentStatistics.build(
            candidates,
            decisions,
            intent_objects,
            normalized_bars,
            snapshot,
        )
        health = IntentStatistics.build_health(statistics)
        recommendations = IntentReporting.build_recommendations(candidates, decisions)

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "load_status": snapshot.get("load_status"),
            "candidates": candidates,
            "decisions": decisions,
            "intent_objects": intent_objects,
            "intent_registry": {
                "registry_count": len(registry_entries),
                "entries": registry_entries,
            },
            "traceability": traceability,
            "statistics": statistics,
            "health": health,
            "production_integration": production_integration,
            "normalized_bars": normalized_bars,
            "recommendations": recommendations,
        }

        output_dir = self._paths["output_dir"]
        export_validation = IntentExporter.validate_exports(
            output_dir,
            tuple(name for name in EXPORT_FILES if name != "engineering_intent_validation.json"),
        )
        validation = IntentValidation().validate(result, snapshot, export_validation)
        result["validation"] = validation
        result["summary"] = IntentStatistics.build_summary(statistics, health, validation.get("status", "FAIL"))
        IntentExporter.export_all(output_dir, result)
        export_validation = IntentExporter.validate_exports(output_dir, EXPORT_FILES)
        result["export_validation"] = export_validation
        validation = IntentValidation().validate(result, snapshot, export_validation)
        result["validation"] = validation
        result["summary"] = IntentStatistics.build_summary(statistics, health, validation.get("status", "FAIL"))
        IntentExporter._write_validation_bundle(output_dir, result)
        IntentExporter.print_summary(result)
        return result

    @staticmethod
    def _evaluate_support_bar(context: dict[str, Any], snapshot: dict[str, Any]) -> List[dict[str, Any]]:
        if not context.get("support_refs"):
            return []
        if context.get("calculation_status") != "COMPLETE":
            return []
        intent_key = f"{context.get('bar_id')}::{EngineeringIntentType.SUPPLEMENTARY_SUPPORT_BAR.value}::SUPPORT"
        if intent_key in snapshot.get("existing_intent_ids", set()):
            return []
        return [
            {
                "intent_key": intent_key,
                "intent_type": EngineeringIntentType.SUPPLEMENTARY_SUPPORT_BAR.value,
                "rule_id": "K.1.RULE.SUPPORT_BAR.001",
                "source_bar_id": context.get("bar_id"),
                "source_engineering_object_id": context.get("engineering_object_id"),
                "beam_id": context.get("beam_id"),
                "support_zone": "SUPPORT",
                "support_reference": (context.get("support_refs") or ["UNKNOWN"])[0],
                "general_note_id": "KNOWLEDGE::GENERAL_NOTES",
                "engineering_rule": "K.1.RULE.SUPPORT_BAR.001",
                "geometry_reference": context.get("geometry_reference"),
                "engineering_graph_node": context.get("engineering_graph_node"),
                "calculation_context_id": context.get("calculation_context_id"),
                "evidence_confidence": 100.0,
                "engineering_justification": (
                    f"Support zone for beam {context.get('beam_id')} implies supplementary "
                    f"support reinforcement for bar {context.get('bar_id')}."
                ),
                "reconstruct": True,
                "context": context,
            }
        ]

    @staticmethod
    def _evaluate_termination(context: dict[str, Any], snapshot: dict[str, Any]) -> List[dict[str, Any]]:
        if not context.get("development_length_mm"):
            return []
        if not context.get("support_refs"):
            return []
        if context.get("calculation_status") != "COMPLETE":
            return []
        candidates: List[dict[str, Any]] = []
        for support_zone in context.get("support_zones") or []:
            intent_key = f"{context.get('bar_id')}::{EngineeringIntentType.SUPPLEMENTARY_TERMINATION.value}::{support_zone}"
            if intent_key in snapshot.get("existing_intent_ids", set()):
                continue
            candidates.append(
                {
                    "intent_key": intent_key,
                    "intent_type": EngineeringIntentType.SUPPLEMENTARY_TERMINATION.value,
                    "rule_id": "K.1.RULE.TERMINATION.001",
                    "source_bar_id": context.get("bar_id"),
                    "source_engineering_object_id": context.get("engineering_object_id"),
                    "beam_id": context.get("beam_id"),
                    "support_zone": support_zone,
                    "support_reference": (context.get("support_refs") or ["UNKNOWN"])[
                        0 if support_zone == "LEFT_SUPPORT" else -1
                    ],
                    "development_length_mm": context.get("development_length_mm"),
                    "development_length_rule": context.get("development_length_rule"),
                    "general_note_id": "RULE::PROJECT#structural_detailing_rules.anchorage_rules",
                    "engineering_rule": "K.1.RULE.TERMINATION.001",
                    "geometry_reference": context.get("geometry_reference"),
                    "engineering_graph_node": context.get("engineering_graph_node"),
                    "calculation_context_id": context.get("calculation_context_id"),
                    "evidence_confidence": 100.0,
                    "engineering_justification": (
                        f"Bar {context.get('bar_id')} termination at {support_zone} requires "
                        f"explicit termination reinforcement per anchorage rules."
                    ),
                    "reconstruct": True,
                    "context": context,
                }
            )
        return candidates

    @staticmethod
    def _objects_from_registry(
        registry_entries: List[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> List[dict[str, Any]]:
        bars_by_intent = {}
        for bar in snapshot.get("intent_bars") or []:
            trace = bar.get("traceability") or {}
            intent_id = trace.get("intent_id")
            if intent_id:
                bars_by_intent[str(intent_id)] = bar
        objects = []
        for entry in registry_entries:
            objects.append(
                {
                    "intent_id": entry.get("intent_id"),
                    "intent_key": entry.get("intent_key"),
                    "intent_type": entry.get("intent_type"),
                    "reconstructed_object_id": entry.get("reconstructed_object_id"),
                    "source_bar_id": entry.get("source_bar_id"),
                    "source_engineering_object_id": entry.get("source_engineering_object_id"),
                    "beam_id": entry.get("beam_id"),
                    "specification_id": entry.get("specification_id"),
                    "context_id": entry.get("context_id"),
                    "normalized_bar_id": entry.get("normalized_bar_id")
                    or (bars_by_intent.get(str(entry.get("intent_id"))) or {}).get("bar_id"),
                    "intent_source": "Phase K.1",
                    "intent_version": "6.0.0",
                    "evidence": {
                        "intent_id": entry.get("intent_id"),
                        "source_engineering_object_id": entry.get("source_engineering_object_id"),
                        "source_bar_id": entry.get("source_bar_id"),
                        "beam_id": entry.get("beam_id"),
                        "general_note_id": entry.get("general_note_id"),
                        "engineering_rule": entry.get("engineering_rule"),
                        "evidence_confidence": entry.get("evidence_confidence", 100.0),
                        "intent_category": entry.get("intent_type"),
                        "engineering_justification": entry.get("engineering_justification")
                        or f"Intent {entry.get('intent_type')} reconstructed from {entry.get('source_bar_id')}",
                    },
                    "engineering_justification": entry.get("engineering_justification")
                    or f"Intent {entry.get('intent_type')} reconstructed from {entry.get('source_bar_id')}",
                }
            )
        return objects

    @staticmethod
    def _traceability_from_registry(registry_entries: List[dict[str, Any]]) -> List[dict[str, Any]]:
        return [
            {
                "intent_id": entry.get("intent_id"),
                "intent_key": entry.get("intent_key"),
                "source_bar_id": entry.get("source_bar_id"),
                "source_engineering_object_id": entry.get("source_engineering_object_id"),
                "engineering_rule": entry.get("engineering_rule"),
                "general_note_id": entry.get("general_note_id"),
                "beam_id": entry.get("beam_id"),
                "reconstructed_object_id": entry.get("reconstructed_object_id"),
            }
            for entry in registry_entries
        ]
