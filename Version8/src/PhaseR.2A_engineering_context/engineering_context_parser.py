"""
Engineering Context Parser — master coordinator.

Thin wrapper that calls the factory and returns the loader directly.
Used by production pipeline modules to access engineering context.

Usage:
    from PhaseR2A.engineering_context_parser import parse_engineering_context
    loader = parse_engineering_context(v7_root)
    cover  = loader.get_cover("BEAM")
"""
from __future__ import annotations
import pathlib
from typing import Optional, Tuple

from .engineering_context_loader  import EngineeringContextLoader
from .engineering_context_factory import EngineeringContextFactory


def parse_engineering_context(
    v7_root: pathlib.Path,
    force_rebuild: bool = False,
) -> Tuple[Optional[EngineeringContextLoader], bool, list]:
    """
    Discovers GN DXF, builds EngineeringContext, and returns a loader.

    Returns (loader_or_None, validation_passed, warnings).
    If parsing fails, returns None and the caller should use existing constants.
    """
    ctx, passed, warnings = EngineeringContextFactory.create_from_registry(
        v7_root
    )
    if ctx is None:
        return None, False, warnings

    loader = EngineeringContextLoader(ctx)
    return loader, passed, warnings
