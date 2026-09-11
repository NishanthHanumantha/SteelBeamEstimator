"""
Stirrup Notation Parser — Phase SI.1 MODULE 1

Parses estimator stirrup notation strings:
  "2L-Y8@100"            → UNIFORM,  legs=2, dia=8,  spacings=[100]
  "2L-Y8@100/200/100"    → VARIABLE, legs=2, dia=8,  spacings=[100,200,100]
  "2L-Y10@150/250/150"   → VARIABLE, legs=2, dia=10, spacings=[150,250,150]
  "2L-Y8@100C/C"         → UNIFORM  (C/C suffix stripped)
  "2Y8@100"              → UNIFORM,  legs=2, dia=8
  "Y8@100"               → UNIFORM,  legs=1, dia=8
  "2Y16"  (no @)         → NOT_PARSEABLE (no spacing — keep legacy)
"""
import re
from typing import Optional

from stirrup_models import ParsedStirrupNotation, StirrupType

_LABEL_RE = re.compile(
    r"(?P<legs>\d+)?"                    # optional leg count  (2, 1)
    r"L?-?"                              # optional "L" and dash
    r"Y(?P<dia>\d+(?:\.\d+)?)"           # Y<diameter>
    r"@(?P<spacings>[\d/]+)"             # @<spacing>[/<spacing>...]
    r"(?:\s*C/?C)?",                     # optional "C/C" suffix
    re.IGNORECASE,
)


class StirrupNotationParser:
    """Deterministic parser for estimator stirrup notation strings."""

    def parse(
        self,
        label: str,
        fallback_spacing_mm: Optional[float] = None,
        fallback_diameter_mm: Optional[float] = None,
        fallback_legs: int = 2,
        fallback_grade: str = "Y",
    ) -> ParsedStirrupNotation:
        """
        Returns a ParsedStirrupNotation.
        If the label is not parseable and fallback_spacing_mm is provided,
        falls back to UNIFORM with that spacing.
        """
        label_clean = (label or "").strip()

        m = _LABEL_RE.search(label_clean)
        if not m:
            if fallback_spacing_mm and fallback_diameter_mm:
                return ParsedStirrupNotation(
                    raw_label=label_clean,
                    legs=fallback_legs,
                    diameter_mm=float(fallback_diameter_mm),
                    steel_grade=fallback_grade,
                    spacings_mm=[int(fallback_spacing_mm)],
                    stirrup_type=StirrupType.UNIFORM,
                    is_parseable=True,
                    parse_note="Parsed from fallback spacing_mm (no @notation in label)",
                )
            return ParsedStirrupNotation(
                raw_label=label_clean,
                legs=fallback_legs,
                diameter_mm=float(fallback_diameter_mm or 8),
                steel_grade=fallback_grade,
                spacings_mm=[],
                stirrup_type=StirrupType.UNIFORM,
                is_parseable=False,
                parse_note=f"Cannot parse stirrup notation: '{label_clean}'",
            )

        legs = int(m.group("legs") or fallback_legs)
        dia  = float(m.group("dia"))
        raw_spacings = m.group("spacings")
        spacings = [int(x) for x in raw_spacings.split("/") if x.isdigit()]

        stype = StirrupType.UNIFORM if len(spacings) == 1 else StirrupType.VARIABLE

        return ParsedStirrupNotation(
            raw_label=label_clean,
            legs=legs,
            diameter_mm=dia,
            steel_grade=fallback_grade,
            spacings_mm=spacings,
            stirrup_type=stype,
            is_parseable=True,
            parse_note="",
        )
