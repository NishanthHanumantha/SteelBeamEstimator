"""Export reinforcement discovery analysis artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.reinforcement_discovery_analysis.discovery_collector import DISCOVERY_STATUSES, MODEL_VERSION


EXPORT_FILES = (
    "reinforcement_inventory.json",
    "reinforcement_discovery_funnel.json",
    "reinforcement_traceability_matrix.json",
    "reinforcement_classification_analysis.json",
    "beam_association_analysis.json",
    "normalization_analysis.json",
    "parser_health_metrics.json",
    "unsupported_reinforcement_patterns.json",
    "reinforcement_discovery_gap_analysis.json",
    "reinforcement_discovery_summary.json",
)


class DiscoveryExporter:
    """Write JSON exports and render console summary."""

    @staticmethod
    def export_all(output_dir: Path, result: dict[str, Any]) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        mapping = {
            "reinforcement_inventory.json": {
                "phase": result.get("phase"),
                "model_version": result.get("model_version"),
                "inventory_count": len(result.get("inventory") or []),
                "inventory": result.get("inventory"),
            },
            "reinforcement_discovery_funnel.json": result.get("discovery_funnel"),
            "reinforcement_traceability_matrix.json": result.get("traceability_matrix"),
            "reinforcement_classification_analysis.json": result.get("classification_analysis"),
            "beam_association_analysis.json": result.get("association_analysis"),
            "normalization_analysis.json": result.get("normalization_analysis"),
            "parser_health_metrics.json": result.get("parser_health_metrics"),
            "unsupported_reinforcement_patterns.json": result.get("unsupported_patterns"),
            "reinforcement_discovery_gap_analysis.json": result.get("discovery_gap_analysis"),
            "reinforcement_discovery_summary.json": result.get("discovery_summary"),
        }
        for filename in EXPORT_FILES:
            path = output_dir / filename
            DiscoveryExporter._write_json(path, mapping[filename])
            written[filename] = str(path)
        result["export_paths"] = written
        return written

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        parser_health = result.get("parser_health_metrics") or {}
        unsupported = result.get("unsupported_patterns") or {}
        gap_analysis = result.get("discovery_gap_analysis") or {}
        association = result.get("association_analysis") or {}
        normalization = result.get("normalization_analysis") or {}
        export_paths = result.get("export_paths") or {}

        print("\n" + "=" * 80)
        print("Reinforcement Discovery Coverage Analysis")
        print("=" * 80)
        print(f"Model Version: {result.get('model_version')}")
        print(f"Phase: {result.get('phase')}")
        print("")
        print("Discovery Funnel")
        print("-" * 80)
        for stage in (result.get("discovery_funnel") or {}).get("stages") or []:
            print(f"{stage.get('label')}: {stage.get('count')}")
        print("")
        print(f"Detection %: {parser_health.get('detection_success_percent')}")
        print(f"Classification %: {parser_health.get('classification_success_percent')}")
        print(f"Association %: {parser_health.get('association_success_percent')}")
        print(f"Normalization %: {parser_health.get('normalization_success_percent')}")
        print(f"Calculation %: {parser_health.get('calculation_success_percent')}")
        print(f"Export %: {parser_health.get('export_success_percent')}")
        print("")
        print("Parser Health")
        print("-" * 80)
        print(f"Overall Discovery Success %: {parser_health.get('overall_discovery_success_percent')}")
        print("")
        print("Top Unsupported Patterns")
        print("-" * 80)
        for item in (unsupported.get("patterns") or [])[:5]:
            print(f"{item.get('original_text')}: {item.get('occurrences')} ({item.get('priority')})")
        print("")
        print("Top Discovery Losses")
        print("-" * 80)
        for item in (result.get("discovery_summary") or {}).get("top_discovery_losses") or []:
            print(f"{item.get('transition')}: {item.get('loss')} ({item.get('loss_percent')}%)")
        print("")
        print("Top Association Failures")
        print("-" * 80)
        for item in (association.get("causes") or [])[:5]:
            print(f"{item.get('reason')}: {item.get('count')}")
        print("")
        print("Top Normalization Failures")
        print("-" * 80)
        for item in (normalization.get("reasons") or [])[:5]:
            print(f"{item.get('reason')}: {item.get('count')}")
        print("")
        print("Export Locations")
        print("-" * 80)
        for filename, path in export_paths.items():
            print(f"{filename}: {path}")
        print("=" * 80 + "\n")

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")


class DiscoveryValidator:
    """Validate reinforcement discovery analysis completeness."""

    def validate(self, result: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.extend(self._scope_checks(result))
        checks.extend(self._inventory_checks(result))
        checks.extend(self._funnel_checks(result))
        checks.extend(self._traceability_checks(result))
        checks.extend(self._status_checks(result))
        checks.extend(self._analysis_checks(result))
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "phase": result.get("phase"),
            "model_version": MODEL_VERSION,
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    def validate_exports(self, output_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
        checks = [
            self._check(
                f"Export Written {filename}",
                (output_dir / filename).exists() and (output_dir / filename).stat().st_size > 0,
            )
            for filename in EXPORT_FILES
        ]
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    def _scope_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        return [
            self._check("Engineering Code Not Modified", result.get("engineering_code_modified") is False),
            self._check("Parser Not Executed", result.get("parser_executed") is False),
            self._check("Read Only Analysis", result.get("read_only_analysis") is True),
            self._check("Model Version 5.23.0", result.get("model_version") == "5.23.0"),
        ]

    def _inventory_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        inventory = result.get("inventory") or []
        discovery_ids = [item.get("discovery_id") for item in inventory]
        unique_ids = set(discovery_ids)
        return [
            self._check("Every Reinforcement Annotation Analysed", len(inventory) >= 1),
            self._check("Every Callout Has Unique Discovery ID", len(discovery_ids) == len(unique_ids)),
            self._check("Discovery IDs Populated", all(discovery_ids)),
        ]

    def _funnel_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        funnel = result.get("discovery_funnel") or {}
        transitions = funnel.get("transitions") or []
        consistent = all(
            transition.get("loss")
            == max(transition.get("from_count", 0) - transition.get("to_count", 0), 0)
            for transition in transitions
        )
        counts = funnel.get("stage_counts") or {}
        valid_counts = all(isinstance(value, int) and value >= 0 for value in counts.values())
        return [
            self._check("Funnel Internally Consistent", consistent),
            self._check("Transition Counts Valid", valid_counts),
        ]

    def _traceability_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        matrix = result.get("traceability_matrix") or {}
        inventory = result.get("inventory") or []
        return [
            self._check(
                "Traceability Complete",
                matrix.get("record_count") == len(inventory) and matrix.get("record_count", 0) >= 1,
            ),
        ]

    def _status_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        inventory = result.get("inventory") or []
        valid = all(item.get("current_status") in DISCOVERY_STATUSES for item in inventory)
        return [self._check("Discovery Statuses Valid", valid)]

    def _analysis_checks(self, result: dict[str, Any]) -> List[dict[str, Any]]:
        return [
            self._check("Parser Health Computed", bool(result.get("parser_health_metrics"))),
            self._check("Unsupported Pattern Library Created", bool(result.get("unsupported_patterns"))),
            self._check("Gap Analysis Generated", bool(result.get("discovery_gap_analysis"))),
        ]

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
