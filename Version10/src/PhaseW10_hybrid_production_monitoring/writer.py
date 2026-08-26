"""Fail-safe persist of W.10 monitoring artefacts. Never raises to the caller."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .config import BEAM_REVIEW_FILENAME, MONITOR_FILENAME, OUTPUT_DIRNAME
from .monitor import build_beam_reviews, build_monitor
from .sanitize import sanitize

logger = logging.getLogger("steel_webapp.hybrid_production")


def output_dir(staging: Path) -> Path:
    return Path(staging) / "data" / "output" / OUTPUT_DIRNAME


def _dump(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize(payload), indent=2, default=str), encoding="utf-8")


def write_run_monitor(
    *,
    staging: Path,
    run_id: str,
    live_result: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Write hybrid_production_monitor.json and beam_evidence_reviews.json.

    Returns the monitor payload, or None if monitoring itself failed.
    Must never raise — estimation / Excel must continue.
    """
    try:
        staging = Path(staging)
        monitor = build_monitor(staging, run_id=run_id, live_result=live_result)
        coverage = {}
        try:
            cov_path = staging / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_coverage.json"
            if cov_path.is_file():
                coverage = json.loads(cov_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            coverage = {}
        shadow = None
        try:
            sh_path = staging / "data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json"
            if sh_path.is_file():
                shadow = json.loads(sh_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            shadow = None
        reviews, _historical = build_beam_reviews(
            staging=staging,
            coverage=coverage if isinstance(coverage, dict) else {},
            shadow=shadow,
        )
        dest = output_dir(staging)
        _dump(dest / MONITOR_FILENAME, monitor)
        _dump(
            dest / BEAM_REVIEW_FILENAME,
            {
                "run_id": run_id,
                "beam_count": len(reviews),
                "beams": sanitize(reviews),
            },
        )
        return monitor
    except Exception as exc:
        logger.warning("W.10 monitoring failed error_type=%s", type(exc).__name__)
        return None
