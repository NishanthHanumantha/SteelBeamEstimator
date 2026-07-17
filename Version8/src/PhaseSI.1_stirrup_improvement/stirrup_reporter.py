"""
Stirrup Reporter — Phase SI.1 MODULE 9

Generates the 8-section Phase SI.1 report.
"""
from datetime import datetime
from typing import List, Dict, Any

from stirrup_models import BeamStirrupResult, StirrupEngineResult, StirrupType


class StirrupReporter:
    def __init__(
        self,
        engine_result: StirrupEngineResult,
        statistics: Dict[str, Any],
    ) -> None:
        self.result = engine_result
        self.stats  = statistics

    def build(self) -> Dict[str, Any]:
        return {
            "phase": "SI.1",
            "model_version": "6.6.1",
            "generated_at": datetime.now().isoformat(),
            "sections": {
                "1_executive_summary":          self._executive_summary(),
                "2_engineering_distribution":   self._distribution_summary(),
                "3_zone_calculations":          self._zone_calculations(),
                "4_quantity_calculations":      self._quantity_calculations(),
                "5_bbs_summary":                self._bbs_summary(),
                "6_steel_weight_summary":       self._steel_weight_summary(),
                "7_validation_summary":         self._validation_summary(),
                "8_comparison_with_old_engine": self._comparison(),
            },
        }

    # ── sections ──────────────────────────────────────────────────────────────

    def _executive_summary(self) -> Dict:
        return {
            "phase_id": "SI.1",
            "model_version": "6.6.1",
            "objective": "Improved stirrup distribution & quantity calculation",
            "beams_with_stirrups": len(self.result.beam_results),
            "uniform_beams": self.result.total_uniform_beams,
            "variable_beams": self.result.total_variable_beams,
            "total_stirrup_qty": self.result.total_quantity,
            "new_total_weight_kg": round(self.result.total_weight_kg, 3),
            "old_total_weight_kg": round(self.result.old_total_weight_kg, 3),
            "weight_improvement_kg": round(
                self.result.total_weight_kg - self.result.old_total_weight_kg, 3
            ),
            "validation_passed": self.result.validation_passed,
        }

    def _distribution_summary(self) -> Dict:
        return self.stats

    def _zone_calculations(self) -> List[Dict]:
        out = []
        for br in self.result.beam_results:
            beam_entry: Dict = {
                "beam_id": br.beam_id,
                "span_mm": br.span_mm,
                "stirrup_type": br.stirrup_type.value,
                "zones": [],
            }
            for g in br.groups:
                for z in g.zones:
                    beam_entry["zones"].append({
                        "zone_id": z.zone_id,
                        "role": z.role.value,
                        "start_mm": z.start_mm,
                        "end_mm": z.end_mm,
                        "length_mm": z.length_mm,
                        "spacing_mm": z.spacing_mm,
                    })
            out.append(beam_entry)
        return out

    def _quantity_calculations(self) -> List[Dict]:
        out = []
        for br in self.result.beam_results:
            groups_info = []
            for g in br.groups:
                groups_info.append({
                    "group_id": g.group_id,
                    "spacing_mm": g.spacing_mm,
                    "quantity": g.quantity,
                    "is_merged": g.is_merged,
                    "merge_note": g.merge_note,
                    "weight_kg": round(g.total_weight_kg, 3),
                })
            out.append({
                "beam_id": br.beam_id,
                "stirrup_type": br.stirrup_type.value,
                "old_quantity": br.old_quantity,
                "new_quantity": br.total_quantity,
                "quantity_change": br.total_quantity - br.old_quantity,
                "groups": groups_info,
            })
        return out

    def _bbs_summary(self) -> Dict:
        total_rows = sum(len(br.groups) for br in self.result.beam_results)
        return {
            "total_bbs_rows": total_rows,
            "merged_support_rows": self.stats.get("total_merged_rows", 0),
            "midspan_rows": self.stats.get("total_midspan_zones", 0),
            "format": "Estimator-style per-zone rows",
        }

    def _steel_weight_summary(self) -> Dict:
        return {
            "new_total_weight_kg": round(self.result.total_weight_kg, 3),
            "old_total_weight_kg": round(self.result.old_total_weight_kg, 3),
            "change_kg": round(
                self.result.total_weight_kg - self.result.old_total_weight_kg, 3
            ),
            "diameter_totals_kg": {
                f"Y{d}": round(w, 3)
                for d, w in self.result.diameter_totals_kg.items()
            },
        }

    def _validation_summary(self) -> Dict:
        return {
            "passed": self.result.validation_passed,
            "errors": self.result.validation_errors,
            "rules_checked": 6,
        }

    def _comparison(self) -> List[Dict]:
        out = []
        for br in self.result.beam_results:
            out.append({
                "beam_id": br.beam_id,
                "old_quantity": br.old_quantity,
                "new_quantity": br.total_quantity,
                "quantity_delta": br.total_quantity - br.old_quantity,
                "old_weight_kg": round(br.old_weight_kg, 3),
                "new_weight_kg": round(br.total_weight_kg, 3),
                "weight_delta_kg": round(
                    br.total_weight_kg - br.old_weight_kg, 3
                ),
            })
        return out
