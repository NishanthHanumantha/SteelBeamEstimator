"""Beam reinforcement summary — Phase I.12."""

__all__ = ["BeamSummaryEngine"]


def __getattr__(name: str):
    if name == "BeamSummaryEngine":
        from src.engineering_calculations.beam_summary.beam_summary_engine import BeamSummaryEngine

        return BeamSummaryEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
