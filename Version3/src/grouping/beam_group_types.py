"""Typed structures for Phase D.3 beam grouping."""

from typing import Any, Dict, List, Literal, Optional, TypedDict

OwnershipMode = Literal["SINGLE", "GROUP"]
ValidationStatus = Literal["PASS", "WARN", "FAIL"]


class BeamGroupMember(TypedDict):
    beam_mark: str
    row_id: int
    cell_bbox: Dict[str, float]
    detail_band: Dict[str, float]
    sketch_ids: List[str]
    occurrence_ids: List[int]


class BeamGroup(TypedDict):
    beam_group_id: str
    members: List[str]
    member_details: List[BeamGroupMember]
    centroid: Dict[str, float]
    bounding_box: Dict[str, float]
    detail_band: Dict[str, float]
    row_id: int
    is_multi_beam: bool


class SharedAnnotation(TypedDict, total=False):
    annotation_id: str
    clean_text: str
    x: float
    y: float
    annotation_type: str
    entity_type: str
    ownership_mode: OwnershipMode
    beam_group_id: Optional[str]
    member_beams: List[str]
    geometric_member_beams: List[str]
    duplicate_member_beams: List[str]
    detection_signals: List[str]
    original_beam_mark: str
    original_sketch_id: str
    original_occurrence_id: int
    final_status: str
    engineering_source: str


class GroupOwnershipRecord(TypedDict, total=False):
    annotation_id: str
    ownership_mode: OwnershipMode
    beam_group_id: str
    member_beams: List[str]
    ownership_source: str
    clean_text: str
    x: float
    y: float
    annotation_type: str
    original_beam_mark: str
    original_sketch_id: str


class ExpandedAnnotation(TypedDict, total=False):
    shared_annotation_id: str
    beam_group_id: str
    expanded_from_group: bool
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    clean_text: str
    x: float
    y: float
    annotation_type: str
    entity_type: str
    final_status: str
    engineering_source: str
    original_annotation_reference: Dict[str, Any]
