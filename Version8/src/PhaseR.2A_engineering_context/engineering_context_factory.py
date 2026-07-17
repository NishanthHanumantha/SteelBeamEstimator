"""
Engineering Context Factory.

Public entry point for creating an EngineeringContext from a GN DXF path.
Uses the cache so parsing happens at most once per process.

Usage:
    from PhaseR2A.engineering_context_factory import EngineeringContextFactory
    ctx  = EngineeringContextFactory.create(gn_dxf_path, project_id)
    loader = EngineeringContextLoader(ctx)
    cover = loader.get_cover("BEAM")
"""
from __future__ import annotations
import pathlib
from typing import Optional, Tuple

from .engineering_context_model     import EngineeringContext
from .engineering_context_builder   import EngineeringContextBuilder
from .engineering_context_validator import EngineeringContextValidator
from .engineering_context_cache     import get_cached, put_cached
from .engineering_context_loader    import EngineeringContextLoader


class EngineeringContextFactory:
    """
    Discovers the GN DXF path from the beam registry (or accepts an explicit path),
    builds and validates the EngineeringContext, and returns it.
    """

    @classmethod
    def create(
        cls,
        gn_dxf_path: pathlib.Path,
        project_id: str = "UNKNOWN",
        force_rebuild: bool = False,
    ) -> Tuple[EngineeringContext, bool, list]:
        """
        Returns (ctx, validation_passed, warnings).

        Parameters
        ----------
        gn_dxf_path    : Path to the General Notes DXF file.
        project_id     : Optional project identifier string.
        force_rebuild  : If True, bypass cache and re-parse.
        """
        if not force_rebuild:
            cached = get_cached(gn_dxf_path)
            if cached is not None:
                return cached, True, []

        # Build
        builder = EngineeringContextBuilder(gn_dxf_path, project_id)
        ctx = builder.build()

        # Validate
        validator = EngineeringContextValidator()
        passed, warnings = validator.validate(ctx)

        # Cache (even if validation partially failed — the ctx is still usable)
        put_cached(gn_dxf_path, ctx)

        return ctx, passed, warnings

    @classmethod
    def create_from_registry(
        cls, v7_root: pathlib.Path
    ) -> Tuple[Optional[EngineeringContext], bool, list]:
        """
        Discovers the GN DXF path from the V.ROOT.1 beam registry or the
        Benchmark_Set_2/general_notes/ directory, then builds the context.
        """
        gn_path = cls._discover_gn_path(v7_root)
        if gn_path is None:
            return None, False, ["EngineeringContextFactory: GN DXF not found."]

        project_id = cls._read_project_id(v7_root)
        return cls.create(gn_path, project_id)

    @classmethod
    def _discover_gn_path(cls, v7_root: pathlib.Path) -> Optional[pathlib.Path]:
        import json

        # 1. Check beam_registry.json
        registry = v7_root / "src" / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
        if registry.exists():
            try:
                reg = json.loads(registry.read_text("utf-8"))
                gn = (
                    reg.get("general_notes_dxf")
                    or reg.get("general_notes", {}).get("path")
                    or reg.get("drawings", {}).get("general_notes")
                )
                if gn:
                    p = pathlib.Path(gn)
                    if not p.is_absolute():
                        p = v7_root / p
                    if p.exists():
                        return p
            except Exception:
                pass

        # 2. Scan data dir
        gn_dir = v7_root / "data" / "Benchmark_Set_2" / "general_notes"
        if gn_dir.exists():
            dxf_files = sorted(gn_dir.glob("*.dxf"))
            if dxf_files:
                return dxf_files[0]

        return None

    @classmethod
    def _read_project_id(cls, v7_root: pathlib.Path) -> str:
        import json
        registry = v7_root / "src" / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
        if registry.exists():
            try:
                reg = json.loads(registry.read_text("utf-8"))
                return (
                    reg.get("project_id")
                    or reg.get("project_name")
                    or reg.get("metadata", {}).get("project_id", "UNKNOWN")
                )
            except Exception:
                pass
        return "UNKNOWN"
