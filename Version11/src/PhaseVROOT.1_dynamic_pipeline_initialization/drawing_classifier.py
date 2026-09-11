"""
Phase V.ROOT.1 -- drawing_classifier.py
Classify every DXF drawing into a structural type.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

import pathlib
import re
from typing import Dict, List, Optional

# Drawing type constants
TYPE_BEAM_REINFORCEMENT = "BEAM_REINFORCEMENT"
TYPE_GENERAL_NOTES      = "GENERAL_NOTES"
TYPE_FRAMING_PLAN       = "FRAMING_PLAN"
TYPE_BEAM_SCHEDULE      = "BEAM_SCHEDULE"
TYPE_SECTION            = "SECTION"
TYPE_DETAIL             = "DETAIL"
TYPE_UNKNOWN            = "UNKNOWN"

_RULES: List[tuple] = [
    # (regex_pattern, drawing_type, priority)
    (re.compile(r'reinforcement|rebar|bending\s*detail', re.I), TYPE_BEAM_REINFORCEMENT, 10),
    (re.compile(r'framing|framing[_\s]*plan|structural[_\s]*plan|layout', re.I), TYPE_FRAMING_PLAN, 9),
    (re.compile(r'general[_\s]*notes?|specification|spec|standard', re.I), TYPE_GENERAL_NOTES, 8),
    (re.compile(r'beam[_\s]*schedule|column[_\s]*schedule|schedule', re.I), TYPE_BEAM_SCHEDULE, 7),
    (re.compile(r'section', re.I), TYPE_SECTION, 6),
    (re.compile(r'detail', re.I), TYPE_DETAIL, 5),
]


class DrawingClassifier:
    """Classify DXF files without reading their content (filename-based)."""

    def classify(self, dxf_path: pathlib.Path) -> str:
        candidate = (dxf_path.stem + ' ' + dxf_path.parent.name).lower()
        best_type  = TYPE_UNKNOWN
        best_prio  = -1

        for pattern, dtype, priority in _RULES:
            if pattern.search(candidate) and priority > best_prio:
                best_type = dtype
                best_prio = priority

        return best_type

    def classify_all(self, dxf_paths: List[pathlib.Path]) -> Dict[str, str]:
        return {str(p): self.classify(p) for p in dxf_paths}

    def primary_reinforcement_drawing(
        self, classified: Dict[str, str]
    ) -> Optional[pathlib.Path]:
        """Return the single best beam reinforcement DXF."""
        candidates = [
            pathlib.Path(p)
            for p, t in classified.items()
            if t == TYPE_BEAM_REINFORCEMENT
        ]
        if not candidates:
            return None
        # Prefer the largest file (likely most detailed)
        return max(candidates, key=lambda p: p.stat().st_size if p.exists() else 0)

    def primary_framing_drawing(
        self, classified: Dict[str, str]
    ) -> Optional[pathlib.Path]:
        candidates = [
            pathlib.Path(p)
            for p, t in classified.items()
            if t == TYPE_FRAMING_PLAN
        ]
        return candidates[0] if candidates else None
