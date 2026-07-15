"""Engineering Context Statistics — compute parse completeness metrics."""
from __future__ import annotations
from typing import Dict, Any
from .engineering_context_model import EngineeringContext


class EngineeringContextStatistics:
    def __init__(self, ctx: EngineeringContext):
        self._ctx = ctx

    def compute(self) -> Dict[str, Any]:
        ctx = self._ctx
        dl = ctx.development_length_table

        # Dev length table coverage
        steel_grades  = set(k[0] for k in dl)
        diameters     = sorted(set(k[1] for k in dl))
        conc_grades   = sorted(set(k[2] for k in dl))

        dl_coverage = {}
        for sg in steel_grades:
            for cg in conc_grades:
                keys = [(sg, d, cg) for d in diameters if (sg, d, cg) in dl]
                dl_coverage[f"{sg}/{cg}"] = {
                    "diameters": [k[1] for k in keys],
                    "count": len(keys),
                    "values_mm": [dl[k] for k in keys],
                }

        # Cover completeness
        cover_elements = [r.element_type for r in ctx.cover_rules]

        return {
            "parse_confidence":          ctx.parse_confidence,
            "steel_grades_found":        list(ctx.steel_grades),
            "primary_steel_grade":       ctx.primary_steel_grade,
            "concrete_grades_found":     list(ctx.concrete_grades),
            "dev_length_table": {
                "total_entries":         len(dl),
                "steel_grades_in_table": sorted(steel_grades),
                "diameters_mm":          diameters,
                "concrete_grades":       conc_grades,
                "coverage_by_sg_cg":     dl_coverage,
            },
            "cover_rules": {
                "total":          len(ctx.cover_rules),
                "elements":       cover_elements,
                "beam_cover_mm":  next((r.cover_mm for r in ctx.cover_rules if "BEAM IN SUPER" in r.element_type.upper()), None),
            },
            "hook_rules":        len(ctx.hook_rules),
            "lap_rules":         len(ctx.lap_rules),
            "spacer_rules":      len(ctx.spacer_rules),
            "code_references":   len(ctx.code_references),
            "warnings":          len(ctx.warnings),
        }
