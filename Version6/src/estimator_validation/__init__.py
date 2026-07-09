"""Estimator validation package — Phase QA.1."""

__all__ = ["AuditEngine"]


def __getattr__(name: str):
    if name == "AuditEngine":
        from src.estimator_validation.audit_engine import AuditEngine

        return AuditEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
