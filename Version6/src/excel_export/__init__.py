"""Excel export package — Phase I.17."""

__all__ = ["ExcelExportEngine"]


def __getattr__(name: str):
    if name == "ExcelExportEngine":
        from src.excel_export.excel_export_engine import ExcelExportEngine

        return ExcelExportEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
