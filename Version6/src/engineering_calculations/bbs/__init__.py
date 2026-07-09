"""Bar bending schedule foundation — Phase I.10."""

__all__ = ["BbsEngine"]


def __getattr__(name: str):
    if name == "BbsEngine":
        from src.engineering_calculations.bbs.bbs_engine import BbsEngine

        return BbsEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
