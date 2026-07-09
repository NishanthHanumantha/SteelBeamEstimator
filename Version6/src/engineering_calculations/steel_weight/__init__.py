"""Steel weight calculation engine — Phase I.11."""

__all__ = ["SteelWeightEngine"]


def __getattr__(name: str):
    if name == "SteelWeightEngine":
        from src.engineering_calculations.steel_weight.steel_weight_engine import SteelWeightEngine

        return SteelWeightEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
