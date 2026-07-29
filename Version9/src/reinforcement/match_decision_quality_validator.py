"""Validate Phase G.2.7 match decision quality and versioning."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.beam_match import beam_matching_applied
from src.reinforcement.detail_identity import MATCHING_STATUS_NOT_MATCHED
from src.reinforcement.match_decision_quality import (
    ALGORITHM_VERSION,
    SHARED_ALGORITHM_ID,
    DecisionConfidenceLevel,
    confidence_level_from_value,
)


class MatchDecisionQualityValidator:
    """Verify decision quality metadata without beam matching or ownership."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        drawing_models = model.get("reinforcement_drawing_models", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_confidence_level_present(drawing_models))
        checks.append(self._check_confidence_level_thresholds(drawing_models))
        checks.append(self._check_algorithm_version_exists(drawing_models))
        checks.append(self._check_algorithm_node_unique(model))
        checks.append(self._check_registry_complete(model, drawing_models))
        checks.append(self._check_drawing_set_updated(model))
        checks.append(self._check_workspace_updated(model))
        checks.append(self._check_graph_relationships(model))
        checks.append(self._check_no_beam_matching(model, drawing_models))
        checks.append(self._check_no_ownership(drawing_models))
        checks.append(self._check_no_engineering_objects(model))
        checks.append(self._check_no_parsing(model))
        checks.append(self._check_no_quantities(model))
        checks.append(self._check_no_beam_context_modification(model))
        checks.append(self._check_backward_compatibility(drawing_models))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.2.7",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "decision_count": sum(
                    dm.get("match_decision_count", 0) for dm in drawing_models
                ),
            },
        }

    def _check_confidence_level_present(self, drawing_models: list) -> dict[str, Any]:
        missing = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                if "confidence_level" not in decision:
                    missing.append(decision.get("decision_id"))
                if "decision_quality" not in decision or "algorithm_info" not in decision:
                    missing.append(decision.get("decision_id"))
        return {
            "name": "Every MatchDecision Has confidence_level",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }

    def _check_confidence_level_thresholds(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                conf = decision.get("confidence")
                expected = confidence_level_from_value(
                    float(conf) if conf is not None else None
                )
                if decision.get("confidence_level") != expected:
                    invalid.append(decision.get("decision_id"))
        return {
            "name": "confidence_level Matches Thresholds",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_algorithm_version_exists(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                info = decision.get("algorithm_info", {})
                if info.get("algorithm_version") != ALGORITHM_VERSION:
                    invalid.append(decision.get("decision_id"))
        return {
            "name": "Algorithm Version Exists",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_algorithm_node_unique(self, model: dict[str, Any]) -> dict[str, Any]:
        algo_export = model.get("decision_algorithm", {})
        algorithms = algo_export.get("algorithms", [])
        ids = [a.get("id") for a in algorithms]
        unique = len(ids) == 1 and ids[0] == SHARED_ALGORITHM_ID
        graph = model.get("project_engineering_graph", {})
        algo_nodes = [n for n in graph.get("nodes", []) if n.get("type") == "MATCH_ALGORITHM"]
        ok = unique and len(algo_nodes) == 1
        return {
            "name": "Algorithm Node Unique",
            "status": "PASS" if ok else "FAIL",
            "algorithm_count": len(algorithms),
            "graph_algorithm_nodes": len(algo_nodes),
        }

    def _check_registry_complete(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        registry = model.get("match_decision_quality_registry", {})
        expected = sum(dm.get("match_decision_count", 0) for dm in drawing_models)
        actual = registry.get("decision_count", 0)
        return {
            "name": "Quality Registry Complete",
            "status": "PASS" if expected > 0 and actual == expected else "FAIL",
            "expected": expected,
            "actual": actual,
        }

    def _check_drawing_set_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for ds in model.get("drawing_sets", []):
            if ds.get("decision_algorithm_version") != ALGORITHM_VERSION:
                invalid.append(ds.get("drawing_set_id"))
            if not ds.get("decision_quality_summary"):
                invalid.append(ds.get("drawing_set_id"))
        return {
            "name": "DrawingSet Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_workspace_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        project = model.get("project_workspace", {})
        if project.get("decision_algorithm_version") != ALGORITHM_VERSION:
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "project"}
        if not project.get("decision_quality_summary"):
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "summary"}
        return {"name": "Workspace Updated", "status": "PASS"}

    def _check_graph_relationships(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("project_engineering_graph", {})
        quality_nodes = [n for n in graph.get("nodes", []) if n.get("type") == "DECISION_QUALITY"]
        has_quality = any(
            e.get("relationship") == "HAS_QUALITY" for e in graph.get("edges", [])
        )
        has_generated = any(
            e.get("relationship") == "GENERATED_BY" for e in graph.get("edges", [])
        )
        ok = len(quality_nodes) > 0 and has_quality and has_generated
        return {
            "name": "Graph Quality Relationships Valid",
            "status": "PASS" if ok else "FAIL",
            "quality_nodes": len(quality_nodes),
            "has_quality_edge": has_quality,
            "has_generated_by_edge": has_generated,
        }

    def _check_no_beam_matching(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        if beam_matching_applied(model):
            return {"name": "No Beam Matching", "status": "PASS", "skipped": "beam_matching_applied"}
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if ident.get("matching_status") != MATCHING_STATUS_NOT_MATCHED:
                    return {"name": "No Beam Matching", "status": "FAIL"}
        return {"name": "No Beam Matching", "status": "PASS"}

    def _check_no_ownership(self, drawing_models: list) -> dict[str, Any]:
        for dm in drawing_models:
            for rel in dm.get("quality_relationships", []):
                if "OWN" in str(rel.get("relationship", "")).upper():
                    return {"name": "No Ownership", "status": "FAIL"}
        return {"name": "No Ownership", "status": "PASS"}

    def _check_no_engineering_objects(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("engineering_objects",) if k in model]
        return {
            "name": "No Engineering Objects",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_parsing(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("parsed_bars", "bar_schedule") if k in model]
        return {
            "name": "No Reinforcement Parsing",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_quantities(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("quantities", "steel_weight", "boq") if k in model]
        return {
            "name": "No Quantity Computation",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_beam_context_modification(self, model: dict[str, Any]) -> dict[str, Any]:
        if beam_matching_applied(model):
            return {
                "name": "No BeamContext Modification",
                "status": "PASS",
                "skipped": "beam_matching_applied",
            }
        invalid = []
        for ctx in model.get("beam_engineering_contexts", []):
            if ctx.get("reinforcement_context_id"):
                invalid.append(ctx.get("context_id"))
        return {
            "name": "No BeamContext Modification",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_backward_compatibility(self, drawing_models: list) -> dict[str, Any]:
        required = (
            "decision_id",
            "decision_status",
            "decision_reason",
            "confidence",
            "requires_manual_review",
        )
        missing = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                for field in required:
                    if field not in decision:
                        missing.append(decision.get("decision_id"))
        return {
            "name": "Backward Compatibility Maintained",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }
