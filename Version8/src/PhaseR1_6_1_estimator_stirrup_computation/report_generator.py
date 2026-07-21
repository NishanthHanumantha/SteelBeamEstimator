"""
Markdown report for Phase R.1.6.1.
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

from typing import Any, Dict, List

from stirrup_model import StirrupComputation

MODEL_VERSION = "8.8.1"


class ReportGenerator:
    def markdown(self, payload: Dict[str, Any]) -> str:
        comps: List[StirrupComputation] = payload["computations"]
        validation = payload["validation"]
        rec = payload.get("recommendation", "B")
        uniform = sum(1 for c in comps if c.notation.notation_type == "UNIFORM")
        variable = sum(1 for c in comps if c.notation.notation_type == "VARIABLE")

        lines = [
            "# Phase R.1.6.1 — Estimator Stirrup Computation Engine",
            "",
            f"**MODEL_VERSION:** {MODEL_VERSION}",
            f"**Recommendation:** {rec}",
            f"**Validation:** {validation.get('passed')}/{validation.get('total')}",
            "",
            "## Executive Summary",
            "",
            f"- Production stirrup computations: **{len(comps)}**",
            f"- Uniform / Variable: **{uniform}** / **{variable}**",
            f"- EngineeringBars: **{len(payload.get('bars') or [])}**",
            f"- Total stirrup steel: **{round(sum(c.weight_kg for c in comps), 3)} kg**",
            "",
            "## Estimator Methodology",
            "",
            "- Zone Length = Beam Length / N (equal zones)",
            "- Quantity = (Length / Spacing) + 1 per zone",
            "- Perimeter = 2 × [(B−2C)+(D−2C)]",
            "- Cut Length = Perimeter + 2 × Hook Length (GN xd)",
            "- Weight = (Cut Length × Quantity) × IS unit weight",
            "",
            "## Sample Computations",
            "",
        ]
        for c in comps[:8]:
            lines.append(
                f"- `{c.beam_id}` `{c.label}` → zones={len(c.zones)} qty={c.total_quantity} "
                f"cut={c.cut_length_mm} mm weight={c.weight_kg} kg"
            )

        lines.extend([
            "",
            "## Regression",
            "",
            f"- Overall: `{validation.get('overall_passed')}`",
            f"- Formula checks: `{[r for r in (validation.get('formula_checks') or []) if not r.get('passed')]}` failures",
            "",
            "## General Notes",
            "",
            f"- `{payload.get('gn_summary')}`",
            "",
            "---",
            f"*Phase R.1.6.1 | MODEL_VERSION {MODEL_VERSION}*",
            "",
        ])
        return "\n".join(lines)
