"""BeamReinforcementModel — canonical semantic contract for all downstream phases."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

PHASE = "Phase L.2"
MODEL_VERSION = "6.4.0"
ENGINE_VERSION = "1.0.0"

# ── Canonical reinforcement roles ────────────────────────────────────────────
ROLE_TOP_MAIN = "TOP_MAIN"
ROLE_BOTTOM_MAIN = "BOTTOM_MAIN"
ROLE_TOP_EXTRA = "TOP_EXTRA"
ROLE_BOTTOM_EXTRA = "BOTTOM_EXTRA"
ROLE_STIRRUP = "STIRRUP"
ROLE_SIDE_FACE = "SIDE_FACE_REINFORCEMENT"
ROLE_SPACER = "SPACER_BAR"
ROLE_CHAIR = "CHAIR_BAR"
ROLE_SUPPLEMENTARY = "SUPPLEMENTARY_BAR"
ROLE_UNKNOWN = "UNKNOWN"

ALL_ROLES = [
    ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN, ROLE_TOP_EXTRA, ROLE_BOTTOM_EXTRA,
    ROLE_STIRRUP, ROLE_SIDE_FACE, ROLE_SPACER, ROLE_CHAIR,
    ROLE_SUPPLEMENTARY, ROLE_UNKNOWN,
]

# ── Position zones within beam section ──────────────────────────────────────
ZONE_TOP = "TOP_ZONE"
ZONE_BOTTOM = "BOTTOM_ZONE"
ZONE_SIDE = "SIDE_ZONE"
ZONE_TRANSVERSE = "TRANSVERSE_ZONE"
ZONE_UNKNOWN = "UNKNOWN_ZONE"

# ── Bar extent along beam ────────────────────────────────────────────────────
EXTENT_FULL = "FULL_SPAN"          # continuous across full span
EXTENT_PARTIAL = "PARTIAL_SPAN"    # does not reach both supports
EXTENT_SUPPORT_LEFT = "LEFT_SUPPORT_ONLY"
EXTENT_SUPPORT_RIGHT = "RIGHT_SUPPORT_ONLY"
EXTENT_SUPPORT_BOTH = "BOTH_SUPPORTS"
EXTENT_MIDSPAN = "MIDSPAN_ONLY"
EXTENT_UNKNOWN = "UNKNOWN"

# ── Continuity types ─────────────────────────────────────────────────────────
CONTINUITY_SINGLE = "SINGLE_BEAM"
CONTINUITY_MULTI = "MULTI_BEAM_CONTINUOUS"
CONTINUITY_SHARED = "SHARED_REINFORCEMENT"
CONTINUITY_BROKEN = "BROKEN_REINFORCEMENT"
CONTINUITY_UNKNOWN = "UNKNOWN"

# ── Support zone types ───────────────────────────────────────────────────────
SUPPORT_LEFT = "LEFT_SUPPORT"
SUPPORT_RIGHT = "RIGHT_SUPPORT"
SUPPORT_INTERMEDIATE = "INTERMEDIATE_SUPPORT"
SUPPORT_CANTILEVER = "CANTILEVER"
SUPPORT_UNKNOWN = "UNKNOWN"


@dataclass
class ReinforcementBar:
    """Single classified reinforcement bar / bar group."""

    bar_id: str
    source_bar_id: Optional[str]          # original ID from pipeline
    beam_id: str
    semantic_role: str                     # TOP_MAIN / BOTTOM_MAIN / etc.
    diameter_mm: float
    quantity: int
    steel_grade: str
    bar_label: str                         # e.g. "2Y16"
    position_zone: str                     # ZONE_TOP / ZONE_BOTTOM / etc.
    extent: str                            # FULL_SPAN / PARTIAL_SPAN / etc.
    continuity: str                        # SINGLE_BEAM / MULTI_BEAM_CONTINUOUS
    support_zone: Optional[str]            # for support bars
    coverage_ratio: Optional[float]        # bar length / span length
    classification_evidence: str           # human-readable evidence
    classification_confidence: str         # HIGH / MEDIUM / LOW
    source_pipeline_role: Optional[str]    # original pipeline role
    spacing_mm: Optional[float] = None
    is_corrected: bool = False             # pipeline role was corrected
    is_reference_anchored: bool = False    # ground truth from reference images


@dataclass
class SupportZone:
    support_id: str
    support_type: str      # LEFT_SUPPORT / RIGHT_SUPPORT / INTERMEDIATE / CANTILEVER
    beam_id: str
    adjacent_beam_id: Optional[str]
    position_fraction: float   # 0.0 = left end, 1.0 = right end
    support_width_mm: Optional[float]


@dataclass
class DevelopmentLengthRegion:
    region_id: str
    beam_id: str
    bar_id: str
    location: str       # "left_support" / "right_support"
    ld_mm: Optional[float]


@dataclass
class ContinuityRegion:
    region_id: str
    beam_ids: List[str]
    bar_ids: List[str]
    continuity_type: str     # CONTINUOUS / LAPPED / SPLICED


@dataclass
class BeamGeometry:
    beam_id: str
    beam_mark: str
    width_mm: Optional[float]
    depth_mm: Optional[float]
    clear_span_mm: Optional[float]
    effective_span_mm: Optional[float]
    top_cover_mm: float = 25.0
    bottom_cover_mm: float = 25.0
    side_cover_mm: float = 25.0


@dataclass
class BeamReinforcementModel:
    """Canonical semantic model for one beam. All downstream phases consume this."""

    beam_id: str
    beam_name: str
    model_id: str
    geometry: Optional[BeamGeometry]
    support_zones: List[SupportZone]

    # ── Core reinforcement roles ───────────────────────────────────────────
    top_main_bars: List[ReinforcementBar]
    bottom_main_bars: List[ReinforcementBar]
    top_extra_bars: List[ReinforcementBar]
    bottom_extra_bars: List[ReinforcementBar]
    side_face_reinforcement: List[ReinforcementBar]
    stirrups: List[ReinforcementBar]
    spacer_bars: List[ReinforcementBar]
    chair_bars: List[ReinforcementBar]
    supplementary_bars: List[ReinforcementBar]

    # ── Regions ───────────────────────────────────────────────────────────
    development_length_regions: List[DevelopmentLengthRegion]
    continuity_regions: List[ContinuityRegion]

    # ── Meta ──────────────────────────────────────────────────────────────
    engineering_notes: List[str]
    total_classified_bars: int
    unclassified_bar_count: int
    classification_complete: bool
    is_benchmark_beam: bool
    interpretation_confidence: str    # HIGH / MEDIUM / LOW
    traceability: Dict[str, Any]

    def all_bars(self) -> List[ReinforcementBar]:
        return (
            self.top_main_bars + self.bottom_main_bars
            + self.top_extra_bars + self.bottom_extra_bars
            + self.side_face_reinforcement + self.stirrups
            + self.spacer_bars + self.chair_bars + self.supplementary_bars
        )

    def bar_count_by_role(self) -> Dict[str, int]:
        return {
            ROLE_TOP_MAIN: len(self.top_main_bars),
            ROLE_BOTTOM_MAIN: len(self.bottom_main_bars),
            ROLE_TOP_EXTRA: len(self.top_extra_bars),
            ROLE_BOTTOM_EXTRA: len(self.bottom_extra_bars),
            ROLE_STIRRUP: len(self.stirrups),
            ROLE_SIDE_FACE: len(self.side_face_reinforcement),
            ROLE_SPACER: len(self.spacer_bars),
            ROLE_CHAIR: len(self.chair_bars),
            ROLE_SUPPLEMENTARY: len(self.supplementary_bars),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "beam_id": self.beam_id,
            "beam_name": self.beam_name,
            "is_benchmark_beam": self.is_benchmark_beam,
            "interpretation_confidence": self.interpretation_confidence,
            "geometry": self._geom_dict(),
            "support_zones": [self._sz(s) for s in self.support_zones],
            "bar_count_by_role": self.bar_count_by_role(),
            "top_main_bars": [self._bar(b) for b in self.top_main_bars],
            "bottom_main_bars": [self._bar(b) for b in self.bottom_main_bars],
            "top_extra_bars": [self._bar(b) for b in self.top_extra_bars],
            "bottom_extra_bars": [self._bar(b) for b in self.bottom_extra_bars],
            "side_face_reinforcement": [self._bar(b) for b in self.side_face_reinforcement],
            "stirrups": [self._bar(b) for b in self.stirrups],
            "spacer_bars": [self._bar(b) for b in self.spacer_bars],
            "chair_bars": [self._bar(b) for b in self.chair_bars],
            "supplementary_bars": [self._bar(b) for b in self.supplementary_bars],
            "development_length_regions": [self._dl(d) for d in self.development_length_regions],
            "continuity_regions": [self._cr(c) for c in self.continuity_regions],
            "engineering_notes": self.engineering_notes,
            "total_classified_bars": self.total_classified_bars,
            "unclassified_bar_count": self.unclassified_bar_count,
            "classification_complete": self.classification_complete,
            "traceability": self.traceability,
        }

    def _geom_dict(self) -> Optional[Dict]:
        if not self.geometry:
            return None
        g = self.geometry
        return {
            "beam_id": g.beam_id,
            "width_mm": g.width_mm,
            "depth_mm": g.depth_mm,
            "clear_span_mm": g.clear_span_mm,
            "effective_span_mm": g.effective_span_mm,
            "top_cover_mm": g.top_cover_mm,
            "bottom_cover_mm": g.bottom_cover_mm,
        }

    @staticmethod
    def _bar(b: ReinforcementBar) -> Dict:
        return {
            "bar_id": b.bar_id,
            "source_bar_id": b.source_bar_id,
            "beam_id": b.beam_id,
            "semantic_role": b.semantic_role,
            "diameter_mm": b.diameter_mm,
            "quantity": b.quantity,
            "steel_grade": b.steel_grade,
            "bar_label": b.bar_label,
            "position_zone": b.position_zone,
            "extent": b.extent,
            "continuity": b.continuity,
            "support_zone": b.support_zone,
            "coverage_ratio": b.coverage_ratio,
            "spacing_mm": b.spacing_mm,
            "classification_evidence": b.classification_evidence,
            "classification_confidence": b.classification_confidence,
            "source_pipeline_role": b.source_pipeline_role,
            "is_corrected": b.is_corrected,
            "is_reference_anchored": b.is_reference_anchored,
        }

    @staticmethod
    def _sz(s: SupportZone) -> Dict:
        return {
            "support_id": s.support_id,
            "support_type": s.support_type,
            "beam_id": s.beam_id,
            "adjacent_beam_id": s.adjacent_beam_id,
            "position_fraction": s.position_fraction,
            "support_width_mm": s.support_width_mm,
        }

    @staticmethod
    def _dl(d: DevelopmentLengthRegion) -> Dict:
        return {
            "region_id": d.region_id,
            "beam_id": d.beam_id,
            "bar_id": d.bar_id,
            "location": d.location,
            "ld_mm": d.ld_mm,
        }

    @staticmethod
    def _cr(c: ContinuityRegion) -> Dict:
        return {
            "region_id": c.region_id,
            "beam_ids": c.beam_ids,
            "bar_ids": c.bar_ids,
            "continuity_type": c.continuity_type,
        }


def make_model_id(beam_id: str) -> str:
    return f"BRM::{beam_id}::L2"
