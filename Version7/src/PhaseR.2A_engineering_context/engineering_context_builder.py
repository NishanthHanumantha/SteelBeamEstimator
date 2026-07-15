"""
Engineering Context Builder — builder pattern for EngineeringContext.

Orchestrates all parsers, assembles their outputs, and produces the
frozen EngineeringContext instance.
"""
from __future__ import annotations
import pathlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .general_notes_text_extractor import GeneralNotesTextExtractor
from .general_notes_classifier     import GeneralNotesClassifier
from .development_length_parser    import DevelopmentLengthParser
from .cover_parser                 import CoverParser
from .steel_grade_parser           import SteelGradeParser
from .concrete_grade_parser        import ConcreteGradeParser
from .hook_rule_parser             import HookRuleParser
from .lap_rule_parser              import LapRuleParser
from .engineering_context_model    import (
    EngineeringContext, DevelopmentLengthEntry,
    CoverRule, HookBendRule, LapRule, SpacerRule, CodeReference,
)

import re

_IS_CODE_PAT = re.compile(r"(IS\s*\d+(?:[-:]\s*\d{4})?|SP\s*\d+)", re.I)
_SPACER_PAT  = re.compile(r"SPACER\s+BARS\s+SHALL\s+BE\s+PROVIDED", re.I)


class EngineeringContextBuilder:
    """
    Builds an immutable EngineeringContext from the General Notes DXF.
    """

    def __init__(self, gn_dxf_path: pathlib.Path, project_id: str = "UNKNOWN"):
        self._path = gn_dxf_path
        self._project_id = project_id
        self._warnings: List[str] = []

    def build(self) -> EngineeringContext:
        extractor = GeneralNotesTextExtractor(self._path)
        _ = extractor.extract()     # warm up

        # --- Run steel parser first so we can pass project grade to DL parser ---
        cover_parser = CoverParser(extractor)
        steel_parser = SteelGradeParser(extractor)
        conc_parser  = ConcreteGradeParser(extractor)
        hook_parser  = HookRuleParser(extractor)
        lap_parser   = LapRuleParser(extractor)

        steel_grades, primary_steel, sg_warn = steel_parser.parse()

        # Pass project primary steel grade so IS456 values are computed for it
        dl_parser = DevelopmentLengthParser(
            extractor, project_steel_grades=[primary_steel]
        )

        # --- Parse ---
        dl_entries, dl_warn, dl_audit   = dl_parser.parse()
        self._dl_audit = dl_audit        # store for orchestrator
        cover_rules, cv_warn            = cover_parser.parse()
        conc_grades, elem_map, cg_warn = conc_parser.parse()
        hook_rules, hk_warn   = hook_parser.parse()
        lap_rules, lp_warn    = lap_parser.parse()

        # Collect all warnings
        for w in dl_warn + cv_warn + sg_warn + cg_warn + hk_warn + lp_warn:
            self._warnings.append(w)

        # --- Spacer rules ---
        spacer_rules = self._extract_spacer_rules(extractor)

        # --- Code references ---
        code_refs = self._extract_code_references(extractor)

        # --- Development length lookup dict ---
        dl_dict = {
            (e.steel_grade, e.diameter_mm, e.concrete_grade): e.length_mm
            for e in dl_entries
        }

        # --- Compute fallback values from parsed data ---
        beam_cover = self._get_beam_cover(cover_rules)
        beam_conc  = elem_map.get("BEAM IN SUPERSTRUCTURE", "M30")
        primary_dl_factor = self._compute_dl_factor(dl_dict, primary_steel, beam_conc)

        # --- Confidence ---
        confidence = self._compute_confidence(
            dl_entries, cover_rules, steel_grades, conc_grades,
            hook_rules, lap_rules,
        )

        return EngineeringContext(
            gn_dxf_path   = str(self._path),
            project_id    = self._project_id,
            parsed_at     = datetime.utcnow().isoformat(),
            steel_grades  = tuple(sorted(set(steel_grades + [primary_steel]))),
            primary_steel_grade = primary_steel,
            concrete_grades     = tuple(sorted(set(conc_grades), key=lambda g: int(g[1:]))),
            development_length_table = dl_dict,
            cover_rules    = tuple(cover_rules),
            hook_rules     = tuple(hook_rules),
            lap_rules      = tuple(lap_rules),
            spacer_rules   = tuple(spacer_rules),
            code_references= tuple(code_refs),
            warnings       = tuple(self._warnings),
            parse_confidence = confidence,
            fallback_dev_length_factor = primary_dl_factor,
            fallback_cover_mm          = beam_cover,
            fallback_steel_grade       = primary_steel,
            fallback_concrete_grade    = beam_conc,
        )

    # ------------------------------------------------------------------
    def _get_beam_cover(self, cover_rules: List[CoverRule]) -> int:
        for rule in cover_rules:
            if "BEAM IN SUPER" in rule.element_type.upper():
                return rule.cover_mm
        for rule in cover_rules:
            if "BEAM" in rule.element_type.upper():
                return rule.cover_mm
        return 30   # IS 456 beam default

    def _compute_dl_factor(
        self,
        dl_dict: Dict,
        steel_grade: str,
        concrete_grade: str,
    ) -> int:
        """Compute representative Ld/diameter ratio for a typical beam bar."""
        # Use dia=12 as the representative diameter for beams
        for dia in [12, 16, 10, 20, 8]:
            key = (steel_grade, dia, concrete_grade)
            if key in dl_dict:
                return round(dl_dict[key] / dia)
        # Try any steel grade
        for key, length in dl_dict.items():
            if key[1] == 12 and key[2] == concrete_grade:
                return round(length / key[1])
        return 40   # IS 456 absolute default

    def _extract_spacer_rules(
        self, extractor: GeneralNotesTextExtractor
    ) -> List[SpacerRule]:
        rules = []
        for item in extractor.extract():
            if _SPACER_PAT.search(item.text):
                rules.append(SpacerRule(
                    description=item.text[:200],
                    source=f"GN_DXF layer={item.layer}",
                ))
        return rules

    def _extract_code_references(
        self, extractor: GeneralNotesTextExtractor
    ) -> List[CodeReference]:
        seen = set()
        refs = []
        for item in extractor.extract():
            for m in _IS_CODE_PAT.finditer(item.text):
                code = re.sub(r"\s+", " ", m.group(0)).strip()
                if code not in seen:
                    seen.add(code)
                    refs.append(CodeReference(
                        code=code,
                        context=item.text[:80],
                        source=f"GN_DXF layer={item.layer}",
                    ))
        return refs

    def _compute_confidence(
        self,
        dl_entries, cover_rules, steel_grades,
        conc_grades, hook_rules, lap_rules,
    ) -> float:
        score = 0.0
        checks = [
            len(dl_entries) >= 10,       # at least 2 diameters × 5 grades
            len(cover_rules) >= 3,       # at least 3 element types
            len(steel_grades) >= 1,      # at least one steel grade
            len(conc_grades) >= 1,       # at least one concrete grade
            len(hook_rules) >= 1,        # at least one hook rule
            len(lap_rules) >= 1,         # at least one lap rule
        ]
        score = sum(checks) / len(checks)
        return round(score, 3)

    @property
    def dl_audit(self) -> dict:
        """Development-length parse audit metadata from the last build()."""
        return getattr(self, "_dl_audit", {})
