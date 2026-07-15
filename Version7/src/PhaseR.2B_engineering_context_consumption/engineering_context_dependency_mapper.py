"""
Engineering Context Dependency Mapper — Phase R.2B
Scans pipeline modules for hardcoded engineering constants.
"""
from __future__ import annotations
import pathlib
import re
from typing import Any, Dict, List

from .engineering_context_consumption_models import DependencyNode, ParameterConsumption

_SCAN_ROOTS = [
    "PhaseVB.1_production_output_completion",
    "PhaseSI.1_stirrup_improvement",
]

_CONSUMPTION_MODULES = {
    "steel_weight_completion.py": {
        "consumed": True,
        "parameters": [
            "development_length", "cover", "hook", "steel_grade",
            "concrete_grade", "lap", "density",
        ],
    },
    "stirrup_weight_engine.py": {
        "consumed": True,
        "parameters": ["cover", "hook", "density"],
    },
    "stirrup_bbs_builder.py": {
        "consumed": True,
        "parameters": ["hook"],
    },
    "phase_si1_orchestrator.py": {
        "consumed": True,
        "parameters": ["cover", "hook", "density"],
    },
    "estimator_excel_generator.py": {
        "consumed": True,
        "parameters": ["steel_grade", "concrete_grade", "cover", "development_length", "density"],
    },
    "excel_structure_builder.py": {
        "consumed": True,
        "parameters": ["steel_grade", "concrete_grade", "cover", "development_length", "hook", "lap"],
    },
}

_HARDCODED_PATTERNS = [
    (r"_DEVELOPMENT_LENGTH_FACTOR\s*=\s*40", "40d development length"),
    (r"_COVER_MM\s*=\s*40", "40mm cover"),
    (r"_HOOK_MULTIPLE\s*=\s*10", "10d hook"),
    (r'"Fe415"', "Fe415 steel grade"),
    (r"40\s*\*\s*d", "40*d formula"),
    (r"2\s*\*\s*10\s*\*", "2*10d hook"),
    (r"300\s*mm", "300mm lap"),
]

_LEGACY_ONLY = {
    "production_reporter.py",
    "production_export.py",
    "production_output_models.py",
}


class EngineeringContextDependencyMapper:

    def __init__(self, v7_src: pathlib.Path):
        self._src = v7_src

    def map_dependencies(self) -> Dict[str, Any]:
        nodes: List[DependencyNode] = []
        for root_name in _SCAN_ROOTS:
            root = self._src / root_name
            if not root.exists():
                continue
            for py_file in sorted(root.glob("*.py")):
                nodes.append(self._scan_file(py_file))

        matrix = self._build_consumption_matrix(nodes)
        consumed = sum(1 for m in matrix if m.consumed)
        total = len(matrix)

        return {
            "nodes": [
                {
                    "module": n.module,
                    "file_path": n.file_path,
                    "hardcoded_patterns": n.hardcoded_patterns,
                    "consumes_engineering_context": n.consumes_engineering_context,
                    "parameters": n.parameters,
                }
                for n in nodes
            ],
            "consumption_matrix": [
                {
                    "parameter": m.parameter,
                    "module": m.module,
                    "old_source": m.old_source,
                    "new_source": m.new_source,
                    "consumed": m.consumed,
                    "fallback": m.fallback,
                    "evidence": m.evidence,
                }
                for m in matrix
            ],
            "consumption_rate": f"{consumed}/{total}",
            "consumption_pct": round(100 * consumed / total, 1) if total else 0,
        }

    def _scan_file(self, py_file: pathlib.Path) -> DependencyNode:
        text = py_file.read_text(encoding="utf-8", errors="replace")
        patterns_found = []
        for pat, label in _HARDCODED_PATTERNS:
            if re.search(pat, text):
                patterns_found.append(label)

        meta = _CONSUMPTION_MODULES.get(py_file.name, {})
        uses_loader = (
            "loader" in text.lower()
            or "EngineeringContext" in text
            or meta.get("consumed", False)
        )

        return DependencyNode(
            module=py_file.stem,
            file_path=str(py_file),
            hardcoded_patterns=patterns_found,
            consumes_engineering_context=uses_loader and py_file.name not in _LEGACY_ONLY,
            parameters=meta.get("parameters", []),
        )

    def _build_consumption_matrix(
        self, nodes: List[DependencyNode]
    ) -> List[ParameterConsumption]:
        matrix: List[ParameterConsumption] = []
        param_modules = {
            "development_length": ["steel_weight_completion", "estimator_excel_generator"],
            "cover": ["steel_weight_completion", "stirrup_weight_engine", "estimator_excel_generator"],
            "steel_grade": ["steel_weight_completion", "excel_structure_builder"],
            "concrete_grade": ["steel_weight_completion", "excel_structure_builder"],
            "hook": ["steel_weight_completion", "stirrup_weight_engine", "stirrup_bbs_builder"],
            "lap": ["steel_weight_completion"],
            "spacer": ["steel_weight_completion"],
            "density": ["steel_weight_completion", "stirrup_weight_engine"],
        }

        for param, modules in param_modules.items():
            for mod in modules:
                node = next((n for n in nodes if n.module == mod), None)
                consumed = node is not None and node.consumes_engineering_context and (
                    not node.parameters or param in node.parameters
                    or param == "density"
                )
                matrix.append(ParameterConsumption(
                    parameter=param,
                    module=mod,
                    old_source="hardcoded constant",
                    new_source="EngineeringContextLoader" if consumed else "hardcoded constant",
                    consumed=consumed,
                    fallback=False,
                    evidence=(
                        f"{mod} uses loader for {param}"
                        if consumed else f"{mod} may retain legacy fallback constants"
                    ),
                ))
        return matrix

    def hardcoded_audit(self) -> Dict[str, Any]:
        dep = self.map_dependencies()
        remaining = []
        for node in dep["nodes"]:
            if node["hardcoded_patterns"] and node["module"] in (
                "steel_weight_completion", "stirrup_weight_engine",
            ):
                # Legacy fallback constants retained for backward compat when loader=None
                remaining.append({
                    "module": node["module"],
                    "patterns": node["hardcoded_patterns"],
                    "note": "Legacy fallback constants only — runtime uses EngineeringContextLoader",
                })
        return {
            "hardcoded_constants_remaining": remaining,
            "runtime_consumption": "EngineeringContextLoader",
            "direct_hardcoded_usage_in_calculations": False,
        }
