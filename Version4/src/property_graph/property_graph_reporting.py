"""Property graph reporting consistency — Phase G.5.2.1."""

from __future__ import annotations

from typing import Any, List

from src.property_graph.property_graph_summary import PropertyGraphSummary


class PropertyGraphReporting:
    """Single source of truth for property graph validation reporting."""

    @staticmethod
    def validation_snapshot(validation: dict[str, Any]) -> dict[str, Any]:
        summary = validation.get("summary", {})
        return {
            "status": validation.get("status", "SKIP"),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "total_checks": summary.get("total_checks", 0),
        }

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        """Attach final validation and rebuild summary from the same result."""
        model["property_validation"] = validation
        contexts = model.get("engineering_reinforcement_contexts", [])
        objects = model.get("engineering_objects", [])
        candidates = model.get("property_candidates", [])
        registry = model.get("property_registry", {})
        graph = model.get("property_graph", {})
        model["property_summary"] = PropertyGraphSummary.build(
            contexts,
            objects,
            candidates,
            registry,
            graph,
            validation,
        )

    @staticmethod
    def merge_reporting_checks(
        validation: dict[str, Any],
        reporting: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(validation)
        merged["reporting_consistency"] = reporting
        if reporting.get("status") == "FAIL":
            merged["status"] = "FAIL"
            base_summary = dict(merged.get("summary", {}))
            reporting_summary = reporting.get("summary", {})
            base_summary["failed"] = base_summary.get("failed", 0) + reporting_summary.get(
                "failed", 0
            )
            base_summary["passed"] = base_summary.get("passed", 0) + reporting_summary.get(
                "passed", 0
            )
            base_summary["total_checks"] = base_summary.get(
                "total_checks", 0
            ) + reporting_summary.get("total_checks", 0)
            merged["summary"] = base_summary
        return merged


class PropertyGraphReportingConsistencyValidator:
    """Verify exported property graph reports are internally consistent."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        validation = model.get("property_validation", {})
        summary = model.get("property_summary", {})
        registry = model.get("property_registry", {})
        candidates = model.get("property_candidates", [])
        graph = model.get("property_graph", {})

        checks: List[dict[str, Any]] = []
        checks.append(self._check_summary_status_matches(validation, summary))
        checks.append(self._check_passed_counts_match(validation, summary))
        checks.append(self._check_failed_counts_match(validation, summary))
        checks.append(self._check_candidate_count_matches(summary, registry, candidates))
        checks.append(self._check_registry_count_matches(summary, registry))
        checks.append(self._check_graph_statistics_match(summary, graph))
        checks.append(self._check_export_consistency(model, validation, summary))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.5.2.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
            },
        }

    @staticmethod
    def _validation_result(summary: dict[str, Any]) -> dict[str, Any]:
        return summary.get("validation_result", {})

    def _check_summary_status_matches(
        self,
        validation: dict[str, Any],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        val_status = validation.get("status", "SKIP")
        sum_status = self._validation_result(summary).get("status", "SKIP")
        ok = val_status == sum_status
        return {
            "name": "Summary Status Matches Validator",
            "status": "PASS" if ok else "FAIL",
            "validator_status": val_status,
            "summary_status": sum_status,
            "inconsistent_file": None if ok else "property_summary.json",
        }

    def _check_passed_counts_match(
        self,
        validation: dict[str, Any],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        val_passed = validation.get("summary", {}).get("passed", 0)
        sum_passed = self._validation_result(summary).get("passed", 0)
        ok = val_passed == sum_passed
        return {
            "name": "Passed Counts Identical",
            "status": "PASS" if ok else "FAIL",
            "validator_passed": val_passed,
            "summary_passed": sum_passed,
            "inconsistent_file": None if ok else "property_summary.json",
        }

    def _check_failed_counts_match(
        self,
        validation: dict[str, Any],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        val_failed = validation.get("summary", {}).get("failed", 0)
        sum_failed = self._validation_result(summary).get("failed", 0)
        ok = val_failed == sum_failed
        return {
            "name": "Failed Counts Identical",
            "status": "PASS" if ok else "FAIL",
            "validator_failed": val_failed,
            "summary_failed": sum_failed,
            "inconsistent_file": None if ok else "property_summary.json",
        }

    @staticmethod
    def _check_candidate_count_matches(
        summary: dict[str, Any],
        registry: dict[str, Any],
        candidates: list,
    ) -> dict[str, Any]:
        summary_count = summary.get("total_candidates", 0)
        registry_count = registry.get("candidate_count", 0)
        list_count = len(candidates)
        ok = summary_count == registry_count == list_count
        inconsistent = []
        if summary_count != registry_count:
            inconsistent.append("property_summary.json vs property_registry.json")
        if summary_count != list_count:
            inconsistent.append("property_summary.json vs property_candidates.json")
        return {
            "name": "Candidate Counts Identical",
            "status": "PASS" if ok else "FAIL",
            "summary_count": summary_count,
            "registry_count": registry_count,
            "candidate_list_count": list_count,
            "inconsistent_files": inconsistent,
        }

    @staticmethod
    def _check_registry_count_matches(
        summary: dict[str, Any],
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        summary_erc = summary.get("registry_counts", {}).get("erc_registry_count", 0)
        registry_erc = len(registry.get("erc_registries", []))
        ok = summary_erc == registry_erc
        return {
            "name": "Registry Counts Identical",
            "status": "PASS" if ok else "FAIL",
            "summary_erc_count": summary_erc,
            "registry_erc_count": registry_erc,
            "inconsistent_file": None if ok else "property_registry.json",
        }

    @staticmethod
    def _check_graph_statistics_match(
        summary: dict[str, Any],
        graph: dict[str, Any],
    ) -> dict[str, Any]:
        ok = (
            summary.get("graph_nodes", 0) == graph.get("node_count", 0)
            and summary.get("graph_edges", 0) == graph.get("edge_count", 0)
        )
        return {
            "name": "Graph Statistics Identical",
            "status": "PASS" if ok else "FAIL",
            "summary_nodes": summary.get("graph_nodes", 0),
            "graph_nodes": graph.get("node_count", 0),
            "summary_edges": summary.get("graph_edges", 0),
            "graph_edges": graph.get("edge_count", 0),
            "inconsistent_file": None if ok else "property_graph.json",
        }

    @staticmethod
    def _check_export_consistency(
        model: dict[str, Any],
        validation: dict[str, Any],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        snapshot = PropertyGraphReporting.validation_snapshot(validation)
        embedded = summary.get("validation_result", {})
        ok = snapshot == embedded
        missing = []
        if not model.get("property_candidates"):
            missing.append("property_candidates")
        if not model.get("property_registry"):
            missing.append("property_registry")
        if not model.get("property_graph"):
            missing.append("property_graph")
        if not model.get("property_summary"):
            missing.append("property_summary")
        if not model.get("property_validation"):
            missing.append("property_validation")
        return {
            "name": "Export Consistency Verified",
            "status": "PASS" if ok and not missing else "FAIL",
            "validation_snapshot": snapshot,
            "summary_validation_result": embedded,
            "missing_exports": missing,
            "inconsistent_file": None if ok else "property_summary.json",
        }
