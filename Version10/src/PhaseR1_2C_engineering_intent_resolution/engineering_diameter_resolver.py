"""
EngineeringDiameterResolver — deterministic diameter from label + cluster evidence.
MODEL_VERSION: 8.3.2
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "8.3.2"

_LABEL_RE = re.compile(r"(\d+)\s*[-]?\s*[YRyTt]\s*(\d+)", re.I)


def parse_label(label: str) -> Tuple[Optional[int], Optional[float]]:
    if not label:
        return None, None
    m = _LABEL_RE.search(label.replace(" ", ""))
    if not m:
        return None, None
    return int(m.group(1)), float(m.group(2))


class EngineeringDiameterResolver:
    """Resolve diameter without nearest-text guessing."""

    def resolve(
        self,
        ann: Dict[str, Any],
        neighbours: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        evidence: List[str] = []
        label = str(ann.get("bar_label") or ann.get("clean_text") or "")
        qty_l, dia_l = parse_label(label)
        dia_field = ann.get("diameter_mm")
        conf = 0.5
        dia = None
        qty = int(ann.get("quantity") or 0) or None

        if dia_l is not None:
            dia = dia_l
            conf = 0.92
            evidence.append(f"label_parse:{label}->{dia_l}")
            if qty_l is not None:
                qty = qty_l
                evidence.append(f"label_qty:{qty_l}")

        if dia_field is not None:
            dia_f = float(dia_field)
            if dia is None:
                dia = dia_f
                conf = 0.8
                evidence.append("annotation_diameter_field")
            elif abs(dia_f - dia) < 0.1:
                conf = min(0.99, conf + 0.05)
                evidence.append("label_field_agree")
            else:
                # Prefer explicit label over field when they disagree
                evidence.append(f"field_conflict:{dia_f}_kept_label:{dia}")
                conf = max(0.6, conf - 0.1)

        # Grouped callouts with same label reinforce diameter
        if neighbours:
            same = [
                float(n.get("diameter_mm") or 0)
                for n in neighbours
                if str(n.get("bar_label") or "") == label and n.get("diameter_mm")
            ]
            if same:
                mode = Counter(int(d) for d in same).most_common(1)[0][0]
                if dia is None:
                    dia = float(mode)
                    conf = 0.75
                    evidence.append(f"neighbour_mode:{mode}")
                elif abs(float(mode) - float(dia)) < 0.1:
                    conf = min(0.99, conf + 0.03)
                    evidence.append("neighbour_mode_agrees")

        if dia is None:
            dia = 8.0
            conf = 0.2
            evidence.append("fallback_default_8")

        return {
            "diameter_mm": float(dia),
            "quantity": int(qty or 1),
            "confidence": round(conf, 4),
            "evidence": evidence,
            "bar_label": label,
        }
