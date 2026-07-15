"""
Engineering Context Loader.

The single interface through which ALL pipeline modules should access
engineering parameters.  Implements project-specific values with IS 456
constant fallbacks.

Usage:
    loader = EngineeringContextLoader(ctx)
    cover = loader.get_cover("BEAM IN SUPERSTRUCTURE")   # 30mm (from GN)
    ld    = loader.get_development_length_mm(12, "M30")  # 455mm (from GN)
    grade = loader.get_primary_steel_grade()              # "Fe550" (from GN)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from .engineering_context_model import EngineeringContext

# ---------------------------------------------------------------------------
# IS 456:2000 absolute fallback constants (kept identical to current pipeline)
# ---------------------------------------------------------------------------
_IS456_COVER_BEAM_MM        = 40   # current pipeline value (hardcoded)
_IS456_DEV_LENGTH_FACTOR    = 40   # current pipeline value (hardcoded)
_IS456_HOOK_MULTIPLE        = 10   # current pipeline value (hardcoded)
_IS456_STEEL_DENSITY        = 7850.0
_IS456_PRIMARY_STEEL        = "Fe415"
_IS456_PRIMARY_CONCRETE     = "M25"

# Element keyword normalization
_ELEMENT_ALIASES = {
    "BEAM":      "BEAM IN SUPERSTRUCTURE",
    "SLAB":      "SLAB IN SUPERSTRUCTURE",
    "COLUMN":    "COLUMNS/WALL ABOVE PLINTH",
    "FOOTING":   "FOOTING",
    "PLINTH":    "PLINTH BEAM",
    "LINTEL":    "LINTELS",
    "WALL":      "COLUMNS/WALL ABOVE PLINTH",
    "RETAINING": "RETAINING WALLS",
}


class EngineeringContextLoader:
    """
    Accessor layer for EngineeringContext.
    Falls back to IS 456 constants when GN value is unavailable.
    Records a deterministic warning for every fallback used.
    """

    def __init__(self, ctx: EngineeringContext):
        self._ctx = ctx
        self._fallback_log: List[str] = []

    @property
    def context(self) -> EngineeringContext:
        return self._ctx

    @property
    def fallback_log(self) -> List[str]:
        return list(self._fallback_log)

    # ------------------------------------------------------------------
    # Cover
    # ------------------------------------------------------------------
    def get_cover(self, element_type: str = "BEAM") -> int:
        norm = self._normalize_element(element_type)
        for rule in self._ctx.cover_rules:
            if norm in rule.element_type.upper() or rule.element_type.upper() in norm:
                return rule.cover_mm
        # fallback
        fb = self._ctx.fallback_cover_mm or _IS456_COVER_BEAM_MM
        self._warn(f"get_cover({element_type!r}): GN not found -> fallback {fb}mm")
        return fb

    # ------------------------------------------------------------------
    # Development Length
    # ------------------------------------------------------------------
    def get_development_length_mm(
        self,
        diameter_mm: int,
        concrete_grade: Optional[str] = None,
        steel_grade: Optional[str] = None,
    ) -> int:
        sg = steel_grade or self._ctx.primary_steel_grade
        cg = concrete_grade or self._ctx.fallback_concrete_grade
        key = (sg, diameter_mm, cg)
        if key in self._ctx.development_length_table:
            return self._ctx.development_length_table[key]
        # Try alternate steel grade (Fe415)
        for sg_try in self._ctx.steel_grades:
            k2 = (sg_try, diameter_mm, cg)
            if k2 in self._ctx.development_length_table:
                self._warn(
                    f"get_development_length_mm(dia={diameter_mm}, cg={cg}): "
                    f"used {sg_try} instead of {sg}"
                )
                return self._ctx.development_length_table[k2]
        # Fallback: factor x diameter
        factor = self._ctx.fallback_dev_length_factor or _IS456_DEV_LENGTH_FACTOR
        fb = factor * diameter_mm
        self._warn(
            f"get_development_length_mm(dia={diameter_mm}, cg={cg}): "
            f"GN table miss -> factor {factor}x{diameter_mm} = {fb}mm"
        )
        return fb

    def get_development_length_factor(
        self,
        concrete_grade: Optional[str] = None,
        steel_grade: Optional[str] = None,
    ) -> int:
        """Return Ld/d ratio for dia=12 (representative beam bar)."""
        sg = steel_grade or self._ctx.primary_steel_grade
        cg = concrete_grade or self._ctx.fallback_concrete_grade
        for dia in [12, 16, 10, 20, 8]:
            key = (sg, dia, cg)
            if key in self._ctx.development_length_table:
                factor = round(self._ctx.development_length_table[key] / dia)
                return factor
        fb = self._ctx.fallback_dev_length_factor or _IS456_DEV_LENGTH_FACTOR
        self._warn(
            f"get_development_length_factor(sg={sg}, cg={cg}): "
            f"GN table miss -> fallback {fb}d"
        )
        return fb

    # ------------------------------------------------------------------
    # Steel grade
    # ------------------------------------------------------------------
    def get_primary_steel_grade(self) -> str:
        if self._ctx.primary_steel_grade:
            return self._ctx.primary_steel_grade
        self._warn("get_primary_steel_grade(): GN not found -> Fe415")
        return _IS456_PRIMARY_STEEL

    def get_steel_grades(self) -> List[str]:
        return list(self._ctx.steel_grades) or [_IS456_PRIMARY_STEEL]

    # ------------------------------------------------------------------
    # Concrete grade
    # ------------------------------------------------------------------
    def get_concrete_grade(self, element_type: str = "BEAM") -> str:
        norm = self._normalize_element(element_type)
        for rule in self._ctx.cover_rules:
            if norm in rule.element_type.upper() or rule.element_type.upper() in norm:
                return rule.concrete_grade
        fb = self._ctx.fallback_concrete_grade or _IS456_PRIMARY_CONCRETE
        self._warn(f"get_concrete_grade({element_type!r}): GN not found -> {fb}")
        return fb

    # ------------------------------------------------------------------
    # Hook / bend
    # ------------------------------------------------------------------
    def get_hook_multiple(self, angle: int = 135) -> int:
        """Return Nd multiple for hook (N*d tail length)."""
        for rule in self._ctx.hook_rules:
            if rule.angle_deg == angle:
                return rule.multiplier_xd
        # Try any hook rule
        if self._ctx.hook_rules:
            return self._ctx.hook_rules[0].multiplier_xd
        self._warn(f"get_hook_multiple(angle={angle} deg): GN not found -> {_IS456_HOOK_MULTIPLE}d")
        return _IS456_HOOK_MULTIPLE

    def get_standard_bend_multiple(self) -> int:
        """Return multiplier for standard 90 deg bend (from GN DXF)."""
        for rule in self._ctx.hook_rules:
            if rule.angle_deg == 90 and "STANDARD" in rule.rule_type.upper():
                return rule.multiplier_xd
        for rule in self._ctx.hook_rules:
            if rule.angle_deg == 90:
                return rule.multiplier_xd
        self._warn("get_standard_bend_multiple(): GN not found -> 4d")
        return 4

    # ------------------------------------------------------------------
    # Lap rules
    # ------------------------------------------------------------------
    def get_minimum_lap_mm(self) -> int:
        for rule in self._ctx.lap_rules:
            if rule.rule_type == "MINIMUM_LAP" and rule.value_mm:
                return rule.value_mm
        self._warn("get_minimum_lap_mm(): GN not found -> 300mm")
        return 300

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def get_steel_density(self) -> float:
        """Steel density — always 7850 kg/m³ (physical constant)."""
        return _IS456_STEEL_DENSITY

    def summary(self) -> Dict[str, Any]:
        return {
            "primary_steel_grade": self.get_primary_steel_grade(),
            "cover_beam_mm":       self.get_cover("BEAM"),
            "concrete_grade_beam": self.get_concrete_grade("BEAM"),
            "dev_length_factor":   self.get_development_length_factor(),
            "hook_multiple_135":   self.get_hook_multiple(135),
            "bend_multiple_90":    self.get_standard_bend_multiple(),
            "min_lap_mm":          self.get_minimum_lap_mm(),
            "steel_density":       self.get_steel_density(),
            "dl_table_entries":    len(self._ctx.development_length_table),
            "cover_rule_count":    len(self._ctx.cover_rules),
            "code_references":     len(self._ctx.code_references),
            "parse_confidence":    self._ctx.parse_confidence,
            "fallback_log":        self._fallback_log,
        }

    def _normalize_element(self, element_type: str) -> str:
        up = element_type.upper().strip()
        for alias, full in _ELEMENT_ALIASES.items():
            if alias in up:
                return full.upper()
        return up

    def _warn(self, msg: str) -> None:
        self._fallback_log.append(f"[FALLBACK] {msg}")
