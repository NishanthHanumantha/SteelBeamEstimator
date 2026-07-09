"""Engineering quantity — Phase I.13."""

__all__ = ["QuantityEngine"]


def __getattr__(name: str):
    if name == "QuantityEngine":
        from src.engineering_calculations.quantity.quantity_engine import QuantityEngine

        return QuantityEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
