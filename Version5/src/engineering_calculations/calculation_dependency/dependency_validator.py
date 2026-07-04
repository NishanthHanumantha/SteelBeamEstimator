"""Validate calculation dependency graph — Phase I.4.6."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_dependency.dependency_builder import (
    calculation_dependency_applied,
)
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_dependency.dependency_types import (
    ALL_DEPENDENCY_CATEGORIES,
    CATEGORY_CUT_LENGTH,
    CATEGORY_DEVELOPMENT_LENGTH,
    CATEGORY_HOOK_LENGTH,
    CATEGORY_LAP_LENGTH,
    DEPENDENCY_NODE_SPECS,
    NAMESPACE_CALCULATION_DEPENDENCY,
)


class CalculationDependencyValidator:
    """Verify calculation dependency graph integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not calculation_dependency_applied(model) and not model.get("calculation_dependency_graph"):
            return {
                "phase": "Phase I.4.6",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "calculation dependency graph not applied"},
            }

        graph = model.get("calculation_dependency_graph", {})
        registry = model.get("calculation_dependency_registry", {})
        nodes = graph.get("nodes", {})

        checks: List[dict[str, Any]] = []
        checks.append(self._check_graph_exists(graph))
        checks.append(self._check_registry_exists(registry))
        checks.append(self._check_metadata_only(graph))
        checks.append(self._check_no_circular_dependencies(graph))
        checks.append(self._check_unique_sequence(nodes))
        checks.append(self._check_dependency_integrity(nodes))
        checks.append(self._check_all_categories_exist(nodes))
        checks.append(self._check_future_categories_reserved(nodes))
        checks.append(self._check_deterministic_ordering(graph))
        checks.append(self._check_registry_integrity(registry, graph))
        checks.append(self._check_export_integrity(graph, registry))
        checks.append(self._check_graph_reproducibility())
        checks.append(self._check_builder_idempotence(graph))
        checks.append(self._check_no_execution_logic(nodes))
        checks.append(self._check_no_orchestration_logic(nodes))
        checks.append(self._check_no_state_mutation_fields(nodes))
        checks.append(self._check_no_result_mutation_fields(nodes))
        checks.append(self._check_development_length_no_dependencies(nodes))
        checks.append(self._check_hook_length_no_dependencies(nodes))
        checks.append(self._check_lap_length_depends_on_development_length(nodes))
        checks.append(self._check_cut_length_depends_on_prerequisites(nodes))
        checks.append(self._check_sequence_monotonic(nodes))
        checks.append(self._check_calculation_type_mapping(nodes))
        checks.append(self._check_index_category_mapping(nodes))
        checks.append(self._check_topological_order_valid(graph))
        checks.append(self._check_node_count_matches_spec(nodes))
        checks.append(self._check_graph_id_deterministic(graph))
        checks.append(self._check_lap_before_cut_sequence(nodes))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.4.6",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "node_count": len(nodes),
            },
        }

    @staticmethod
    def _check_graph_exists(graph: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Dependency Graph Exists",
            "status": "PASS" if graph.get("nodes") else "FAIL",
        }

    @staticmethod
    def _check_registry_exists(registry: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Dependency Registry Exists",
            "status": "PASS" if registry.get("registry_id") else "FAIL",
        }

    @staticmethod
    def _check_metadata_only(graph: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Graph Is Metadata Only",
            "status": "PASS" if graph.get("metadata_only") is True else "FAIL",
        }

    @staticmethod
    def _check_no_circular_dependencies(graph: dict[str, Any]) -> dict[str, Any]:
        rebuilt = CalculationDependencyGraph.from_spec()
        return {
            "name": "No Circular Dependencies",
            "status": "PASS" if not rebuilt.has_cycle() else "FAIL",
        }

    @staticmethod
    def _check_unique_sequence(nodes: dict[str, Any]) -> dict[str, Any]:
        sequences = [int(node.get("sequence", 0)) for node in nodes.values()]
        return {
            "name": "Unique Sequence Numbers",
            "status": "PASS" if len(sequences) == len(set(sequences)) else "FAIL",
        }

    @staticmethod
    def _check_dependency_integrity(nodes: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for category, node in nodes.items():
            for dependency in node.get("depends_on", []):
                if dependency not in nodes:
                    invalid.append(f"{category}->{dependency}")
        return {
            "name": "Dependency Integrity",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_all_categories_exist(nodes: dict[str, Any]) -> dict[str, Any]:
        missing = sorted(ALL_DEPENDENCY_CATEGORIES - set(nodes.keys()))
        return {
            "name": "All Categories Exist",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }

    @staticmethod
    def _check_future_categories_reserved(nodes: dict[str, Any]) -> dict[str, Any]:
        future = {
            CATEGORY_CUT_LENGTH,
            "SHAPE_CODE",
            "BAR_IDENTITY",
            "BAR_GROUP",
            "BBS",
            "STEEL_WEIGHT",
            "BEAM_SUMMARY",
            "QUANTITY",
            "BOQ",
        }
        missing = sorted(future - set(nodes.keys()))
        return {
            "name": "Future Categories Reserved",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }

    @staticmethod
    def _check_deterministic_ordering(graph: dict[str, Any]) -> dict[str, Any]:
        ordered = graph.get("ordered_categories", [])
        expected = CalculationDependencyGraph.from_spec().ordered_categories()
        return {
            "name": "Deterministic Ordering",
            "status": "PASS" if ordered == expected else "FAIL",
        }

    @staticmethod
    def _check_registry_integrity(registry: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_CALCULATION_DEPENDENCY
            and registry.get("node_count") == len(graph.get("nodes", {}))
            and registry.get("graph_id") == graph.get("graph_id")
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if ok else "FAIL",
        }

    @staticmethod
    def _check_export_integrity(graph: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
        ok = bool(graph.get("graph_id")) and bool(registry.get("registry_id"))
        return {
            "name": "Export Integrity",
            "status": "PASS" if ok else "FAIL",
        }

    @staticmethod
    def _check_graph_reproducibility() -> dict[str, Any]:
        first = CalculationDependencyGraph.from_spec().to_dict()
        second = CalculationDependencyGraph.from_spec().to_dict()
        return {
            "name": "Graph Reproducibility",
            "status": "PASS" if first == second else "FAIL",
        }

    @staticmethod
    def _check_builder_idempotence(graph: dict[str, Any]) -> dict[str, Any]:
        rebuilt = CalculationDependencyGraph.from_spec().to_dict()
        return {
            "name": "Builder Idempotence",
            "status": "PASS" if graph == rebuilt else "FAIL",
        }

    @staticmethod
    def _check_no_execution_logic(nodes: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"execute", "run", "engine", "orchestrate"}
        violations = []
        for category, node in nodes.items():
            for key in node.keys():
                if key.lower() in forbidden:
                    violations.append(f"{category}.{key}")
        return {
            "name": "No Execution Logic",
            "status": "PASS" if not violations else "FAIL",
        }

    @staticmethod
    def _check_no_orchestration_logic(nodes: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"orchestration", "pipeline", "scheduler"}
        violations = []
        for category, node in nodes.items():
            for key in node.keys():
                if key.lower() in forbidden:
                    violations.append(f"{category}.{key}")
        return {
            "name": "No Orchestration Logic",
            "status": "PASS" if not violations else "FAIL",
        }

    @staticmethod
    def _check_no_state_mutation_fields(nodes: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"mutate_state", "update_state", "calculation_state"}
        violations = []
        for category, node in nodes.items():
            for key in node.keys():
                if key.lower() in forbidden:
                    violations.append(f"{category}.{key}")
        return {
            "name": "No State Mutation Fields",
            "status": "PASS" if not violations else "FAIL",
        }

    @staticmethod
    def _check_no_result_mutation_fields(nodes: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"result_value", "modify_result", "mutate_result"}
        violations = []
        for category, node in nodes.items():
            for key in node.keys():
                if key.lower() in forbidden:
                    violations.append(f"{category}.{key}")
        return {
            "name": "No Result Mutation Fields",
            "status": "PASS" if not violations else "FAIL",
        }

    @staticmethod
    def _check_development_length_no_dependencies(nodes: dict[str, Any]) -> dict[str, Any]:
        node = nodes.get(CATEGORY_DEVELOPMENT_LENGTH, {})
        return {
            "name": "Development Length Has No Dependencies",
            "status": "PASS" if not node.get("depends_on") else "FAIL",
        }

    @staticmethod
    def _check_hook_length_no_dependencies(nodes: dict[str, Any]) -> dict[str, Any]:
        node = nodes.get(CATEGORY_HOOK_LENGTH, {})
        return {
            "name": "Hook Length Has No Dependencies",
            "status": "PASS" if not node.get("depends_on") else "FAIL",
        }

    @staticmethod
    def _check_lap_length_depends_on_development_length(nodes: dict[str, Any]) -> dict[str, Any]:
        node = nodes.get(CATEGORY_LAP_LENGTH, {})
        deps = list(node.get("depends_on", []))
        return {
            "name": "Lap Length Depends On Development Length",
            "status": "PASS" if deps == [CATEGORY_DEVELOPMENT_LENGTH] else "FAIL",
        }

    @staticmethod
    def _check_cut_length_depends_on_prerequisites(nodes: dict[str, Any]) -> dict[str, Any]:
        node = nodes.get(CATEGORY_CUT_LENGTH, {})
        expected = [
            CATEGORY_DEVELOPMENT_LENGTH,
            CATEGORY_HOOK_LENGTH,
            CATEGORY_LAP_LENGTH,
        ]
        return {
            "name": "Cut Length Depends On Prerequisites",
            "status": "PASS" if list(node.get("depends_on", [])) == expected else "FAIL",
        }

    @staticmethod
    def _check_sequence_monotonic(nodes: dict[str, Any]) -> dict[str, Any]:
        sequences = sorted(int(node.get("sequence", 0)) for node in nodes.values())
        return {
            "name": "Sequence Monotonic",
            "status": "PASS" if sequences == list(range(1, len(sequences) + 1)) else "FAIL",
        }

    @staticmethod
    def _check_calculation_type_mapping(nodes: dict[str, Any]) -> dict[str, Any]:
        mismatches = []
        for category, spec in DEPENDENCY_NODE_SPECS.items():
            node = nodes.get(category, {})
            if node.get("calculation_type") != spec["calculation_type"]:
                mismatches.append(category)
        return {
            "name": "Calculation Type Mapping",
            "status": "PASS" if not mismatches else "FAIL",
        }

    @staticmethod
    def _check_index_category_mapping(nodes: dict[str, Any]) -> dict[str, Any]:
        mismatches = []
        for category, spec in DEPENDENCY_NODE_SPECS.items():
            node = nodes.get(category, {})
            if node.get("index_category") != spec["index_category"]:
                mismatches.append(category)
        return {
            "name": "Index Category Mapping",
            "status": "PASS" if not mismatches else "FAIL",
        }

    @staticmethod
    def _check_topological_order_valid(graph: dict[str, Any]) -> dict[str, Any]:
        ordered = graph.get("ordered_categories", [])
        position = {category: index for index, category in enumerate(ordered)}
        violations = []
        for category in ordered:
            node = graph.get("nodes", {}).get(category, {})
            for dependency in node.get("depends_on", []):
                if position.get(dependency, -1) >= position.get(category, 0):
                    violations.append(f"{dependency}->{category}")
        return {
            "name": "Topological Order Valid",
            "status": "PASS" if not violations else "FAIL",
        }

    @staticmethod
    def _check_node_count_matches_spec(nodes: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Node Count Matches Spec",
            "status": "PASS" if len(nodes) == len(DEPENDENCY_NODE_SPECS) else "FAIL",
        }

    @staticmethod
    def _check_graph_id_deterministic(graph: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Graph Id Deterministic",
            "status": "PASS" if graph.get("graph_id") == "CALC_DEPENDENCY_GRAPH" else "FAIL",
        }

    @staticmethod
    def _check_lap_before_cut_sequence(nodes: dict[str, Any]) -> dict[str, Any]:
        lap_seq = int(nodes.get(CATEGORY_LAP_LENGTH, {}).get("sequence", 0))
        cut_seq = int(nodes.get(CATEGORY_CUT_LENGTH, {}).get("sequence", 0))
        return {
            "name": "Lap Before Cut Sequence",
            "status": "PASS" if lap_seq < cut_seq else "FAIL",
        }
