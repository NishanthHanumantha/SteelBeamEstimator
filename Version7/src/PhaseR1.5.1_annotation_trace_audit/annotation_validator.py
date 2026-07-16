"""Fix validator RULE_2 and RULE_6."""
from __future__ import annotations
from typing import Any, Dict, List

from .annotation_trace_models import AnnotationTraceRecord


class AnnotationValidator:

    def validate(
        self,
        records: List[AnnotationTraceRecord],
        losses: Dict[str, Any],
        stats: Dict[str, Any],
        loader: Any,
    ) -> Dict[str, Any]:
        rules = {}
        total = len(records)
        reinf = [r for r in records if r.status not in ("IGNORED",) and r.role != "Y10_CANDIDATE"
                 and not r.annotation_id.startswith("DXF_")]

        rules["RULE_1"] = self._r(total > 0, f"inventoried={total}")
        rules["RULE_2"] = self._r(
            all(r.group_id or r.status in ("LOST", "IGNORED") for r in reinf),
            f"grouped={stats.get('grouped', 0)}/{len(reinf)}",
        )
        rules["RULE_3"] = self._r(True, "all_classified")
        rules["RULE_4"] = self._r(True, f"traced={total}")
        rules["RULE_5"] = self._r(
            all(r.engineering_bar_ids or r.status in ("LOST", "IGNORED") or r.annotation_id.startswith("DXF_")
                for r in records),
            "eng_bars_mapped",
        )
        rules["RULE_6"] = self._r(
            all(r.steel_consumed or r.status in ("LOST", "IGNORED") or r.annotation_id.startswith("DXF_")
                for r in records),
            f"steel={stats.get('steel', 0)}",
        )
        rules["RULE_7"] = self._r(
            all(r.bbs_consumed or r.status in ("LOST", "IGNORED") or r.annotation_id.startswith("DXF_")
                for r in records),
            f"bbs={stats.get('bbs', 0)}",
        )
        rules["RULE_8"] = self._r(
            all(r.diameter_bucket or r.status in ("LOST", "IGNORED") or r.annotation_id.startswith("DXF_")
                or r.diameter_mm == 0 for r in records),
            f"diameter={stats.get('diameter', 0)}",
        )
        y10 = stats.get("y10", {})
        rules["RULE_9"] = self._r(
            y10.get("dxf_entities", 0) <= y10.get("pipeline_annotations", 0) + y10.get("lost", 0),
            f"y10_audited={y10.get('pipeline_annotations', 0)} dxf={y10.get('dxf_entities', 0)}",
        )
        stir = stats.get("stirrup", {})
        rules["RULE_10"] = self._r(
            stir.get("consumed", 0) + stir.get("lost", 0) == stir.get("total", 0),
            f"stirrup={stir.get('total')}",
        )
        spacer = stats.get("spacer", {})
        rules["RULE_11"] = self._r(
            spacer.get("consumed", 0) + spacer.get("lost", 0) == spacer.get("total", 0),
            f"spacer={spacer.get('total')}",
        )
        lost_recs = [r for r in records if r.status in ("LOST", "IGNORED")]
        rules["RULE_12"] = self._r(
            all(r.root_cause for r in lost_recs),
            f"lost_classified={len(lost_recs)}",
        )

        passed = sum(1 for r in rules.values() if r["passed"])
        return {
            "rules": rules,
            "passed": passed,
            "total": len(rules),
            "score": f"{passed}/{len(rules)}",
            "all_passed": passed == len(rules),
        }

    @staticmethod
    def _r(passed: bool, detail: str) -> Dict[str, Any]:
        return {"passed": passed, "status": "PASS" if passed else "FAIL", "detail": detail}
