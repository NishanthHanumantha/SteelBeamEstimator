"""
engineering_fact_builder.py — Build EngineeringFact from R.2.1B ESO.
MODEL_VERSION: 7.12.0

Orchestrates the normalization pipeline for one ESO:
  RoleNormalizer
  → PlacementNormalizer
  → IntentNormalizer
  → SemanticCandidateBuilder
  → ConfidenceNormalizer
  → EngineeringFact
"""
from __future__ import annotations

from typing import Any, Dict, List

from .confidence_normalizer import ConfidenceNormalizer
from .fact_models import INTENT_UNKNOWN, EngineeringFact
from .intent_normalizer import IntentNormalizer
from .placement_normalizer import PlacementNormalizer
from .role_normalizer import RoleNormalizer
from .semantic_candidate_builder import SemanticCandidateBuilder


class EngineeringFactBuilder:
    """
    Converts one R.2.1B EngineeringSemanticObject dict into an EngineeringFact.
    """

    def __init__(self):
        self._role_norm     = RoleNormalizer()
        self._place_norm    = PlacementNormalizer()
        self._intent_norm   = IntentNormalizer()
        self._cand_builder  = SemanticCandidateBuilder()
        self._conf_norm     = ConfidenceNormalizer()

    def build(self, eso: Dict[str, Any]) -> EngineeringFact:
        """Convert one ESO dict to an EngineeringFact."""
        notes: List[str] = []

        # Step 1 — Role
        role, role_notes = self._role_norm.normalize(eso)
        notes.extend(role_notes)

        # Step 2 — Placement
        placement, place_notes = self._place_norm.normalize(eso, role)
        notes.extend(place_notes)

        # Step 3 — Intent (remove premature, generate candidates)
        eso_meaning = eso.get("engineering_meaning") or "UNKNOWN"
        intent, base_candidates, deferred_reason, geometry_req, intent_notes = (
            self._intent_norm.normalize(role, placement, eso_meaning)
        )
        notes.extend(intent_notes)

        # Step 4 — Semantic candidate refinement
        modifiers      = list(eso.get("modifiers") or [])
        semantic_flags = list(eso.get("semantic_flags") or [])
        refined_candidates, cand_notes = self._cand_builder.refine(
            base_candidates, role, placement, modifiers, semantic_flags, eso
        )
        notes.extend(cand_notes)

        # Step 5 — Confidence (role + placement only)
        confidence, conf_notes = self._conf_norm.normalize(eso, role, placement)
        notes.extend(conf_notes)

        # Assemble preserved quantities
        quantity = int(eso.get("quantity") or 0)
        diameter = float(eso.get("diameter") or 0.0)
        grade    = str(eso.get("grade") or "Y460")
        spacing  = eso.get("spacing")

        return EngineeringFact(
            annotation_id          = str(eso.get("annotation_id") or ""),
            beam_id                = str(eso.get("beam_id") or ""),
            clean_text             = str(eso.get("clean_text") or ""),
            quantity               = quantity,
            diameter               = diameter,
            grade                  = grade,
            spacing                = spacing,
            role                   = role,
            placement              = placement,
            intent                 = INTENT_UNKNOWN,
            intent_candidates      = refined_candidates,
            modifiers              = modifiers,
            semantic_flags         = semantic_flags,
            confidence             = confidence,
            source                 = str(eso.get("source") or "UNKNOWN"),
            engineering_notes      = notes,
            original_semantic_object = eso,
            intent_deferred_reason = deferred_reason,
            geometry_required      = geometry_req,
        )

    def build_all(
        self,
        esos_by_beam: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[EngineeringFact]]:
        """Build engineering facts for all beams."""
        result: Dict[str, List[EngineeringFact]] = {}
        for beam_id, esos in esos_by_beam.items():
            facts = []
            for eso in esos:
                # Ensure beam_id is in the ESO dict
                if not eso.get("beam_id"):
                    eso = {**eso, "beam_id": beam_id}
                facts.append(self.build(eso))
            result[beam_id] = facts
        return result
