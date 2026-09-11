"""Thin web wrapper around the W.5 Hybrid shadow adapter. Fail-closed."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import config

logger = logging.getLogger("steel_webapp.hybrid_shadow")

_SRC = (config.ENGINE_ROOT / "src").resolve()
_V10 = config.ENGINE_ROOT.resolve()
for _p in (str(_V10), str(_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PhaseW5_production_hybrid_shadow.config import MODE_OFF  # noqa: E402
from PhaseW5_production_hybrid_shadow.settings import (  # noqa: E402
    HybridSettings,
    health_payload,
    hybrid_mode,
    load_settings,
)


def hybrid_health() -> Dict[str, Any]:
    return health_payload()


def maybe_run_hybrid_shadow(
    *,
    run_id: str,
    staging: Path,
    client_override: Optional[Callable] = None,
    settings: Optional[HybridSettings] = None,
) -> Optional[Dict[str, Any]]:
    """
    Collect Hybrid summary after the deterministic/Hybrid pipeline.

    When W.6 HYBRID is a production stage, do not invoke Claude again.
    When HYBRID_MODE=off, return None.
    Never raises into the estimation caller.
    """
    try:
        cfg = settings or load_settings()
        if cfg.mode == MODE_OFF:
            logger.info("Hybrid skipped run_id=%s mode=off", run_id)
            return None
        if config.hybrid_stage_configured():
            from PhaseW6_hybrid_production_authority.orchestrator import (  # noqa: WPS433
                load_public_summary,
            )

            summary = load_public_summary(Path(staging))
            if summary:
                return summary
            return {
                "hybrid_mode": cfg.mode,
                "hybrid_status": "MISSING_W6_ARTEFACT",
                "reason": "W6_OBSERVABILITY_MISSING",
                "request_count": 0,
                "production_authority_applied": False,
            }
        from PhaseW5_production_hybrid_shadow.adapter import (  # noqa: WPS433
            public_summary,
            run_hybrid_shadow,
        )

        result = run_hybrid_shadow(
            run_id=run_id,
            staging=Path(staging),
            client_override=client_override,
            settings=cfg,
            persist=True,
        )
        logger.info(
            "Hybrid shadow finished run_id=%s status=%s requests=%s "
            "latency_s=%s estimated_cost_usd=%s cost_basis=%s excel_unchanged=%s",
            run_id,
            result.get("hybrid_status"),
            result.get("request_count"),
            result.get("hybrid_latency_s"),
            result.get("estimated_cost_usd"),
            result.get("cost_basis"),
            result.get("excel_unchanged"),
        )
        return public_summary(result)
    except Exception:
        logger.exception("Hybrid wrapper failed run_id=%s", run_id)
        return {
            "hybrid_mode": hybrid_mode(),
            "hybrid_status": "ERROR",
            "reason": "WRAPPER_EXCEPTION",
            "request_count": 0,
            "excel_unchanged": True,
        }
