"""Estimator audit engine — Phase QA.1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.estimator_validation.audit_builder import AuditBuilder
from src.estimator_validation.audit_types import PHASE, AUDIT_VERSION, default_paths


class AuditEngine:
    """Run read-only estimator output audit."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        builder = AuditBuilder(self._paths)
        artifacts = builder.build()
        return {
            "phase": PHASE,
            "audit_version": AUDIT_VERSION,
            "generated_workbook": str(self._paths["generated_workbook"]),
            "estimator_workbook": str(self._paths["estimator_workbook"]),
            "output_dir": str(self._paths["output_dir"]),
            **artifacts,
        }
