"""
Engineering Context Writer — exports all 7 JSON output artefacts (R.2A.1 adds
engineering_context_validation.json and fe550_parsing_report.json).
"""
from __future__ import annotations
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List

from .engineering_context_model     import EngineeringContext
from .engineering_context_loader    import EngineeringContextLoader
from .engineering_context_validation import EngineeringContextValidation


def _save(out: pathlib.Path, name: str, data: Any) -> pathlib.Path:
    p = out / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


class EngineeringContextWriter:
    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def write_all(
        self,
        ctx: EngineeringContext,
        loader: EngineeringContextLoader,
        validation_passed: bool,
        validation_warnings: List[str],
        dl_audit: Dict[str, Any] = None,
    ) -> Dict[str, str]:
        ts = datetime.utcnow().isoformat()
        paths: Dict[str, str] = {}

        # 1. engineering_context.json — full context
        p = _save(self._out, "engineering_context.json", {
            "generated": ts,
            "model_version": "7.5.0",
            "phase": "R.2A",
            **ctx.to_dict(),
        })
        paths["engineering_context"] = str(p)

        # 2. engineering_context_statistics.json
        p = _save(self._out, "engineering_context_statistics.json", {
            "generated": ts,
            "parse_confidence": ctx.parse_confidence,
            "steel_grades": list(ctx.steel_grades),
            "concrete_grades": list(ctx.concrete_grades),
            "development_length_table_entries": len(ctx.development_length_table),
            "cover_rules": len(ctx.cover_rules),
            "hook_rules": len(ctx.hook_rules),
            "lap_rules": len(ctx.lap_rules),
            "spacer_rules": len(ctx.spacer_rules),
            "code_references": len(ctx.code_references),
            "warnings": len(ctx.warnings),
        })
        paths["engineering_context_statistics"] = str(p)

        # 3. engineering_context_audit.json
        p = _save(self._out, "engineering_context_audit.json", {
            "generated": ts,
            "validation_passed": validation_passed,
            "validation_warnings": validation_warnings,
            "parse_warnings": list(ctx.warnings),
            "fallback_log": loader.fallback_log,
            "coverage_summary": {
                "development_length_table": "PARSED" if len(ctx.development_length_table) >= 5 else "MISSING",
                "cover_rules": "PARSED" if ctx.cover_rules else "MISSING",
                "steel_grade": "PARSED" if ctx.primary_steel_grade else "FALLBACK",
                "concrete_grade": "PARSED" if ctx.concrete_grades else "FALLBACK",
                "hook_rules": "PARSED" if ctx.hook_rules else "MISSING",
                "lap_rules": "PARSED" if ctx.lap_rules else "MISSING",
                "spacer_rules": "PARSED" if ctx.spacer_rules else "MISSING",
            },
        })
        paths["engineering_context_audit"] = str(p)

        # 4. engineering_context_warnings.json
        p = _save(self._out, "engineering_context_warnings.json", {
            "generated": ts,
            "parse_warnings": list(ctx.warnings),
            "validation_warnings": validation_warnings,
            "fallback_events": loader.fallback_log,
            "total_warnings": len(ctx.warnings) + len(validation_warnings),
        })
        paths["engineering_context_warnings"] = str(p)

        # 5. engineering_context_summary.json
        p = _save(self._out, "engineering_context_summary.json", {
            "generated": ts,
            "gn_dxf": ctx.gn_dxf_path,
            "project_id": ctx.project_id,
            "primary_steel_grade": ctx.primary_steel_grade,
            "concrete_grades": list(ctx.concrete_grades),
            "cover_beam_mm": loader.get_cover("BEAM"),
            "concrete_grade_beam": loader.get_concrete_grade("BEAM"),
            "dev_length_factor_d": loader.get_development_length_factor(),
            "dev_length_dia12_mm": loader.get_development_length_mm(12),
            "hook_multiple_135d": loader.get_hook_multiple(135),
            "bend_multiple_90d": loader.get_standard_bend_multiple(),
            "min_lap_mm": loader.get_minimum_lap_mm(),
            "steel_density_kg_m3": loader.get_steel_density(),
            "parse_confidence": ctx.parse_confidence,
            "pipeline_impact": self._build_impact(ctx, loader),
        })
        paths["engineering_context_summary"] = str(p)

        # 6. engineering_context_lookup_tables.json
        dl_table = {}
        for (sg, dia, cg), lmm in ctx.development_length_table.items():
            dl_table.setdefault(sg, {}).setdefault(f"dia_{dia}", {})[cg] = lmm

        cover_table = {
            r.element_type: {
                "cover_mm": r.cover_mm,
                "concrete_grade": r.concrete_grade,
                "steel_grade": r.steel_grade,
                "source": r.source,
            }
            for r in ctx.cover_rules
        }

        p = _save(self._out, "engineering_context_lookup_tables.json", {
            "generated": ts,
            "development_length_table": dl_table,
            "cover_table": cover_table,
            "hook_rules": [
                {"type": r.rule_type, "angle": r.angle_deg, "multiplier": r.multiplier_xd}
                for r in ctx.hook_rules
            ],
            "lap_rules": [
                {"type": r.rule_type, "value_mm": r.value_mm, "table_ref": r.table_ref}
                for r in ctx.lap_rules
            ],
        })
        paths["engineering_context_lookup_tables"] = str(p)

        # 7. engineering_context_validation.json — 10-rule Fe550 validation
        validator    = EngineeringContextValidation()
        fresh_loader = EngineeringContextLoader(ctx)
        vresults     = validator.run(ctx, fresh_loader, dl_audit or {})
        v_passed     = sum(1 for r in vresults if r.passed)
        p = _save(self._out, "engineering_context_validation.json", {
            "generated": ts,
            "phase": "R.2A.1",
            "model_version": "7.5.1",
            "validation_score": f"{v_passed}/{len(vresults)}",
            "all_pass": v_passed == len(vresults),
            "rules": [r.to_dict() for r in vresults],
        })
        paths["engineering_context_validation"] = str(p)

        # 8. fe550_parsing_report.json
        fe550_keys = {
            k: v for k, v in ctx.development_length_table.items() if k[0] == "Fe550"
        }
        fe415_keys = {
            k: v for k, v in ctx.development_length_table.items() if k[0] == "Fe415"
        }
        fe500_keys = {
            k: v for k, v in ctx.development_length_table.items() if k[0] == "Fe500"
        }

        fe550_source_breakdown: Dict[str, int] = {}
        for entry in ctx.cover_rules:  # hack: iterate full table via ctx.to_dict
            pass
        # Determine source from entries — check via source stored in model
        # (We track this via the IS456_2000_COMPUTED tag in entries)
        # Since we can't access entry sources from the frozen dict, use dl_audit
        fe550_in_dxf   = dl_audit.get("fe550_in_dxf", False) if dl_audit else False
        fe550_computed = dl_audit.get("fe550_computed", False) if dl_audit else False

        comparison: Dict[str, Any] = {}
        for (sg, dia, cg), val in fe550_keys.items():
            k415 = ("Fe415", dia, cg)
            k500 = ("Fe500", dia, cg)
            comparison[f"dia{dia}_{cg}"] = {
                "Fe415_mm": ctx.development_length_table.get(k415),
                "Fe500_mm": ctx.development_length_table.get(k500),
                "Fe550_mm": val,
                "Fe550_source": "GN_DXF_TABLE_1" if fe550_in_dxf else "IS456_2000_COMPUTED",
            }

        p = _save(self._out, "fe550_parsing_report.json", {
            "generated": ts,
            "model_version": "7.5.4",
            "audit_finding": (
                dl_audit.get("root_cause", "")
                if dl_audit else
                "Fe550 development-length table status unknown."
            ),
            "fe550_in_gn_dxf": fe550_in_dxf,
            "fe550_computed_from_is456": fe550_computed,
            "is456_formula": "Ld = (phi * fy/1.15) / (4 * tau_bd) — fallback only",
            "bond_stresses": {
                "M20": "1.2 * 1.6 = 1.92 N/mm2",
                "M25": "1.4 * 1.6 = 2.24 N/mm2",
                "M30": "1.5 * 1.6 = 2.40 N/mm2",
                "M35": "1.7 * 1.6 = 2.72 N/mm2",
                "M40": "1.9 * 1.6 = 3.04 N/mm2",
            },
            "fe550_entry_count": len(fe550_keys),
            "previous_fallback_behaviour": "get_development_length_mm(Fe550) silently returned Fe415 value",
            "corrected_behaviour": (
                "get_development_length_mm(Fe550) returns DXF-parsed Fe550 value "
                "when FY-550 table is extracted via block expansion (R.2A.2+)"
            ),
            "tables_in_gn_dxf": dl_audit.get("dxf_table_headers_found", []) if dl_audit else [],
            "validation_score": f"{v_passed}/{len(vresults)}",
            "lookup_comparison_sample": dict(list(comparison.items())[:5]),
        })
        paths["fe550_parsing_report"] = str(p)

        return paths

    def _build_impact(self, ctx: EngineeringContext, loader: EngineeringContextLoader) -> dict:
        """Compare GN-parsed values against current pipeline hardcoded constants."""
        gn_cover   = loader.get_cover("BEAM")
        gn_steel   = ctx.primary_steel_grade
        gn_dl_12   = loader.get_development_length_mm(12)
        gn_dl_fact = loader.get_development_length_factor()
        gn_conc    = loader.get_concrete_grade("BEAM")

        pipeline_cover  = 40   # hardcoded in steel_weight_completion.py
        pipeline_steel  = "Fe415"
        pipeline_dl_12  = 40 * 12
        pipeline_dl_f   = 40
        pipeline_conc   = "M30"

        return {
            "cover_mm": {
                "pipeline_hardcoded": pipeline_cover,
                "gn_dxf_value": gn_cover,
                "match": gn_cover == pipeline_cover,
                "delta": gn_cover - pipeline_cover,
            },
            "steel_grade": {
                "pipeline_hardcoded": pipeline_steel,
                "gn_dxf_value": gn_steel,
                "match": gn_steel == pipeline_steel,
            },
            "development_length_dia12_mm": {
                "pipeline_hardcoded": pipeline_dl_12,
                "gn_dxf_value": gn_dl_12,
                "match": gn_dl_12 == pipeline_dl_12,
                "delta": gn_dl_12 - pipeline_dl_12,
            },
            "dev_length_factor_d": {
                "pipeline_hardcoded": pipeline_dl_f,
                "gn_dxf_value": gn_dl_fact,
                "match": gn_dl_fact == pipeline_dl_f,
                "delta": gn_dl_fact - pipeline_dl_f,
            },
            "concrete_grade_beam": {
                "pipeline_hardcoded": pipeline_conc,
                "gn_dxf_value": gn_conc,
                "match": gn_conc == pipeline_conc,
            },
        }
