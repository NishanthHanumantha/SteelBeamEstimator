"""
Stirrup Models — Phase SI.1
Data classes for stirrup notation, zones, quantities, and BBS rows.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class StirrupType(str, Enum):
    UNIFORM  = "UNIFORM"    # single spacing over entire span
    VARIABLE = "VARIABLE"   # multiple spacings / shear zones


class ZoneRole(str, Enum):
    LEFT_SUPPORT  = "LEFT_SUPPORT"
    MIDSPAN       = "MIDSPAN"
    RIGHT_SUPPORT = "RIGHT_SUPPORT"


@dataclass
class ParsedStirrupNotation:
    """Result of parsing a stirrup label string."""
    raw_label: str
    legs: int
    diameter_mm: float
    steel_grade: str
    spacings_mm: List[int]            # ordered list; length 1 = UNIFORM
    stirrup_type: StirrupType
    is_parseable: bool = True
    parse_note: str = ""


@dataclass
class StirrupZone:
    """One engineering shear zone in the beam."""
    zone_id: str
    zone_index: int                   # 0-based position along beam
    role: ZoneRole
    start_mm: float
    end_mm: float
    length_mm: float
    spacing_mm: int


@dataclass
class StirrupGroup:
    """
    One or more merged zones that share the same spacing.
    Generates exactly ONE BBS row.
    """
    group_id: str
    beam_id: str
    diameter_mm: float
    steel_grade: str
    legs: int
    spacing_mm: int
    zones: List[StirrupZone]
    quantity: int
    cut_length_mm: float
    weight_per_unit_kg: float
    total_weight_kg: float
    is_merged: bool = False           # True when left+right supports are combined
    merge_note: str = ""


@dataclass
class BeamStirrupResult:
    """All stirrup groups computed for one beam."""
    beam_id: str
    span_mm: float
    depth_mm: float
    width_mm: float
    stirrup_type: StirrupType
    groups: List[StirrupGroup] = field(default_factory=list)
    total_quantity: int = 0
    total_weight_kg: float = 0.0
    old_quantity: int = 0           # quantity from previous engine (for comparison)
    old_weight_kg: float = 0.0
    parse_note: str = ""


@dataclass
class StirrupEngineResult:
    """Aggregate result across all beams."""
    model_version: str = "6.6.1"
    beam_results: List[BeamStirrupResult] = field(default_factory=list)
    total_uniform_beams: int = 0
    total_variable_beams: int = 0
    total_merged_rows: int = 0
    total_quantity: int = 0
    total_weight_kg: float = 0.0
    old_total_weight_kg: float = 0.0
    diameter_totals_kg: dict = field(default_factory=dict)
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
