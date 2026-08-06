"""
evidence_builder.py — Build ObservableEvidence from a R.2.1C EngineeringFact dict.
MODEL_VERSION: 7.12.1

Only observable drawing information is captured.
No engineering assumptions, inferences, or intent conclusions are included.

Observable means:
  - Directly readable from annotation text
  - Directly readable from position zone
  - Directly readable from R.1 classifier signal (the classification, not its interpretation)
  - Directly readable from semantic modifier detection

NOT observable:
  - Engineering meaning (TOP_MAIN, BOTTOM_EXTRA, ...)
  - Support position
  - Bar extent
  - Span continuity
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .evidence_models import (
    ObservableEvidence,
    PLACEMENT_TO_ZONE,
    ZONE_UNKNOWN,
    SOURCE_UNKNOWN,
)

# Pattern to extract zone from R.2.1B engineering_notes
_ZONE_PATTERN = re.compile(r"zone\s+([A-Z_]+ZONE)", re.IGNORECASE)

# Pattern to extract placement source from notes
_PLACEMENT_SRC_PATTERN = re.compile(
    r"Placement\s+(from|overridden|from zone)\s+(.+?)(?:\s*->|\s*$)", re.IGNORECASE
)


class EvidenceBuilder:
    """
    Build ObservableEvidence from a R.2.1C fact dict.

    All fields are populated purely from observable drawing data.
    """

    def build(self, fact_dict: Dict[str, Any]) -> ObservableEvidence:
        eso  = fact_dict.get("original_semantic_object") or {}
        notes: List[str] = []

        # ── Annotation text ───────────────────────────────────────────────────
        original_text = str(eso.get("raw_text") or "").strip()
        clean_text    = str(fact_dict.get("clean_text") or "").strip()
        if not original_text:
            original_text = clean_text  # raw_text may be empty in some ESOs

        # ── Annotation zone ───────────────────────────────────────────────────
        annotation_zone = self._extract_zone(eso, fact_dict)

        # ── Role source ───────────────────────────────────────────────────────
        role_source = self._extract_role_source(eso, fact_dict)

        # ── Placement source ──────────────────────────────────────────────────
        placement_source = self._extract_placement_source(eso, fact_dict)

        # ── R.1 original role ─────────────────────────────────────────────────
        r1_original_role = str(eso.get("original_r1_role") or "UNKNOWN").strip()

        # ── Confidence source ─────────────────────────────────────────────────
        confidence_source = str(
            fact_dict.get("source") or eso.get("source") or SOURCE_UNKNOWN
        ).strip()

        # ── Observation notes ─────────────────────────────────────────────────
        notes.append(f"clean_text observed: {clean_text!r}")
        if r1_original_role and r1_original_role != "UNKNOWN":
            notes.append(f"R.1 signal observed: {r1_original_role!r}")
        mods = list(fact_dict.get("modifiers") or [])
        if mods:
            notes.append(f"Modifiers observed: {mods}")
        flags = list(fact_dict.get("semantic_flags") or [])
        if flags:
            notes.append(f"Semantic flags observed: {flags}")
        dia = float(fact_dict.get("diameter") or 0.0)
        if dia > 0:
            notes.append(f"Diameter observed: {dia}mm")
        qty = int(fact_dict.get("quantity") or 0)
        if qty > 0:
            notes.append(f"Quantity observed: {qty}")
        spc = fact_dict.get("spacing")
        if spc is not None:
            notes.append(f"Spacing observed: {spc}mm")

        return ObservableEvidence(
            annotation_id    = str(fact_dict.get("annotation_id") or ""),
            beam_id          = str(fact_dict.get("beam_id") or ""),
            original_text    = original_text,
            clean_text       = clean_text,
            role_source      = role_source,
            placement_source = placement_source,
            quantity         = qty,
            diameter         = dia,
            grade            = str(fact_dict.get("grade") or "Y460"),
            spacing          = spc,
            modifiers        = mods,
            semantic_flags   = flags,
            annotation_zone  = annotation_zone,
            r1_original_role = r1_original_role,
            confidence_source= confidence_source,
            notes            = notes,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _extract_zone(self, eso: Dict[str, Any], fact_dict: Dict[str, Any]) -> str:
        """Derive annotation zone from ESO notes or placement."""
        # Try to find zone in ESO engineering_notes first
        for note in (eso.get("engineering_notes") or []):
            m = _ZONE_PATTERN.search(str(note))
            if m:
                return m.group(1).upper()

        # Fallback: derive from fact placement
        placement = str(fact_dict.get("placement") or "UNKNOWN")
        return PLACEMENT_TO_ZONE.get(placement, ZONE_UNKNOWN)

    def _extract_role_source(
        self, eso: Dict[str, Any], fact_dict: Dict[str, Any]
    ) -> str:
        """Derive the observable source of role classification."""
        source = str(fact_dict.get("source") or eso.get("source") or SOURCE_UNKNOWN)
        # Look for role-specific note in ESO
        for note in (eso.get("engineering_notes") or []):
            n = str(note).lower()
            if "dictionary" in n and "role" in n:
                return "SEMANTIC_DICTIONARY"
            if "modifier" in n and "role" in n:
                return "EXPLICIT_MODIFIER"
            if "r.1 classifier" in n or "r1" in n and "role" in n:
                return "R1_CLASSIFIER"
        return source

    def _extract_placement_source(
        self, eso: Dict[str, Any], fact_dict: Dict[str, Any]
    ) -> str:
        """Derive the observable source of placement determination."""
        for note in (eso.get("engineering_notes") or []):
            n = str(note).lower()
            if "zone" in n and "placement" in n:
                return "POSITION_ZONE"
            if "modifier" in n and "placement" in n:
                return "EXPLICIT_MODIFIER"
            if "override" in n and "placement" in n:
                return "ROLE_OVERRIDE"
        return "POSITION_ZONE"
