"""Framing plan beam geometry extraction (Phase F)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.framing.beam_geometry_pipeline import BeamGeometryPipeline
    from src.framing.framing_beam_extractor import FramingBeamExtractor

__all__ = ["BeamGeometryPipeline", "FramingBeamExtractor"]


def __getattr__(name: str):
    if name == "BeamGeometryPipeline":
        from src.framing.beam_geometry_pipeline import BeamGeometryPipeline

        return BeamGeometryPipeline
    if name == "FramingBeamExtractor":
        from src.framing.framing_beam_extractor import FramingBeamExtractor

        return FramingBeamExtractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
