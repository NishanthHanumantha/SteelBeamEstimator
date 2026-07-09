"""Material quantification — Phase I.14."""

__all__ = ["MaterialQuantificationEngine"]


def __getattr__(name: str):
    if name == "MaterialQuantificationEngine":
        from src.engineering_calculations.material_quantification.material_engine import (
            MaterialQuantificationEngine,
        )

        return MaterialQuantificationEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
