"""Development length engine. MODEL_VERSION: 8.4.0"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.4.0"


class DevelopmentLengthEngine:
    """Compute Ld from engineering context; flag if unavailable — never fabricate."""

    def __init__(self, engineering_context: Optional[Dict[str, Any]] = None):
        self._ctx = engineering_context or {}

    def compute(self, intent: Any) -> Dict[str, Any]:
        evidence: List[str] = []
        dia = int(float(getattr(intent, "diameter_mm", 0) or 0))
        if dia <= 0:
            return {
                "development_length_mm": None,
                "lap_length_mm": None,
                "development_rule": "",
                "development_source": "UNAVAILABLE",
                "hook_type": "UNKNOWN",
                "anchor_type": "UNKNOWN",
                "confidence": 0.0,
                "evidence": ["diameter_missing_ld_flagged"],
                "flagged": True,
            }

        if getattr(intent, "development_length_mm", None) is not None:
            ld = int(intent.development_length_mm)
            evidence.append("intent_development_length")
            return self._pack(ld, ld, "INTENT", "EngineeringIntent", evidence, 0.9)

        factor = self._ctx.get("dev_length_factor") or self._ctx.get(
            "fallback_dev_length_factor"
        )
        table = self._ctx.get("development_length_table")
        conc = (
            self._ctx.get("concrete_grade_beam")
            or self._ctx.get("concrete_grade")
            or "M30"
        )

        ld = None
        source = "UNAVAILABLE"
        rule = ""
        if isinstance(table, dict):
            for key, val in table.items():
                try:
                    if isinstance(key, (list, tuple)) and len(key) >= 2:
                        if str(key[0]) == str(conc) and int(key[1]) == dia:
                            ld = int(val)
                            break
                    sk = str(key)
                    if str(dia) in sk and str(conc) in sk:
                        ld = int(val)
                        break
                except Exception:
                    continue
            if ld is not None:
                source = "EngineeringContext.development_length_table"
                rule = f"table[{conc},{dia}]"
                evidence.append("dl_table_hit")

        if ld is None and factor:
            ld = int(factor) * dia
            source = "EngineeringContext.dev_length_factor"
            rule = f"{factor}*db"
            evidence.append(f"factor={factor}")

        if ld is None:
            return {
                "development_length_mm": None,
                "lap_length_mm": None,
                "development_rule": "",
                "development_source": "UNAVAILABLE",
                "hook_type": self._hook(),
                "anchor_type": "STANDARD",
                "confidence": 0.2,
                "evidence": ["ld_unavailable_flagged_not_fabricated"],
                "flagged": True,
            }

        lap = self._ctx.get("min_lap_mm")
        if lap is None:
            lap = ld
            evidence.append("lap_equals_ld")
        else:
            evidence.append("lap_from_context")

        return self._pack(ld, int(lap), rule, source, evidence, 0.85)

    def _hook(self) -> str:
        hm = self._ctx.get("hook_multiple_135") or self._ctx.get("hook_multiple")
        return f"135deg_x{hm}" if hm else "135_STANDARD"

    def _pack(self, ld, lap, rule, source, evidence, conf):
        return {
            "development_length_mm": ld,
            "lap_length_mm": lap,
            "development_rule": rule,
            "development_source": source,
            "hook_type": self._hook(),
            "anchor_type": "STANDARD",
            "confidence": conf,
            "evidence": evidence,
            "flagged": False,
        }
