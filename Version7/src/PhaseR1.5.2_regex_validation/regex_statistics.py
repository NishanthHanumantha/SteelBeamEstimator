"""STEP 8-11 — Y10, stirrup, spacer audits and regex statistics."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .regex_validation_models import MtextCleaningRecord, RawTextEntity, RegexMatchResult

_Y10_RX = re.compile(r"Y\s*10\b", re.I)
_STIRRUP_RX = [
    re.compile(r"Y\d+\s*@", re.I),
    re.compile(r"\d+L[-\s]*Y\d+\s*@", re.I),
    re.compile(r"R\d+\s*@", re.I),
    re.compile(r"Y\d+\s*@\s*\d+/\d+", re.I),
]
_SPACER_RX = re.compile(r"SPACER|S\.P\.|SP\.|PIN\s*BAR|SUPPORT\s*BAR|DISTRIBUTION", re.I)


class RegexStatistics:

    def compute(
        self,
        entities: List[RawTextEntity],
        clean_map: Dict[str, MtextCleaningRecord],
        matches: List[RegexMatchResult],
        r1_annotations: List[Dict],
    ) -> Dict[str, Any]:
        match_by_id = {m.entity_id: m for m in matches}
        reinf_entities = self._reinforcement_entities(entities, clean_map, matches)

        y10_audit = self._y10_audit(entities, clean_map, match_by_id, r1_annotations)
        stirrup_audit = self._stirrup_audit(entities, clean_map, match_by_id, r1_annotations)
        spacer_audit = self._spacer_audit(entities, clean_map, match_by_id, r1_annotations)

        matched = sum(1 for m in matches if m.matched)
        cleaning_fail = sum(
            1 for c in clean_map.values()
            if c.entire_annotation_removed or c.status == "ENGINEERING_TEXT_LOST"
        )
        regex_fail = sum(1 for m in matches if not m.matched and m.text)
        semantic_fail = sum(
            1 for m in matches
            if m.matched and m.classification == "UNKNOWN"
        )

        return {
            "total_dxf_entities": len(entities),
            "reinforcement_candidates": len(reinf_entities),
            "regex_matched": matched,
            "regex_failed": regex_fail,
            "cleaning_failures": cleaning_fail,
            "semantic_failures": semantic_fail,
            "y10": y10_audit,
            "stirrup": stirrup_audit,
            "spacer": spacer_audit,
            "entity_type_counts": self._entity_type_counts(entities),
            "classification_counts": self._classification_counts(matches),
        }

    def _reinforcement_entities(
        self,
        entities: List[RawTextEntity],
        clean_map: Dict[str, MtextCleaningRecord],
        matches: List[RegexMatchResult],
    ) -> List[str]:
        ids = []
        reinf_rx = re.compile(
            r"Y\d+|R\d+|S\.?F\.?R|SPACER|Ld|Lap|@\d+", re.I
        )
        for ent in entities:
            text = f"{ent.raw_text} {clean_map[ent.entity_id].cleaned_text}"
            if reinf_rx.search(text):
                ids.append(ent.entity_id)
        return ids

    def _y10_audit(
        self,
        entities: List[RawTextEntity],
        clean_map: Dict[str, MtextCleaningRecord],
        match_by_id: Dict[str, RegexMatchResult],
        r1_annotations: List[Dict],
    ) -> Dict[str, Any]:
        dxf_y10 = []
        for ent in entities:
            if not _Y10_RX.search(ent.raw_text):
                continue
            cleaning = clean_map[ent.entity_id]
            match = match_by_id[ent.entity_id]
            dxf_y10.append({
                "entity_id": ent.entity_id,
                "entity_type": ent.entity_type,
                "raw_text": ent.raw_text[:200],
                "cleaned_text": cleaning.cleaned_text,
                "matched": match.matched,
                "regex_name": match.regex_name,
                "classification": match.classification,
                "engineering_role": "SFR_SIDE_FACE" if "S.F.R" in ent.raw_text.upper().replace(".", "") else "UNKNOWN",
                "nearest_beam_id": ent.nearest_beam_id,
                "root_cause": match.root_cause or cleaning.status,
            })

        r1_y10 = [
            a for a in r1_annotations
            if a.get("diameter_mm") == 10 or "Y10" in (a.get("clean_text") or "").upper()
        ]
        parsed = sum(1 for y in dxf_y10 if y["matched"])
        total = len(dxf_y10)
        support_pct = round(100.0 * parsed / total, 2) if total else 100.0

        return {
            "dxf_entities": total,
            "dxf_details": dxf_y10,
            "r1_pipeline_y10": len(r1_y10),
            "parsed": parsed,
            "unparsed": total - parsed,
            "support_pct": support_pct,
        }

    def _stirrup_audit(
        self,
        entities: List[RawTextEntity],
        clean_map: Dict[str, MtextCleaningRecord],
        match_by_id: Dict[str, RegexMatchResult],
        r1_annotations: List[Dict],
    ) -> Dict[str, Any]:
        dxf_stirrups = []
        for ent in entities:
            combined = f"{ent.raw_text} {clean_map[ent.entity_id].cleaned_text}"
            if not any(rx.search(combined) for rx in _STIRRUP_RX):
                continue
            match = match_by_id[ent.entity_id]
            dxf_stirrups.append({
                "entity_id": ent.entity_id,
                "raw_text": ent.raw_text[:120],
                "cleaned_text": clean_map[ent.entity_id].cleaned_text,
                "matched": match.matched and match.regex_name == "RE_STIRRUP",
                "regex_name": match.regex_name,
                "nearest_beam_id": ent.nearest_beam_id,
            })

        r1_stirrups = [a for a in r1_annotations if a.get("role") == "STIRRUP"]
        parsed = sum(1 for s in dxf_stirrups if s["matched"])
        total = len(dxf_stirrups)
        return {
            "dxf_patterns": total,
            "dxf_details": dxf_stirrups,
            "r1_pipeline_stirrups": len(r1_stirrups),
            "parsed": parsed,
            "unparsed": total - parsed,
            "coverage_pct": round(100.0 * parsed / total, 2) if total else 100.0,
        }

    def _spacer_audit(
        self,
        entities: List[RawTextEntity],
        clean_map: Dict[str, MtextCleaningRecord],
        match_by_id: Dict[str, RegexMatchResult],
        r1_annotations: List[Dict],
    ) -> Dict[str, Any]:
        dxf_spacers = []
        for ent in entities:
            if not _SPACER_RX.search(ent.raw_text):
                continue
            match = match_by_id[ent.entity_id]
            dxf_spacers.append({
                "entity_id": ent.entity_id,
                "raw_text": ent.raw_text[:120],
                "cleaned_text": clean_map[ent.entity_id].cleaned_text,
                "matched": match.matched,
                "classification": match.classification,
                "nearest_beam_id": ent.nearest_beam_id,
            })

        r1_spacers = [a for a in r1_annotations if "SPACER" in (a.get("role") or "")]
        parsed = sum(1 for s in dxf_spacers if s["matched"] or s["classification"] == "SPACER")
        total = len(dxf_spacers)
        return {
            "dxf_patterns": total,
            "dxf_details": dxf_spacers,
            "r1_pipeline_spacers": len(r1_spacers),
            "parsed": parsed,
            "unparsed": total - parsed,
            "coverage_pct": round(100.0 * parsed / total, 2) if total else 100.0,
        }

    @staticmethod
    def _entity_type_counts(entities: List[RawTextEntity]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in entities:
            counts[e.entity_type] = counts.get(e.entity_type, 0) + 1
        return counts

    @staticmethod
    def _classification_counts(matches: List[RegexMatchResult]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for m in matches:
            lbl = m.classification or "UNCLASSIFIED"
            counts[lbl] = counts.get(lbl, 0) + 1
        return counts
