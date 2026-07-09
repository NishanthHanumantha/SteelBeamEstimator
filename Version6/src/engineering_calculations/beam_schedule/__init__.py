"""Beam reinforcement schedule — Phase I.15."""

__all__ = ["BeamScheduleEngine"]


def __getattr__(name: str):
    if name == "BeamScheduleEngine":
        from src.engineering_calculations.beam_schedule.beam_schedule_engine import (
            BeamScheduleEngine,
        )

        return BeamScheduleEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
