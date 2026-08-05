"""
QA.2B.1 — WorkbookValidator
MODEL_VERSION: 9.6.1
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .workbook_utils import inspect_workbook_contents, iso_mtime, sha256_file

MODEL_VERSION = "9.6.1"


class WorkbookValidator:
    def validate(
        self,
        workbook: Path,
        *,
        prior_sha256: Optional[str] = None,
        regeneration_started_utc: Optional[str] = None,
    ) -> Dict[str, Any]:
        workbook = Path(workbook)
        checks: Dict[str, bool] = {}
        contents = inspect_workbook_contents(workbook) if workbook.exists() else {
            "ok": False,
            "row_count": 0,
            "beam_count": 0,
            "bar_count": 0,
            "steel_kg": 0.0,
            "error": "missing",
        }
        exists = workbook.exists()
        sha = sha256_file(workbook) if exists else None
        mtime = iso_mtime(workbook) if exists else None

        checks["workbook_exists"] = exists
        checks["workbook_row_count_gt_0"] = int(contents.get("row_count") or 0) > 0
        checks["beam_count_gt_0"] = int(contents.get("beam_count") or 0) > 0
        checks["steel_quantities_generated"] = (
            float(contents.get("steel_kg") or 0) > 0
            or int(contents.get("bar_count") or 0) > 0
            or int(contents.get("row_count") or 0) > 0
        )
        checks["not_same_hash_as_prior"] = bool(
            prior_sha256 and sha and sha != prior_sha256
        ) if prior_sha256 else True
        if regeneration_started_utc and mtime:
            checks["workbook_timestamp_updated"] = mtime >= regeneration_started_utc
        else:
            checks["workbook_timestamp_updated"] = exists

        return {
            "model_version": MODEL_VERSION,
            "path": str(workbook),
            "sha256": sha,
            "mtime_utc": mtime,
            "contents": contents,
            "checks": checks,
            "pass": all(checks.values()),
        }
