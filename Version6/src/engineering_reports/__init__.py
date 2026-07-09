"""Engineering report model — Phase I.16."""

__all__ = ["EngineeringReportEngine"]


def __getattr__(name: str):
    if name == "EngineeringReportEngine":
        from src.engineering_reports.engineering_report_engine import EngineeringReportEngine

        return EngineeringReportEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
