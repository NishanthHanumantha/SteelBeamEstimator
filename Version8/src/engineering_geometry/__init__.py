"""Engineering Geometry Association — Phase H.2."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.engineering_geometry.geometry_association_builder import GeometryAssociationBuilder

__all__ = ["GeometryAssociationBuilder"]


def __getattr__(name: str):
    if name == "GeometryAssociationBuilder":
        from src.engineering_geometry.geometry_association_builder import GeometryAssociationBuilder

        return GeometryAssociationBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
