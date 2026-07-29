"""STEP 6 — Determine production parser support status (read-only regex check)."""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
import types
from typing import Dict, List, Tuple

from .notation_models import NotationGroup


def _load_production_regex():
    """Read-only load of R.1 annotation_discovery regex patterns."""
    src = pathlib.Path(__file__).resolve().parent.parent
    pkg_dir = src / "PhaseR.1_generalized_reinforcement_discovery"
    pkg_name = "PhaseR1_readonly_for_r201"

    if pkg_name not in sys.modules:
        pkg_mod = types.ModuleType(pkg_name)
        pkg_mod.__path__ = [str(pkg_dir)]
        pkg_mod.__package__ = pkg_name
        sys.modules[pkg_name] = pkg_mod

    def _load(name: str):
        full = f"{pkg_name}.{name}"
        if full in sys.modules:
            return sys.modules[full]
        spec = importlib.util.spec_from_file_location(full, pkg_dir / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[full] = mod
        spec.loader.exec_module(mod)
        return mod

    _load("reinforcement_models")
    ann = _load("annotation_discovery")
    return ann._RE_BAR, ann._RE_STIRRUP, ann._RE_COMPOSITE, ann._is_noise


class NotationSupportAnalyzer:

    def __init__(self):
        self._re_bar, self._re_stirrup, self._re_composite, self._is_noise = (
            _load_production_regex()
        )

    def analyze(
        self,
        groups: List[NotationGroup],
        categories: Dict[str, str],
        symbols: Dict[str, Dict],
    ) -> Dict[str, Dict]:
        result = {}
        for g in groups:
            status, reason = self._status(
                g.normalized_notation,
                categories.get(g.normalized_notation, "UNKNOWN"),
                symbols.get("by_notation", {}).get(g.normalized_notation, {}),
            )
            result[g.normalized_notation] = {
                "support_status": status,
                "support_reason": reason,
            }
        return result

    def _status(
        self, notation: str, category: str, symbol_info: Dict
    ) -> Tuple[str, str]:
        if self._is_noise(notation):
            return "UNKNOWN", "Filtered as noise by production _NOISE_PATTERNS"

        if self._re_composite.match(notation):
            return "SUPPORTED", "Matched by production RE_COMPOSITE"
        if self._re_stirrup.search(notation):
            return "SUPPORTED", "Matched by production RE_STIRRUP"
        if self._re_bar.search(notation):
            # Bar matched but modifiers/roles may be ignored
            if category in ("MODIFIER", "REINFORCEMENT_ROLE", "POSITION", "DEVELOPMENT"):
                return "PARTIALLY_SUPPORTED", "RE_BAR matches diameter/qty; semantic ignored"
            if re.search(r"\([^)]+\)", notation) or "S.F.R" in notation.upper():
                return "PARTIALLY_SUPPORTED", "RE_BAR matches core; modifiers/roles ignored"
            return "SUPPORTED", "Matched by production RE_BAR"

        family = symbol_info.get("symbol_family", "")
        if category == "GEOMETRY" or family == "BEAM_SECTION":
            return "UNKNOWN", "Beam section/geometry label; not a reinforcement callout"
        if category == "DRAWING":
            return "UNKNOWN", "Drawing annotation; not a reinforcement callout"
        if category in ("TITLE", "GENERAL_NOTE"):
            return "UNKNOWN", "Title/note text; not a reinforcement callout"

        # Pure engineering symbols without bar/stirrup
        if symbol_info.get("is_engineering_symbol"):
            if family in ("S.F.R.",):
                return "UNSUPPORTED", "No semantic classifier for side-face role"
            if family in ("O.E.F.", "T.O.F.", "B.O.F.", "PAREN_MODIFIER"):
                return "UNSUPPORTED", "No quantity/face modifier interpretation"
            if family in ("FACE", "FACE_PHRASE", "N.F.", "F.F."):
                return "UNSUPPORTED", "No face-position semantic classifier"
            if family in ("Ld", "Lap", "Hook", "Bend", "Anchor", "Crank", "DEV"):
                return "UNSUPPORTED", "No development-length semantic parser"
            if family in ("Spacer",):
                return "UNSUPPORTED", "No spacer notation regex (geometry-inferred only)"
            if family in ("CONT", "TYP."):
                return "UNKNOWN", "Drawing annotation; not a reinforcement callout"
            if family in ("ZONE_SPACING",):
                return "UNSUPPORTED", "Zone-split spacing not parsed as standalone"
            return "UNSUPPORTED", "Engineering symbol without production regex support"

        return "UNKNOWN", "No matching production regex or known engineering symbol"
