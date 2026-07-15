"""
reinforcement_models.py — Data models for Phase R.1.
MODEL_VERSION: 7.3.0
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# ── Engineering roles (canonical) ────────────────────────────────────────────
ROLE_TOP_MAIN    = "TOP_MAIN"
ROLE_BOTTOM_MAIN = "BOTTOM_MAIN"
ROLE_TOP_EXTRA   = "TOP_EXTRA"
ROLE_BOTTOM_EXTRA = "BOTTOM_EXTRA"
ROLE_STIRRUP     = "STIRRUP"
ROLE_SIDE_FACE   = "SIDE_FACE_REINFORCEMENT"
ROLE_SPACER      = "SPACER_BAR"
ROLE_DEVELOPMENT = "DEVELOPMENT"
ROLE_LAP         = "LAP"
ROLE_BENT_UP     = "BENT_UP"
ROLE_ANCHORAGE   = "ANCHORAGE"
ROLE_UNKNOWN     = "UNKNOWN"

# ── Position zones ────────────────────────────────────────────────────────────
ZONE_TOP         = "TOP_ZONE"
ZONE_BOTTOM      = "BOTTOM_ZONE"
ZONE_SIDE        = "SIDE_ZONE"
ZONE_TRANSVERSE  = "TRANSVERSE_ZONE"
ZONE_UNKNOWN     = "UNKNOWN_ZONE"

# ── Steel grades ──────────────────────────────────────────────────────────────
GRADE_Y  = "Y460"    # High tensile (Y)
GRADE_R  = "R250"    # Mild steel (R)
GRADE_T  = "T500"    # High tensile (T)


@dataclass
class BeamDetail:
    """A single beam reinforcement detail block discovered in the DXF."""
    beam_id:     str
    beam_mark:   str
    centroid_x:  float
    centroid_y:  float
    section:     Dict[str, Any]        # width_mm, depth_mm
    detail_radius: float               # search radius for annotations
    entity_count:  int = 0


@dataclass
class ReinforcementAnnotation:
    """A single engineering annotation found within a beam detail."""
    annotation_id:    str
    beam_id:          str
    raw_text:         str
    clean_text:       str
    x:                float
    y:                float
    dy_from_centroid: float           # +ve = above centroid = top zone
    entity_type:      str             # TEXT / MTEXT
    role:             str = ROLE_UNKNOWN
    position_zone:    str = ZONE_UNKNOWN
    quantity:         int  = 0
    diameter_mm:      float = 0.0
    steel_grade:      str  = GRADE_Y
    spacing_mm:       Optional[float] = None   # for stirrups
    bar_label:        str  = ""
    confidence:       str  = "LOW"
    is_reinforcement: bool = False


@dataclass
class ReinforcementGroup:
    """One engineering group (TOP_MAIN, STIRRUP, etc.) for a beam."""
    group_id:     str
    beam_id:      str
    role:         str
    bars:         List[ReinforcementAnnotation] = field(default_factory=list)
    total_quantity: int  = 0
    diameters_mm: List[float] = field(default_factory=list)
    labels:       List[str]   = field(default_factory=list)


@dataclass
class R1BeamReinforcementModel:
    """Complete reinforcement model for one beam, produced by R.1."""
    beam_id:          str
    beam_mark:        str
    model_id:         str
    section:          Dict[str, Any]
    groups:           Dict[str, ReinforcementGroup]   # role → group
    all_annotations:  List[ReinforcementAnnotation]
    coverage_pct:     float    # % annotations classified (not UNKNOWN)
    classification_complete: bool
    model_version:    str = "7.3.0"
    phase:            str = "R.1"

    def to_dict(self) -> dict:
        return {
            "beam_id":          self.beam_id,
            "beam_mark":        self.beam_mark,
            "model_id":         self.model_id,
            "model_version":    self.model_version,
            "phase":            self.phase,
            "section":          self.section,
            "coverage_pct":     self.coverage_pct,
            "classification_complete": self.classification_complete,
            "groups": {
                role: {
                    "group_id":      g.group_id,
                    "role":          g.role,
                    "total_quantity": g.total_quantity,
                    "diameters_mm":  g.diameters_mm,
                    "labels":        g.labels,
                    "bar_count":     len(g.bars),
                }
                for role, g in self.groups.items()
            },
            "annotation_count": len(self.all_annotations),
            "reinforcement_count": sum(1 for a in self.all_annotations if a.is_reinforcement),
        }
