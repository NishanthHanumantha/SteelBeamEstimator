"""
semantic_interpreter.py — Orchestrate the semantic interpretation pipeline.
MODEL_VERSION: 7.11.0

Pipeline per annotation:
  annotation dict
  ↓  SemanticContextBuilder        (gather all facts)
  ↓  SemanticModifierParser        (detect O.E.F., S.F.R., BOTH FACE, etc.)
  ↓  SemanticRoleResolver          (determine role from modifier > dict > regex)
  ↓  SemanticQuantityResolver      (preserve qty without multiplication)
  ↓  SemanticPlacementResolver     (NEAR/FAR/BOTH/SIDE/TOP/BOTTOM)
  ↓  SemanticConflictResolver      (adjudicate conflicts, set confidence/source)
  ↓  EngineeringMeaningBuilder     (produce final EngineeringSemanticObject)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .engineering_meaning_builder import EngineeringMeaningBuilder
from .semantic_conflict_resolver import SemanticConflictResolver
from .semantic_context_builder import SemanticContextBuilder
from .semantic_models import EngineeringSemanticObject
from .semantic_modifier_parser import SemanticModifierParser
from .semantic_placement_resolver import SemanticPlacementResolver
from .semantic_quantity_resolver import SemanticQuantityResolver
from .semantic_role_resolver import SemanticRoleResolver

log = logging.getLogger(__name__)


class SemanticInterpreter:
    """
    Converts a single R.1 annotation dict + semantic dictionary into an
    EngineeringSemanticObject with full engineering meaning.
    """

    def __init__(self, dictionary_entries: Dict[str, Any], vocabulary_map: Dict[str, str]):
        self._entries   = dictionary_entries
        self._vocab     = vocabulary_map

        self._ctx_builder    = SemanticContextBuilder()
        self._mod_parser     = SemanticModifierParser()
        self._role_resolver  = SemanticRoleResolver()
        self._qty_resolver   = SemanticQuantityResolver()
        self._place_resolver = SemanticPlacementResolver()
        self._conflict       = SemanticConflictResolver()
        self._meaning_builder= EngineeringMeaningBuilder()

    def interpret(self, annotation: Dict[str, Any]) -> EngineeringSemanticObject:
        """Interpret one annotation and return its EngineeringSemanticObject."""

        # Step 1 — Build context (facts only)
        ctx = self._ctx_builder.build(annotation, self._entries, self._vocab)

        # Step 2 — Parse modifiers from text
        modifiers = self._mod_parser.parse(ctx.clean_text, ctx.raw_text)

        # Step 3 — Resolve role
        semantic_role, role_source, role_notes = self._role_resolver.resolve(ctx, modifiers)

        # Step 4 — Resolve quantity
        quantity, qty_notes = self._qty_resolver.resolve(ctx, modifiers)

        # Step 5 — Resolve placement
        placement, place_notes = self._place_resolver.resolve(ctx, modifiers, semantic_role)

        # Step 6 — Adjudicate conflicts
        dict_meaning = None
        if ctx.dictionary_entry:
            dict_meaning = ctx.dictionary_entry.get("engineering_meaning")
        conflict_result = self._conflict.resolve(ctx, modifiers, role_source, dict_meaning)

        # Step 7 — Build final semantic object
        eso = self._meaning_builder.build(
            ctx           = ctx,
            modifiers     = modifiers,
            semantic_role = semantic_role,
            placement     = placement,
            confidence    = conflict_result["confidence"],
            source        = conflict_result["source"],
            role_notes    = role_notes,
            placement_notes = place_notes,
            quantity_notes  = qty_notes,
            conflict_notes  = conflict_result["conflict_notes"],
            quantity      = quantity,
        )

        if eso.role_overridden:
            log.info(
                "Semantic override  beam=%s  ann=%s  %s -> %s",
                eso.beam_id, eso.annotation_id,
                eso.original_r1_role, eso.engineering_role,
            )

        return eso

    def interpret_all(
        self,
        annotations_by_beam: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[EngineeringSemanticObject]]:
        """Interpret all annotations across all beams."""
        result: Dict[str, List[EngineeringSemanticObject]] = {}
        total = 0
        for beam_id, anns in annotations_by_beam.items():
            esos = []
            for ann in anns:
                # Inject beam_id if missing in annotation dict
                if "beam_id" not in ann or not ann["beam_id"]:
                    ann = {**ann, "beam_id": beam_id}
                esos.append(self.interpret(ann))
                total += 1
            result[beam_id] = esos
        log.info("SemanticInterpreter: %d annotations interpreted", total)
        return result
