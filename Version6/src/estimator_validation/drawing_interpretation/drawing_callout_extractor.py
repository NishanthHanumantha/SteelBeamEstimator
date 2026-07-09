"""Extract raw drawing callouts and annotations — Phase QA.3."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.estimator_validation.drawing_interpretation.drawing_loader import DrawingLoader
from src.estimator_validation.drawing_interpretation.interpretation_types import (
    BeamInterpretation,
    EngineeringConcept,
)


BAR_PATTERN = re.compile(
    r"(?P<qty>\d+)?\s*(?:L[-\s]?)?(?P<dia>Y?\d+)\s*(?:@\s*(?P<spacing>\d+)\s*(?:C/C|c/c|mm)?)?",
    re.IGNORECASE,
)


class DrawingCalloutExtractor:
    """Build drawing interpretation objects from existing JSON only."""

    def extract_all(self, data: dict[str, Any], beam_marks: List[str]) -> Dict[str, BeamInterpretation]:
        text_by_beam = self._index_text_objects(data.get("reinforcement_text"))
        properties_by_beam = self._index_properties(data.get("engineering_properties"))
        bars_by_beam = self._index_bars(data.get("reinforcement_objects"))
        interpretations: Dict[str, BeamInterpretation] = {}
        for beam_mark in beam_marks:
            interpretations[beam_mark] = self._extract_beam(
                beam_mark,
                text_by_beam.get(beam_mark, []),
                properties_by_beam.get(beam_mark, []),
                bars_by_beam.get(beam_mark, []),
            )
        return interpretations

    def _extract_beam(
        self,
        beam_mark: str,
        texts: List[str],
        properties: List[dict[str, Any]],
        bars: List[dict[str, Any]],
    ) -> BeamInterpretation:
        interpretation = BeamInterpretation(beam_mark=beam_mark)
        interpretation.raw_annotations = list(dict.fromkeys(texts))
        for text in texts:
            normalized = text.strip()
            upper = normalized.upper()
            if upper in {"LD", "L/D"} or "DEVELOPMENT" in upper:
                interpretation.development_notes.append(normalized)
            elif "HOOK" in upper:
                interpretation.hook_notes.append(normalized)
            elif "SHAPE" in upper or upper.startswith("SC_"):
                interpretation.shape_notes.append(normalized)
            elif "ZONE" in upper or "SUPPORT" in upper:
                interpretation.zone_notes.append(normalized)
                interpretation.support_notes.append(normalized)

        concepts: List[EngineeringConcept] = []
        seen_keys: set[str] = set()
        for text in texts:
            for concept in self._concepts_from_callout(beam_mark, text, source_layer="reinforcement_text"):
                if concept.concept_key() not in seen_keys:
                    seen_keys.add(concept.concept_key())
                    concepts.append(concept)

        for bar in bars:
            role = str(bar.get("role") or "UNKNOWN")
            callout = ""
            trace = bar.get("traceability") or {}
            if isinstance(trace, dict):
                callout = str(trace.get("callout") or "")
            concept = EngineeringConcept(
                beam_mark=beam_mark,
                concept_type=role,
                role=role,
                diameter_mm=float(bar["diameter_mm"]) if bar.get("diameter_mm") is not None else None,
                quantity=float(bar["quantity"]) if bar.get("quantity") is not None else None,
                raw_callouts=[callout] if callout else [],
                description=callout or role,
                source_layer="reinforcement_objects",
            )
            if concept.concept_key() not in seen_keys:
                seen_keys.add(concept.concept_key())
                concepts.append(concept)

        for prop in properties:
            prop_type = str(prop.get("property_type") or "ANNOTATION")
            source_text = str(prop.get("source_text") or prop.get("parsed_value") or "")
            if not source_text:
                continue
            if prop_type in {"DEVELOPMENT_LENGTH", "HOOK", "SHAPE_CODE", "SPACING"}:
                note_lists = {
                    "DEVELOPMENT_LENGTH": interpretation.development_notes,
                    "HOOK": interpretation.hook_notes,
                    "SHAPE_CODE": interpretation.shape_notes,
                    "SPACING": interpretation.zone_notes,
                }
                note_lists.get(prop_type, interpretation.raw_annotations).append(source_text)
            for concept in self._concepts_from_callout(beam_mark, source_text, source_layer="engineering_properties"):
                concept.concept_type = self._property_to_concept_type(prop_type, concept.role)
                if concept.concept_key() not in seen_keys:
                    seen_keys.add(concept.concept_key())
                    concepts.append(concept)

        interpretation.concepts = concepts
        return interpretation

    def _concepts_from_callout(
        self,
        beam_mark: str,
        text: str,
        source_layer: str,
    ) -> List[EngineeringConcept]:
        cleaned = re.sub(r"\\A\d+;", "", text).strip()
        if not cleaned or cleaned.startswith("B") and "(" in cleaned:
            return []
        concepts: List[EngineeringConcept] = []
        for match in BAR_PATTERN.finditer(cleaned.replace("-", "")):
            qty = float(match.group("qty")) if match.group("qty") else None
            dia_text = match.group("dia").upper().replace("Y", "")
            diameter = float(dia_text) if dia_text.isdigit() else None
            spacing = float(match.group("spacing")) if match.group("spacing") else None
            role = self._infer_role(cleaned, spacing)
            concepts.append(
                EngineeringConcept(
                    beam_mark=beam_mark,
                    concept_type=role,
                    role=role,
                    diameter_mm=diameter,
                    quantity=qty,
                    spacing_mm=spacing,
                    raw_callouts=[cleaned],
                    description=cleaned,
                    source_layer=source_layer,
                )
            )
        if not concepts and cleaned:
            concepts.append(
                EngineeringConcept(
                    beam_mark=beam_mark,
                    concept_type="ANNOTATION",
                    role="ANNOTATION",
                    raw_callouts=[cleaned],
                    description=cleaned,
                    source_layer=source_layer,
                )
            )
        return concepts

    @staticmethod
    def _infer_role(text: str, spacing: Optional[float]) -> str:
        upper = text.upper()
        if spacing is not None or "@" in upper or "C/C" in upper:
            return "STIRRUP"
        if "SPACER" in upper:
            return "SPACER_BAR"
        if "SFR" in upper:
            return "SFR"
        if "EXTRA" in upper:
            return "TOP_EXTRA"
        if "BOTTOM" in upper:
            return "BOTTOM_MAIN"
        if "SIDE" in upper:
            return "SIDE_BAR"
        return "TOP_MAIN"

    @staticmethod
    def _property_to_concept_type(property_type: str, role: str) -> str:
        mapping = {
            "DEVELOPMENT_LENGTH": "DEVELOPMENT_LENGTH_NOTE",
            "HOOK": "HOOK_NOTE",
            "SHAPE_CODE": "SHAPE_NOTE",
            "SPACING": "SPACING_ZONE",
        }
        return mapping.get(property_type, role)

    def _index_text_objects(self, payload: Any) -> Dict[str, List[str]]:
        indexed: Dict[str, List[str]] = {}
        if not payload:
            return indexed
        for item in payload.get("text_objects") or []:
            owner = (item.get("ownership") or {}).get("owner_id", "")
            beam_mark = DrawingLoader.beam_mark_from_owner(str(owner))
            if not beam_mark:
                continue
            indexed.setdefault(beam_mark, []).append(str(item.get("text") or ""))
        return indexed

    def _index_properties(self, payload: Any) -> Dict[str, List[dict[str, Any]]]:
        indexed: Dict[str, List[dict[str, Any]]] = {}
        if not payload:
            return indexed
        for item in payload.get("properties") or payload.get("results") or []:
            owner = str(item.get("owner_context_id") or "")
            beam_mark = DrawingLoader.beam_mark_from_owner(owner)
            if not beam_mark:
                continue
            indexed.setdefault(beam_mark, []).append(item)
        return indexed

    def _index_bars(self, payload: Any) -> Dict[str, List[dict[str, Any]]]:
        indexed: Dict[str, List[dict[str, Any]]] = {}
        if not payload:
            return indexed
        for item in payload.get("bars") or []:
            beam_mark = str(item.get("beam_id") or item.get("beam_mark") or "")
            if beam_mark:
                indexed.setdefault(beam_mark, []).append(item)
        return indexed
