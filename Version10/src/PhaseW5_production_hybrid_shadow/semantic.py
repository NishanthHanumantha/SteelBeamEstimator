"""Build Hybrid semantic observations without D.3/D.4 engineering calculation."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .paths import ensure_src_on_path


def resolve_semantic(
    *,
    beam_id: str,
    model: Optional[Dict[str, Any]],
    vision_row: Optional[Dict[str, Any]],
    provenance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ensure_src_on_path()
    from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.hybrid_runner_adapter import (  # noqa: WPS433
        build_deterministic_payload,
        build_vision_payload,
    )
    from PhaseP2610D2_shadow_hybrid_semantic_resolver.resolver import (  # noqa: WPS433
        resolve_hybrid_beam,
    )

    vision = build_vision_payload(vision_row)
    deterministic = build_deterministic_payload(model)
    vision_used = bool(
        vision.get("usable")
        and (vision.get("groups") or vision.get("stirrups") or vision.get("target_identified"))
    )
    source = dict(provenance or {})
    source.setdefault("kind", "HYBRID" if vision_used else "FALLBACK")
    source.setdefault("vision_used", vision_used)
    source.setdefault("mode", "PRODUCTION_SHADOW")
    hybrid = resolve_hybrid_beam(
        beam_id=beam_id,
        vision=vision,
        deterministic=deterministic,
        source_provenance=source,
    )
    return {
        "beam_id": beam_id,
        "vision_used": vision_used,
        "vision": vision,
        "deterministic": {
            "group_count": len(deterministic.get("groups") or []),
            "stirrup_count": len(deterministic.get("stirrups") or []),
        },
        "hybrid_semantic": hybrid,
    }
