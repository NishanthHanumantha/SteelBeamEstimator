"""Live Claude invocation wrapper. Reuses E.2 call_live_beam. Fail-closed."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .paths import ensure_src_on_path


def call_shadow_beam(
    *,
    version10_root: Path,
    beam_id: str,
    render_path: Path,
    client_override: Optional[Callable] = None,
    context_path: Optional[Path] = None,
    detail_path: Optional[Path] = None,
    context_source: Optional[str] = None,
    detail_source: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_src_on_path()
    from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.live_caller import (  # noqa: WPS433
        call_live_beam,
    )

    ctx = Path(context_path or render_path)
    det = Path(detail_path or render_path)
    ctx_src = context_source or "W8_EVIDENCE"
    det_src = detail_source or context_source or "W8_EVIDENCE"
    return call_live_beam(
        version10_root=Path(version10_root),
        beam_id=str(beam_id),
        render_path=ctx,
        context_path=ctx,
        detail_path=det,
        context_source=str(ctx_src),
        detail_source=str(det_src),
        client_override=client_override,
    )
