"""STEP 7 — Build deterministic engineering vocabulary database."""
from __future__ import annotations

from typing import Dict, List

from .notation_models import NotationGroup, PriorityItem, VocabularyEntry

# Impact heuristics for R.2.1 priority (discovery ranking only)
_HIGH_IMPACT = {
    "S.F.R.", "O.E.F.", "BOTH FACE", "ON BOTH FACE", "NEAR FACE", "FAR FACE",
    "EACH FACE", "T.O.F.", "B.O.F.",
}
_MEDIUM_IMPACT = {
    "Ld", "Lap", "Hook", "Bend", "Anchor", "Crank", "Spacer", "U-BAR",
    "ZONE_SPACING", "PAREN_MODIFIER", "N.F.", "F.F.", "FACE",
}


class NotationInventoryDatabase:

    def build(
        self,
        groups: List[NotationGroup],
        categories: Dict[str, str],
        support: Dict[str, Dict],
        symbols: Dict[str, Dict],
    ) -> List[VocabularyEntry]:
        entries: List[VocabularyEntry] = []
        by_notation = symbols.get("by_notation", {})
        for g in groups:
            cat = categories.get(g.normalized_notation, "UNKNOWN")
            sup = support.get(g.normalized_notation, {})
            sym = by_notation.get(g.normalized_notation, {})
            status = sup.get("support_status", "UNKNOWN")
            reason = sup.get("support_reason", "")
            impact = self._impact(g.normalized_notation, status, cat, g.frequency)
            entries.append(VocabularyEntry(
                notation=g.normalized_notation,
                normalized_notation=g.normalized_notation,
                category=cat,
                frequency=g.frequency,
                support_status=status,
                support_reason=reason,
                example_text=g.example_texts[0] if g.example_texts else "",
                beam_ids=g.beam_ids,
                drawing_ids=g.drawing_ids,
                entity_ids=g.entity_ids[:50],
                first_seen=g.entity_ids[0] if g.entity_ids else "",
                recommendation=self._recommendation(g.normalized_notation, status, cat),
                is_engineering_symbol=bool(sym.get("is_engineering_symbol")),
                impact=impact,
            ))
        entries.sort(key=lambda e: (-e.frequency, e.normalized_notation))
        return entries

    def build_priorities(
        self, entries: List[VocabularyEntry]
    ) -> List[PriorityItem]:
        candidates = [
            e for e in entries
            if e.support_status in ("UNSUPPORTED", "PARTIALLY_SUPPORTED")
            and e.category not in ("TITLE", "GENERAL_NOTE", "DRAWING", "GEOMETRY")
        ]
        # Rank: HIGH impact first, then frequency
        impact_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        candidates.sort(
            key=lambda e: (impact_rank.get(e.impact, 3), -e.frequency, e.notation)
        )
        priorities = []
        for i, e in enumerate(candidates[:25], start=1):
            priorities.append(PriorityItem(
                priority=i,
                notation=e.notation,
                impact=e.impact,
                reason=e.recommendation or e.support_reason,
                frequency=e.frequency,
                category=e.category,
            ))
        return priorities

    @staticmethod
    def _impact(notation: str, status: str, category: str, frequency: int) -> str:
        if status == "SUPPORTED":
            return "NONE"
        if category == "GEOMETRY":
            return "LOW"
        if notation in _HIGH_IMPACT or notation.upper().startswith("S.F.R"):
            return "HIGH"
        if notation.upper() in ("(O.E.F)", "(O.E.F.)"):
            return "HIGH"
        if any(notation.startswith(p) or notation == p for p in _MEDIUM_IMPACT):
            return "MEDIUM"
        if category in ("REINFORCEMENT_ROLE", "MODIFIER", "DEVELOPMENT", "POSITION"):
            return "HIGH" if frequency >= 1 else "MEDIUM"
        if status == "UNSUPPORTED" and frequency >= 3:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _recommendation(notation: str, status: str, category: str) -> str:
        if status == "SUPPORTED":
            return "No action required"
        recs = {
            "S.F.R.": "Implement SIDE_FACE_REINFORCEMENT role classifier in Phase R.2.1",
            "O.E.F.": "Implement One-Each-Face quantity multiplier in Phase R.2.1",
            "BOTH FACE": "Map face phrase to dual-face quantity rule in Phase R.2.1",
            "ON BOTH FACE": "Map face phrase to dual-face quantity rule in Phase R.2.1",
            "NEAR FACE": "Map near-face position modifier in Phase R.2.1",
            "FAR FACE": "Map far-face position modifier in Phase R.2.1",
            "EACH FACE": "Map each-face quantity multiplier in Phase R.2.1",
            "T.O.F.": "Implement Top-of-Face modifier in Phase R.2.1",
            "B.O.F.": "Implement Bottom-of-Face modifier in Phase R.2.1",
            "Ld": "Parse development length notation in Phase R.2.1",
            "Lap": "Parse lap splice notation in Phase R.2.1",
            "Hook": "Parse hook modifier in Phase R.2.1",
            "Spacer": "Add spacer notation discovery in Phase R.2.1",
            "U-BAR": "Classify U-bar reinforcement role in Phase R.2.1",
        }
        if notation in recs:
            return recs[notation]
        if category == "DEVELOPMENT":
            return f"Add development/detailing parser for '{notation}' in Phase R.2.1"
        if category == "MODIFIER":
            return f"Interpret modifier '{notation}' in Phase R.2.1"
        if category == "POSITION":
            return f"Map position symbol '{notation}' in Phase R.2.1"
        if status == "PARTIALLY_SUPPORTED":
            return f"Extend semantic handling for '{notation}' beyond regex match"
        return f"Evaluate '{notation}' for Phase R.2.1 semantic coverage"
