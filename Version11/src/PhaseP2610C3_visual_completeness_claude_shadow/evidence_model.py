"""Typed selected-evidence objects. No beam-ID decision logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _selected_candidate(side: Dict[str, Any]) -> Dict[str, Any]:
    path = side.get("selected_path")
    sha = side.get("selected_sha256")
    for c in side.get("candidates") or []:
        if path and c.get("path") == path:
            return c
        if sha and c.get("sha256") == sha:
            return c
    return {}


@dataclass
class SelectedRender:
    crop_type: str
    source_phase: Optional[str]
    path: Optional[str]
    sha256: Optional[str]
    primary_status: Optional[str]
    critical_failure: bool
    selection_status: Optional[str]
    reason_codes: List[str]
    usable_status: bool
    score: float
    foreground_ratio: float
    coverage_x: float
    coverage_y: float
    empty_sides: List[str]
    quality_flags: List[str]
    integrity: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_side(cls, crop_type: str, side: Dict[str, Any]) -> "SelectedRender":
        cand = _selected_candidate(side)
        return cls(
            crop_type=crop_type,
            source_phase=side.get("selected_source_phase"),
            path=side.get("selected_path"),
            sha256=side.get("selected_sha256"),
            primary_status=side.get("selected_primary_status") or cand.get("primary_status"),
            critical_failure=bool(side.get("selected_critical_failure") if side.get("selected_critical_failure") is not None else cand.get("critical_failure")),
            selection_status=side.get("selection_status"),
            reason_codes=list(side.get("selection_reason_codes") or []),
            usable_status=bool(cand.get("usable_status")),
            score=float(cand.get("score") if cand.get("score") is not None else -1.0),
            foreground_ratio=float(cand.get("foreground_ratio") or 0.0),
            coverage_x=float(cand.get("coverage_x") or 0.0),
            coverage_y=float(cand.get("coverage_y") or 0.0),
            empty_sides=list(cand.get("empty_sides") or []),
            quality_flags=list(cand.get("quality_flags") or []),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crop_type": self.crop_type,
            "source_phase": self.source_phase,
            "path": self.path,
            "sha256": self.sha256,
            "primary_status": self.primary_status,
            "critical_failure": self.critical_failure,
            "selection_status": self.selection_status,
            "reason_codes": self.reason_codes,
            "usable_status": self.usable_status,
            "score": self.score,
            "foreground_ratio": self.foreground_ratio,
            "coverage_x": self.coverage_x,
            "coverage_y": self.coverage_y,
            "empty_sides": self.empty_sides,
            "quality_flags": self.quality_flags,
            "integrity": self.integrity,
        }


@dataclass
class BeamEvidence:
    beam_id: str
    context: SelectedRender
    detail: SelectedRender
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "context": self.context.to_dict(),
            "detail": self.detail.to_dict(),
        }


def beam_from_manifest_row(row: Dict[str, Any]) -> BeamEvidence:
    return BeamEvidence(
        beam_id=str(row.get("beam_id") or ""),
        context=SelectedRender.from_side("context", row.get("context") or {}),
        detail=SelectedRender.from_side("detail", row.get("detail") or {}),
        raw=row,
    )


__all__ = ["BeamEvidence", "SelectedRender", "beam_from_manifest_row"]
