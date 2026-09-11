"""Prepare beam crops for Hybrid Vision without rewriting T1.

T1 production only writes opencv_renders for OpenCV-fallback residual beams.
W.6 reuses the existing Phase M.1 DXF renderer and T1.5 geometry envelopes
to produce run-isolated context/detail crops when T1 crops are absent.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PhaseW5_production_hybrid_shadow.config import T1_RENDER_REL
from PhaseW5_production_hybrid_shadow.paths import ENGINE_ROOT
from PhaseW5_production_hybrid_shadow.visual_sources import crop_path, discover_visuals

from .config import OUTPUT_DIRNAME

logger = logging.getLogger("steel_webapp.hybrid_production")

ENVELOPE_REL = (
    "data/output/PhaseT1_geometric_stirrup_evidence/geometry_envelopes.json"
)
W6_CROP_REL = f"data/output/{OUTPUT_DIRNAME}/crops"


def w6_crop_path(staging: Path, beam_id: str) -> Path:
    return Path(staging) / W6_CROP_REL / f"{beam_id}_crop.png"


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _reinforcement_dxf(staging: Path) -> Optional[Path]:
    folder = Path(staging) / "reinforcement"
    if not folder.is_dir():
        return None
    dxfs = sorted(folder.glob("*.dxf"))
    return dxfs[0] if dxfs else None


def _envelope_extent(envelopes: Dict[str, Any], beam_id: str) -> Optional[Tuple[float, float, float, float]]:
    by_beam = envelopes.get("by_beam") if isinstance(envelopes, dict) else None
    rec = (by_beam or {}).get(beam_id) if isinstance(by_beam, dict) else None
    if not isinstance(rec, dict):
        return None
    extent = rec.get("extent")
    if isinstance(extent, (list, tuple)) and len(extent) == 4:
        try:
            return (float(extent[0]), float(extent[1]), float(extent[2]), float(extent[3]))
        except (TypeError, ValueError):
            return None
    try:
        return (
            float(rec["xmin"]),
            float(rec["ymin"]),
            float(rec["xmax"]),
            float(rec["ymax"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _load_renderer():
    import importlib.util
    import sys

    renderer_path = (
        ENGINE_ROOT / "src" / "PhaseM.1_engineering_vision_dataset" / "dxf_renderer.py"
    )
    spec = importlib.util.spec_from_file_location("dxf_renderer_w6", renderer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Phase M.1 dxf_renderer.py is not importable")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dxf_renderer_w6"] = mod
    spec.loader.exec_module(mod)
    return mod


def render_w6_envelope_crop(staging: Path, beam_id: str) -> Dict[str, Any]:
    """Explicit W.6 compatibility renderer: T1.5 envelope + M.1 PNG. Never silent."""
    staging = Path(staging)
    dest = w6_crop_path(staging, beam_id)
    dxf = _reinforcement_dxf(staging)
    if dxf is None or not dxf.is_file():
        return {"ok": False, "path": str(dest), "reason": "REINFORCEMENT_DXF_MISSING"}
    envelopes = _load_json(staging / ENVELOPE_REL) or {}
    extent = _envelope_extent(envelopes, beam_id)
    if extent is None:
        return {"ok": False, "path": str(dest), "reason": "ENVELOPE_EXTENT_MISSING"}
    try:
        renderer = _load_renderer()
    except Exception as exc:
        logger.warning("W.6 renderer unavailable error_type=%s", type(exc).__name__)
        return {"ok": False, "path": str(dest), "reason": f"RENDERER_UNAVAILABLE:{type(exc).__name__}"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        renderer.render_dxf_region_to_png(dxf, dest, extent, render_text=True)
    except Exception as exc:
        logger.warning(
            "W.6 envelope render failed beam_id=%s error_type=%s",
            beam_id,
            type(exc).__name__,
        )
        return {"ok": False, "path": str(dest), "reason": type(exc).__name__, "extent": list(extent)}
    if dest.is_file() and dest.stat().st_size >= 200:
        return {
            "ok": True,
            "path": str(dest),
            "reason": None,
            "extent": list(extent),
            "source": "W6_ENVELOPE_RENDER",
        }
    return {"ok": False, "path": str(dest), "reason": "RENDER_EMPTY", "extent": list(extent)}


def ensure_visuals(staging: Path, *, beam_ids: List[str]) -> Dict[str, Any]:
    """
    Ensure each Hybrid-eligible beam has selected context + detail evidence.

    PRIMARY (W.8): P2.6.10-B.1 adaptive context/detail via M.1 renderer.
    FALLBACK: W.6 T1.5 envelope single crop, or existing T1 OpenCV crop.
    Every fallback is recorded in hybrid_evidence/<beam_id>/evidence_manifest.json.
    """
    staging = Path(staging)
    try:
        from PhaseW8_production_vision_evidence.package import prepare_production_evidence

        return prepare_production_evidence(staging, beam_ids=beam_ids)
    except Exception as exc:
        logger.warning("W.8 evidence adapter failed error_type=%s", type(exc).__name__)
        return _ensure_visuals_w6_legacy(staging, beam_ids=beam_ids, w8_error=type(exc).__name__)


def _ensure_visuals_w6_legacy(
    staging: Path, *, beam_ids: List[str], w8_error: Optional[str] = None
) -> Dict[str, Any]:
    """W.6 compatibility path only. Invoked when the W.8 adapter cannot run."""
    staging = Path(staging)
    visual = discover_visuals(staging, beam_ids=beam_ids)
    missing = [
        bid
        for bid in beam_ids
        if not ((visual.get("by_id") or {}).get(bid) or {}).get("available")
    ]
    report: Dict[str, Any] = {
        "t1_available": int(visual.get("available_count") or 0),
        "missing_before": len(missing),
        "rendered": 0,
        "render_failed": 0,
        "dxf": None,
        "source": "T1_OPENCV_CROP",
        "fallback_status": "W6_LEGACY",
        "fallback_reason": w8_error or "W8_ADAPTER_UNAVAILABLE",
    }
    if not missing:
        sources = {
            str(((visual.get("by_id") or {}).get(bid) or {}).get("source") or "EXISTING")
            for bid in beam_ids
        }
        report["source"] = next(iter(sources)) if len(sources) == 1 else "MIXED"
        return report

    dxf = _reinforcement_dxf(staging)
    report["dxf"] = str(dxf) if dxf else None
    for bid in missing:
        result = render_w6_envelope_crop(staging, bid)
        if result.get("ok"):
            report["rendered"] += 1
        else:
            report["render_failed"] += 1
    if report["rendered"]:
        report["source"] = "T1_ENVELOPE_PLUS_M1_RENDERER"
    return report
