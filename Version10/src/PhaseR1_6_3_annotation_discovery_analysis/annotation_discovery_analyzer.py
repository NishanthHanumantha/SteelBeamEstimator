"""
Per-beam annotation discovery analyzer — evidence only.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from beam_analysis_model import (
    MODEL_VERSION,
    BeamAnalysisRecord,
    BeamInventoryRecord,
    StageEvidence,
    StirrupDiscoveryStatus,
)
from drawing_evidence_builder import DrawingEvidenceBuilder
from input_loader import natural_beam_key

_LEG_RE = re.compile(r"(?i)(\d+)\s*L")


class AnnotationDiscoveryAnalyzer:
    def __init__(self):
        self._evidence = DrawingEvidenceBuilder()

    def analyze_all(self, data: Dict[str, Any]) -> List[BeamAnalysisRecord]:
        records: List[BeamAnalysisRecord] = []
        for beam_id in sorted(data["beam_ids"], key=natural_beam_key):
            records.append(self.analyze_beam(beam_id, data))
        return records

    def analyze_beam(self, beam_id: str, data: Dict[str, Any]) -> BeamAnalysisRecord:
        registry_beams = data["registry"].get("beams") or {}
        reg = registry_beams.get(beam_id) or {}
        geo = (data["geometry"] or {}).get(beam_id) or {}
        axis = (data["axes"] or {}).get(beam_id) if isinstance(data["axes"], dict) else None
        annotations = list((data["annotations_by_beam"] or {}).get(beam_id) or [])
        relationships = list((data["relationships_by_beam"] or {}).get(beam_id) or [])

        inventory = self._inventory(beam_id, reg, geo, axis, data["registry"])
        stage_sets = self._stage_stirrup_sets(data)
        pipeline = self._pipeline_trace(beam_id, stage_sets, annotations)
        stirrup = self._stirrup_status(beam_id, annotations, data)
        drawing = self._evidence.build_for_beam(
            beam_id=beam_id,
            registry_beam=reg,
            annotations=annotations,
            relationships=relationships,
            leaders=data.get("leaders") or [],
            axis=axis if isinstance(axis, dict) else None,
        )
        status = (data.get("rule012_status_by_beam") or {}).get(beam_id) or "UNKNOWN"
        return BeamAnalysisRecord(
            inventory=inventory,
            stirrup_status=stirrup,
            pipeline_trace=pipeline,
            drawing_evidence=drawing,
            rule012_status=status,
        )

    def _inventory(
        self,
        beam_id: str,
        reg: Dict[str, Any],
        geo: Dict[str, Any],
        axis: Optional[Dict[str, Any]],
        registry: Dict[str, Any],
    ) -> BeamInventoryRecord:
        section = reg.get("section") or {}
        length = geo.get("effective_span_mm") or geo.get("clear_span_mm") or reg.get("clear_span_mm")
        width = geo.get("width_mm") or section.get("width_mm")
        depth = geo.get("depth_mm") or section.get("depth_mm")
        orientation = "UNKNOWN"
        if isinstance(axis, dict) and axis.get("orientation"):
            orientation = str(axis["orientation"])
        drawing_path = str(reg.get("drawing_path") or registry.get("drawing_path") or "")
        drawing_name = str(reg.get("drawing_stem") or "")
        if not drawing_name and drawing_path:
            drawing_name = drawing_path.replace("\\", "/").split("/")[-1]
        return BeamInventoryRecord(
            beam_id=beam_id,
            beam_length_mm=float(length) if length is not None else None,
            beam_width_mm=float(width) if width is not None else None,
            beam_depth_mm=float(depth) if depth is not None else None,
            orientation=orientation,
            drawing_name=drawing_name,
            drawing_path=drawing_path,
            registry_status=str(reg.get("status") or ("REGISTERED" if reg else "MISSING_FROM_REGISTRY_DETAIL")),
            centroid_x=reg.get("centroid_x"),
            centroid_y=reg.get("centroid_y"),
            bbox=reg.get("bbox") if isinstance(reg.get("bbox"), dict) else None,
            section_refs=tuple(),
        )

    def _stirrup_status(
        self,
        beam_id: str,
        annotations: List[Dict[str, Any]],
        data: Dict[str, Any],
    ) -> StirrupDiscoveryStatus:
        stirrup_anns = [a for a in annotations if str(a.get("role") or "").upper() == "STIRRUP"]
        rule_pass = beam_id in (data.get("detected_ids") or set())

        ebar_count = 0
        for bm in data.get("bars") or []:
            if bm.get("beam_id") != beam_id:
                continue
            for bar in bm.get("bars") or []:
                if str(bar.get("bar_role") or "").upper() == "STIRRUP":
                    ebar_count += 1

        if not rule_pass:
            return StirrupDiscoveryStatus(
                stirrup_detected="NO",
                engineeringbar_count=ebar_count,
                annotation_stirrup_count=len(stirrup_anns),
                note="No Stirrup Representation",
            )

        # Prefer annotation facts when present; do not invent missing fields.
        notation = None
        diameter = None
        spacing = None
        legs = None
        if stirrup_anns:
            first = stirrup_anns[0]
            notation = first.get("clean_text") or first.get("bar_label")
            diameter = first.get("diameter_mm")
            spacing = first.get("spacing_mm")
            m = _LEG_RE.search(str(notation or ""))
            if m:
                legs = int(m.group(1))
        else:
            for it in data.get("intents") or []:
                if it.get("beam_id") == beam_id and str(it.get("role") or "").upper() == "STIRRUP":
                    notation = it.get("bar_label") or notation
                    if it.get("diameter_mm") is not None:
                        diameter = it.get("diameter_mm")
                    if it.get("spacing_mm") is not None:
                        spacing = it.get("spacing_mm")
                    m = _LEG_RE.search(str(notation or ""))
                    if m:
                        legs = int(m.group(1))
                    break

        return StirrupDiscoveryStatus(
            stirrup_detected="YES",
            detected_notation=str(notation) if notation else None,
            detected_diameter_mm=float(diameter) if diameter is not None else None,
            spacing_mm=spacing,
            leg_count=legs,
            engineeringbar_count=ebar_count,
            annotation_stirrup_count=len(stirrup_anns),
            note="",
        )

    def _pipeline_trace(
        self,
        beam_id: str,
        stage_sets: Dict[str, Set[str]],
        annotations: List[Dict[str, Any]],
    ) -> List[StageEvidence]:
        sources = {
            "Annotation Discovery": "PhaseR.1_generalized_reinforcement_discovery/reinforcement_annotations.json",
            "Intent Resolution": "PhaseR1_2C_engineering_intent_resolution/engineering_intents.json",
            "Reinforcement Detail": "PhaseR1_2D_reinforcement_detailing/reinforcement_details.json",
            "Piece Generation": "PhaseR1_3_reinforcement_piece_generation/reinforcement_pieces.json",
            "EngineeringBars": "PhaseR1.3_pipeline_integration/engineering_bar_models.json",
        }
        out: List[StageEvidence] = []
        for stage, path in sources.items():
            present = beam_id in stage_sets.get(stage, set())
            if stage == "Annotation Discovery" and not annotations:
                status = "Missing"
            elif stage == "Annotation Discovery" and annotations and not present:
                # Beam has annotations but no STIRRUP role
                status = "Missing"
            else:
                status = "Present" if present else "Missing"
            detail = "STIRRUP role present" if present else "STIRRUP role absent"
            if stage == "Annotation Discovery":
                detail = f"{detail}; annotation_count={len(annotations)}"
            out.append(StageEvidence(stage=stage, status=status, evidence_source=path, detail=detail))
        return out

    @staticmethod
    def _stage_stirrup_sets(data: Dict[str, Any]) -> Dict[str, Set[str]]:
        def role_ok(r: Any) -> bool:
            return str(r or "").strip().upper() == "STIRRUP"

        ann_set: Set[str] = set()
        for bid, items in (data.get("annotations_by_beam") or {}).items():
            if any(role_ok(a.get("role")) for a in items or []):
                ann_set.add(str(bid))

        intent_set = {str(i["beam_id"]) for i in data.get("intents") or [] if role_ok(i.get("role")) and i.get("beam_id")}
        detail_set = {str(d["beam_id"]) for d in data.get("details") or [] if role_ok(d.get("role")) and d.get("beam_id")}
        piece_set = {
            str(p["beam_id"])
            for p in data.get("pieces") or []
            if role_ok(p.get("role") or p.get("piece_role")) and p.get("beam_id")
        }
        ebar_set: Set[str] = set()
        for bm in data.get("bars") or []:
            bid = bm.get("beam_id")
            if not bid:
                continue
            if any(role_ok(bar.get("bar_role")) for bar in bm.get("bars") or []):
                ebar_set.add(str(bid))

        return {
            "Annotation Discovery": ann_set,
            "Intent Resolution": intent_set,
            "Reinforcement Detail": detail_set,
            "Piece Generation": piece_set,
            "EngineeringBars": ebar_set,
        }
