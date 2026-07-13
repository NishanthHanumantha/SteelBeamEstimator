"""Read-only data loader for Phase L.1 Accuracy Sprint."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

PHASE = "Phase L.1"
MODEL_VERSION = "6.3.0"
ENGINE_VERSION = "1.0.0"
PHASE_FOLDER = "PhaseL.1 - accuracy_sprint_1_estimator_gap_closure"
OUTPUT_DIR_REL = Path("data/output") / PHASE_FOLDER
CONFIG_REL = Path("config/accuracy_sprint_1.yaml")


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists() or path.stat().st_size <= 2:
        return None
    import json
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def default_paths(project_root: Path) -> Dict[str, Path]:
    root = project_root
    v6_out = root / "data/output"
    v5_out = root.parent / "Version5/data/output"
    phase_i = v6_out / "phase_i"
    return {
        "output_dir": v6_out / PHASE_FOLDER,
        "config": root / CONFIG_REL,
        # Ground-truth estimator Excel
        "estimator_excel": _find_estimator_excel(root),
        # V6 K.1.1 decisions (always available after K.1.1 run)
        "decision_objects": v6_out / "engineering_intent_resolution/engineering_decision_objects.json",
        "decision_registry": v6_out / "engineering_intent_resolution/engineering_decision_registry.json",
        "decision_statistics": v6_out / "engineering_intent_resolution/engineering_decision_statistics.json",
        "decision_traceability": v6_out / "engineering_intent_resolution/engineering_intent_resolution_traceability.json",
        # V6 K.2.1 validation
        "validated_registry": v6_out / "PhaseK.2.1 - engineering_decision_validation/validated_decision_registry.json",
        "validation_statistics": v6_out / "PhaseK.2.1 - engineering_decision_validation/decision_validation_statistics.json",
        "validation_matrix": v6_out / "PhaseK.2.1 - engineering_decision_validation/decision_validation_matrix.json",
        # V6 intent
        "intent_objects": v6_out / "engineering_intent/engineering_intent_objects.json",
        "intent_statistics": v6_out / "engineering_intent/engineering_intent_statistics.json",
        # V6 Phase I pipeline outputs (may be absent if pipeline not fully run)
        "steel_weight_results": phase_i / "i_11_steel_weight/steel_weight_results.json",
        "bbs_results": phase_i / "i_10_bbs/bbs_results.json",
        "beam_schedule_results": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "engineering_reports": phase_i / "i_16_engineering_report/engineering_reports.json",
        "calculation_contexts": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "cut_length_results": phase_i / "i_6_cut_length/cut_length_results.json",
        "development_length_results": phase_i / "i_3_development_length/development_length_results.json",
        "hook_results": phase_i / "i_4_hook_length/hook_results.json",
        # V6 Engineering objects
        "engineering_objects": v6_out / "phase_g/g_5_1_engineering_objects/engineering_objects.json",
        "recovery_registry": v6_out / "engineering_recovery/recovery_registry.json",
        # V6 QA / comparison outputs (if run)
        "v6_audit_summary": v6_out / "estimator_validation/audit_summary.json",
        "v6_comparison_stats": v6_out / "estimator_validation/comparison_statistics.json",
        "v6_accuracy_stats": v6_out / "accuracy_dashboard/accuracy_statistics.json",
        "v6_diameter_coverage": v6_out / "accuracy_dashboard/diameter_coverage.json",
        "v6_engineering_gap": v6_out / "engineering_analysis/engineering_gap_analysis.json",
        # V5 reference baseline (read-only, for comparison context)
        "v5_comparison_stats": v5_out / "estimator_validation/comparison_statistics.json",
        "v5_accuracy_stats": v5_out / "accuracy_dashboard/accuracy_statistics.json",
        "v5_diameter_coverage": v5_out / "accuracy_dashboard/diameter_coverage.json",
        "v5_engineering_gap": v5_out / "engineering_analysis/engineering_gap_analysis.json",
        "v5_beam_comparison": v5_out / "estimator_validation/beam_comparison.json",
        "v5_root_cause_report": v5_out / "estimator_validation/root_cause_report.json",
    }


def _find_estimator_excel(root: Path) -> Path:
    folder = root / "data/Estimator_Validated_Output"
    if folder.exists():
        candidates = sorted(folder.glob("*.xlsx"))
        if candidates:
            return candidates[0]
    return folder / "Estimator_Validated_Output.xlsx"


def load_validation_config(config_path: Path) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "enable": True,
        "benchmark_project_only": True,
        "generate_excel_report": True,
        "generate_dashboard": True,
        "strict_gap_classification": True,
        "strict_root_cause_assignment": True,
        "export_improvement_tracker": True,
        "generate_priority_backlog": True,
    }
    if not config_path.exists():
        return defaults
    try:
        import yaml  # type: ignore
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            defaults.update(payload)
    except Exception:
        pass
    return defaults


class AccuracyLoader:
    """Load all available Phase L.1 inputs. Strictly read-only."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def load(self) -> Dict[str, Any]:
        json_keys = {k for k in self.paths if k not in ("output_dir", "config", "estimator_excel")}
        payloads: Dict[str, Any] = {}
        for key in json_keys:
            path = self.paths[key]
            val = _load_json(path)
            payloads[key] = val
            self.load_status[key] = val is not None

        # Parse estimator Excel
        estimator_data = self._parse_estimator_excel()
        self.load_status["estimator_excel"] = bool(estimator_data.get("beam_blocks"))

        # Flatten decisions
        decisions_payload = payloads.get("decision_objects") or {}
        decisions: List[Dict[str, Any]] = list(decisions_payload.get("objects") or [])
        if not decisions:
            reg = payloads.get("decision_registry") or {}
            decisions = list(reg.get("entries") or [])

        # Flatten engineering intents
        intent_payload = payloads.get("intent_objects") or {}
        intents: List[Dict[str, Any]] = list(intent_payload.get("objects") or [])

        # Build beam-level decision index
        decisions_by_beam: Dict[str, List[Dict[str, Any]]] = {}
        for d in decisions:
            beam = str(d.get("beam_id") or "")
            if beam:
                decisions_by_beam.setdefault(beam, []).append(d)

        # Build decision category index
        decisions_by_category: Dict[str, List[Dict[str, Any]]] = {}
        for d in decisions:
            cat = str(d.get("decision_category") or "UNKNOWN")
            decisions_by_category.setdefault(cat, []).append(d)

        # Validated IDs
        val_reg = payloads.get("validated_registry") or {}
        execution_allowed_ids = set(str(i) for i in (val_reg.get("execution_allowed_ids") or []))

        # Artifact presence
        artifact_presence: Dict[str, bool] = {
            k: bool(payloads.get(k)) for k in (
                "steel_weight_results", "bbs_results", "beam_schedule_results",
                "engineering_reports", "calculation_contexts", "cut_length_results",
                "development_length_results", "hook_results", "engineering_objects",
                "recovery_registry",
            )
        }
        artifact_presence["v5_baseline"] = bool(payloads.get("v5_comparison_stats"))
        artifact_presence["v6_qa"] = bool(payloads.get("v6_accuracy_stats"))

        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "project_root": str(self.project_root),
            "paths": {k: str(v) for k, v in self.paths.items()},
            "load_status": dict(self.load_status),
            "estimator_data": estimator_data,
            "decisions": decisions,
            "decisions_by_beam": decisions_by_beam,
            "decisions_by_category": decisions_by_category,
            "execution_allowed_ids": execution_allowed_ids,
            "intents": intents,
            "payloads": payloads,
            "artifact_presence": artifact_presence,
        }

    def _parse_estimator_excel(self) -> Dict[str, Any]:
        path = self.paths["estimator_excel"]
        if not path.exists():
            return {"beam_blocks": {}, "rows": [], "error": "Estimator Excel not found"}
        try:
            import sys
            root_str = str(self.project_root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
            from src.estimator_validation.comparison_utils import (
                load_workbook,
                find_schedule_start_row,
                parse_schedule_rows,
            )
            wb = load_workbook(str(path))
            ws = wb.active
            start_row = find_schedule_start_row(ws)
            blocks = parse_schedule_rows(ws, start_row)
            all_rows = []
            beam_summaries: Dict[str, Any] = {}
            for beam_mark, block in blocks.items():
                rows_data = []
                total_bars = 0
                total_weight = 0.0
                diameters: set = set()
                roles: set = set()
                for row in block.rows:
                    r = {
                        "beam_mark": beam_mark,
                        "row_number": row.row_number,
                        "description": row.description,
                        "role_hint": row.role_hint or "",
                        "diameter_mm": row.diameter_mm,
                        "spacing_m": row.spacing_m,
                        "bar_count": row.bar_count,
                        "development_length_m": row.development_length_m,
                        "cut_length_m": row.cut_length_m,
                        "total_length_m": row.total_length_m,
                        "steel_weight_kg": row.steel_weight_kg,
                        "fabrication_mark": row.fabrication_mark,
                        "shape_code": row.shape_code,
                    }
                    rows_data.append(r)
                    all_rows.append(r)
                    total_bars += int(row.bar_count or 0)
                    total_weight += float(row.steel_weight_kg or 0.0)
                    if row.diameter_mm:
                        diameters.add(float(row.diameter_mm))
                    if row.role_hint:
                        roles.add(row.role_hint)
                beam_summaries[beam_mark] = {
                    "beam_mark": beam_mark,
                    "row_count": len(rows_data),
                    "total_bars": total_bars,
                    "total_steel_weight_kg": round(total_weight, 3),
                    "diameters_mm": sorted(diameters),
                    "roles": sorted(roles),
                    "rows": rows_data,
                }
            total_est_weight = sum(b["total_steel_weight_kg"] for b in beam_summaries.values())
            total_est_bars = sum(b["total_bars"] for b in beam_summaries.values())
            total_est_rows = sum(b["row_count"] for b in beam_summaries.values())
            all_diameters = sorted({r["diameter_mm"] for r in all_rows if r["diameter_mm"]})
            all_roles = sorted({r["role_hint"] for r in all_rows if r["role_hint"]})
            return {
                "beam_blocks": beam_summaries,
                "rows": all_rows,
                "beam_count": len(beam_summaries),
                "total_rows": total_est_rows,
                "total_bars": total_est_bars,
                "total_steel_weight_kg": round(total_est_weight, 3),
                "all_diameters_mm": all_diameters,
                "all_roles": all_roles,
                "source_file": str(path.name),
                "error": None,
            }
        except Exception as exc:
            return {"beam_blocks": {}, "rows": [], "error": str(exc)}
