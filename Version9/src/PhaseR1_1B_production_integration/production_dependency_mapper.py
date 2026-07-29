"""
production_dependency_mapper.py — Maps production pipeline dependencies.
MODEL_VERSION: 8.2.1

Inspects every production stage and identifies its current reinforcement
data source, required source, and migration status.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List


class ProductionDependencyMapper:
    """Builds the complete production dependency graph."""

    PIPELINE_STAGES = [
        {
            "stage": "V.ROOT.1",
            "module": "PhaseVROOT.1_dynamic_pipeline_initialization",
            "class": "PhaseVROOT1Orchestrator",
            "reads": ["DXF files", "input folder"],
            "writes": ["beam_registry.json", "drawing_manifest.json", "engineering_objects.json"],
            "reinforcement_role": "initializer",
            "current_source": "DXF discovery",
            "required_source": "DXF discovery",
            "migration_status": "DONE",
        },
        {
            "stage": "R.1",
            "module": "PhaseR.1_generalized_reinforcement_discovery",
            "class": "PhaseR1Orchestrator",
            "reads": ["beam_registry.json", "reinforcement DXF"],
            "writes": ["beam_reinforcement_models.json", "reinforcement_annotations.json", "reinforcement_groups.json"],
            "reinforcement_role": "annotation_discovery",
            "current_source": "R.1.1A AdaptiveAssociationEngine",
            "required_source": "R.1.1A AdaptiveAssociationEngine",
            "migration_status": "DONE",
        },
        {
            "stage": "R.1.3",
            "module": "PhaseR1.3_pipeline_integration",
            "class": "PipelineIntegrationManager",
            "reads": ["beam_reinforcement_models.json (R.1)", "beam_registry.json"],
            "writes": ["engineering_bar_models.json", "beam_reinforcement_models_production.json"],
            "reinforcement_role": "model_builder",
            "current_source": "R.1 beam_reinforcement_models.json",
            "required_source": "R.1.1A beam_reinforcement_models.json",
            "migration_status": "DONE",
        },
        {
            "stage": "V.B.1 (Steel)",
            "module": "PhaseVB.1_production_output_completion",
            "class": "SteelWeightCompletion",
            "reads": ["beam_reinforcement_models_production.json (R.1.3) OR beam_reinforcement_models.json (L.2 fallback)"],
            "writes": ["steel_weight_summary.json"],
            "reinforcement_role": "consumer",
            "current_source": "ReinforcementSourceSelector: R.1.3 preferred, L.2 fallback",
            "required_source": "EngineeringBarModel via R.1.3 ONLY",
            "migration_status": "ACTIVE — R.1.3 path preferred, L.2 fallback retained",
        },
        {
            "stage": "V.B.1 (BBS)",
            "module": "PhaseVB.1_production_output_completion",
            "class": "BBSCompletionEngine",
            "reads": ["beam_reinforcement_models_production.json (R.1.3) OR beam_reinforcement_models.json (L.2 fallback)"],
            "writes": ["bbs_summary.json"],
            "reinforcement_role": "consumer",
            "current_source": "ReinforcementSourceSelector: R.1.3 preferred",
            "required_source": "EngineeringBarModel via R.1.3 ONLY",
            "migration_status": "ACTIVE — R.1.3 path preferred",
        },
        {
            "stage": "V.B.1 (Excel)",
            "module": "PhaseVB.1_production_output_completion",
            "class": "EstimatorExcelGenerator",
            "reads": ["steel_weight_summary.json", "bbs_summary.json"],
            "writes": ["Estimation_Output.xlsx", "Engineering_Review.xlsx"],
            "reinforcement_role": "consumer",
            "current_source": "Downstream of steel/BBS",
            "required_source": "Downstream of steel/BBS (EngineeringBarModel)",
            "migration_status": "DONE — indirect via steel/BBS",
        },
        {
            "stage": "L.2 (legacy spine)",
            "module": "PhaseL.2 - engineering_reinforcement_interpretation",
            "class": "EngineeringReinforcementInterpretationEngine",
            "reads": ["reinforcement_objects.json (V5 adapter)", "engineering_objects.json"],
            "writes": ["beam_reinforcement_models.json (L.2)"],
            "reinforcement_role": "legacy_interpreter",
            "current_source": "V5 adapter reinforcement_objects.json",
            "required_source": "Not required — R.1 path supersedes",
            "migration_status": "LEGACY — bypassed when R.1.3 present",
        },
    ]

    LEGACY_READERS = [
        {
            "module": "PhaseVB.1_production_output_completion/phase_vb1_orchestrator.py",
            "class": "PhaseVB1Orchestrator",
            "function": "_resolve_r13_reinforcement_path",
            "reads": "REFERENCE_CLASSIFICATION_LEGACY (L.2 beam_reinforcement_models.json)",
            "condition": "when R.1.3 production file absent",
            "status": "FALLBACK — active when R.1.3 not built",
        },
        {
            "module": "PhaseL.2 - engineering_reinforcement_interpretation",
            "class": "InterpretationCollector",
            "function": "collect",
            "reads": "reinforcement_objects.json (Version5 adapter format)",
            "condition": "always — part of L.2 legacy spine",
            "status": "LEGACY — not consumed by R.1.3 path",
        },
        {
            "module": "PhaseVROOT.1_dynamic_pipeline_initialization",
            "class": "EngineeringObjectInitializer",
            "function": "write_adapters",
            "reads": "DXF → writes reinforcement_objects.json for L.2",
            "condition": "always — writes V5 adapter for L.2 compatibility",
            "status": "COMPATIBILITY_ADAPTER",
        },
    ]

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root

    def build(self) -> Dict[str, Any]:
        artefact_status = self._audit_artefacts()
        dependency_graph = self._build_graph(artefact_status)
        return {
            "pipeline_stages": self.PIPELINE_STAGES,
            "legacy_readers": self.LEGACY_READERS,
            "artefact_status": artefact_status,
            "dependency_graph": dependency_graph,
            "summary": {
                "total_stages": len(self.PIPELINE_STAGES),
                "done_stages": sum(1 for s in self.PIPELINE_STAGES if s["migration_status"] == "DONE"),
                "active_stages": sum(1 for s in self.PIPELINE_STAGES if s["migration_status"].startswith("ACTIVE")),
                "legacy_stages": sum(1 for s in self.PIPELINE_STAGES if s["migration_status"].startswith("LEGACY")),
                "legacy_reader_count": len(self.LEGACY_READERS),
            },
        }

    def _audit_artefacts(self) -> Dict[str, Any]:
        checks = {
            "r1_beam_reinforcement_models": (
                self._v7 / "data/output/PhaseR.1_generalized_reinforcement_discovery/beam_reinforcement_models.json"
            ),
            "r13_engineering_bar_models": (
                self._v7 / "data/output/PhaseR1.3_pipeline_integration/engineering_bar_models.json"
            ),
            "r13_production_models": (
                self._v7 / "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json"
            ),
            "l2_beam_reinforcement_models": (
                self._v7 / "data/output/PhaseL.2 - engineering_reinforcement_interpretation/beam_reinforcement_models.json"
            ),
            "production_steel_summary": (
                self._v7 / "data/output/Production_Output/steel_weight_summary.json"
            ),
            "production_bbs_summary": (
                self._v7 / "data/output/Production_Output/bbs_summary.json"
            ),
            "production_estimation_xlsx": (
                self._v7 / "data/output/Production_Output/Estimation_Output.xlsx"
            ),
        }
        result = {}
        for key, path in checks.items():
            exists = path.exists()
            info: Dict[str, Any] = {"exists": exists, "path": str(path)}
            if exists and path.suffix == ".json":
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        for size_key in ("total_bars", "beam_count", "total_beams", "beams_with_steel"):
                            if size_key in data:
                                info["size_hint"] = f"{size_key}={data[size_key]}"
                                break
                except Exception:
                    pass
            result[key] = info
        return result

    def _build_graph(self, artefact_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        r1_ok = artefact_status.get("r1_beam_reinforcement_models", {}).get("exists", False)
        r13_ok = artefact_status.get("r13_production_models", {}).get("exists", False)
        steel_ok = artefact_status.get("production_steel_summary", {}).get("exists", False)
        bbs_ok = artefact_status.get("production_bbs_summary", {}).get("exists", False)
        excel_ok = artefact_status.get("production_estimation_xlsx", {}).get("exists", False)

        return [
            {"from": "DXF", "to": "R.1 (annotation discovery)", "active": True, "method": "ezdxf parse"},
            {"from": "R.1", "to": "R.1.3 (EngineeringBarBuilder)", "active": r1_ok, "method": "beam_reinforcement_models.json"},
            {"from": "R.1.3", "to": "V.B.1 Steel", "active": r13_ok, "method": "beam_reinforcement_models_production.json"},
            {"from": "V.B.1 Steel", "to": "V.B.1 BBS", "active": steel_ok, "method": "steel_weight_summary.json"},
            {"from": "V.B.1 BBS", "to": "V.B.1 Excel", "active": bbs_ok, "method": "bbs_summary.json"},
            {"from": "V.B.1 Excel", "to": "Estimation_Output.xlsx", "active": excel_ok, "method": "openpyxl"},
            {"from": "L.2 (legacy)", "to": "V.B.1 (fallback)", "active": not r13_ok, "method": "LEGACY — bypassed when R.1.3 present"},
        ]
