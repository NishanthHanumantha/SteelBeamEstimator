"""
Collect drawing evidence per beam — collection only, no interpretation.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from beam_analysis_model import DrawingEvidence

_DIM_RE = re.compile(r"(?i)\d+\s*[x×]\s*\d+|^\d+(\.\d+)?$")
_SECTION_RE = re.compile(r"(?i)\b(section|typ|typical|elev|detail)\b")
_LEADER_NEAR_MM = 5000.0


class DrawingEvidenceBuilder:
    def build_for_beam(
        self,
        beam_id: str,
        registry_beam: Dict[str, Any],
        annotations: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        leaders: List[Dict[str, Any]],
        axis: Optional[Dict[str, Any]],
    ) -> DrawingEvidence:
        _ = axis  # numeric rotation not available in artefacts
        cx = registry_beam.get("centroid_x")
        cy = registry_beam.get("centroid_y")
        texts: List[str] = []
        labels: List[str] = []
        dimensions: List[str] = []
        section_refs: List[str] = []
        unknown_texts: List[str] = []
        roles: Counter = Counter()
        distances: List[float] = []

        for a in annotations:
            text = str(a.get("clean_text") or "").strip()
            label = str(a.get("bar_label") or "").strip()
            role = str(a.get("role") or "UNKNOWN")
            roles[role] += 1
            if text:
                texts.append(text)
            if label:
                labels.append(label)
            if text and _DIM_RE.search(text):
                dimensions.append(text)
            if text and _SECTION_RE.search(text):
                section_refs.append(text)
            if role.upper() == "UNKNOWN" and text:
                unknown_texts.append(text)
            d = a.get("dy_from_centroid")
            if d is not None:
                try:
                    distances.append(abs(float(d)))
                except (TypeError, ValueError):
                    pass
            elif cx is not None and cy is not None and a.get("x") is not None and a.get("y") is not None:
                try:
                    distances.append(math.hypot(float(a["x"]) - float(cx), float(a["y"]) - float(cy)))
                except (TypeError, ValueError):
                    pass

        leader_refs: List[str] = []
        near_layers: List[str] = []
        leader_near = 0
        for ldr in leaders:
            lid = str(ldr.get("leader_id") or "")
            lb = str(ldr.get("beam_id") or "")
            layer = str(ldr.get("layer") or "")
            matched = lb == beam_id
            near = False
            if cx is not None and cy is not None:
                try:
                    dist = math.hypot(
                        float(ldr.get("tip_x") or 0) - float(cx),
                        float(ldr.get("tip_y") or 0) - float(cy),
                    )
                    near = dist <= _LEADER_NEAR_MM
                except (TypeError, ValueError):
                    near = False
            if matched or near:
                leader_near += 1
                if lid:
                    leader_refs.append(lid if matched else f"{lid}~near")
                if layer:
                    near_layers.append(layer)

        bbox = registry_beam.get("bbox") if isinstance(registry_beam.get("bbox"), dict) else None

        return DrawingEvidence(
            beam_id=beam_id,
            nearby_annotation_texts=texts[:50],
            associated_reinforcement_labels=sorted(set(labels))[:50],
            associated_dimensions=sorted(set(dimensions))[:30],
            section_references=sorted(set(section_refs))[:30],
            leader_references=leader_refs[:40],
            nearest_annotation_distance=min(distances) if distances else None,
            annotation_count=len(annotations),
            text_entity_count=None,
            mtext_count=None,
            block_reference_count=None,
            layer_names=sorted(set(near_layers)),
            rotation=None,
            coordinates={"x": cx, "y": cy},
            bounding_box=bbox,
            role_counts=dict(roles),
            leader_count_near_beam=leader_near,
            relationship_count=len(relationships),
            unknown_annotation_texts=unknown_texts[:30],
        )
