"""
r13_injector.py — Apply SpacerRuleEngine onto R.1.3 BeamEngineeringModel lists.
MODEL_VERSION: 9.1.0

Purely additive: appends SPACER_BAR EngineeringBarModel rows. Never mutates
existing bars. Behind enable_spacer_rule (caller responsibility).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .spacer_engine import (
    RULE_VERSION,
    SPACER_DIA_MM,
    SPACER_SPACING_MM,
    compute_spacers_for_beam,
    face_for_role,
    is_longitudinal_role,
)
from .spacer_models import BeamSpacerInput, LongitudinalGroup, SpacerRow

logger = logging.getLogger(__name__)

MODEL_VERSION = "9.1.0"


def _meta(bar: Any) -> Dict[str, Any]:
    return dict(getattr(bar, "engineering_metadata", None) or {})


def _bar_to_group(bar: Any, span_mm: Optional[float] = None) -> Optional[LongitudinalGroup]:
    role = str(getattr(bar, "bar_role", "") or "").upper()
    if not is_longitudinal_role(role):
        return None
    face = face_for_role(role)
    if face is None:
        return None
    meta = _meta(bar)
    start = meta.get("piece_start_mm")
    end = meta.get("piece_end_mm")
    clear = meta.get("cut_length_mm")
    conf = "HIGH"
    # Prefer geometric piece length when available
    if start is not None and end is not None:
        try:
            if float(end) > float(start):
                clear = clear or (float(end) - float(start))
        except (TypeError, ValueError):
            pass
    else:
        conf = "MISSING"
        # Synthesize MAIN full-span extent from beam clear span so overlap math works
        if "MAIN" in role and span_mm is not None and float(span_mm) > 0:
            start = 0.0
            end = float(span_mm)
            conf = "LOW"
            clear = clear or float(span_mm)
    if start is not None and end is not None:
        if str(meta.get("extent") or "").upper() in ("", "UNKNOWN") and conf == "HIGH":
            conf = "LOW"
    # EXTRA clear length: prefer piece length over hooked cut length when both exist
    if "EXTRA" in role and start is not None and end is not None:
        try:
            piece_len = float(end) - float(start)
            if piece_len > 0:
                clear = piece_len
        except (TypeError, ValueError):
            pass
    return LongitudinalGroup(
        role=role,
        face=face,
        start_mm=float(start) if start is not None else None,
        end_mm=float(end) if end is not None else None,
        clear_length_mm=float(clear) if clear is not None else None,
        extent_confidence=conf,
        diameter_mm=getattr(bar, "diameter_mm", None),
        quantity=int(getattr(bar, "quantity", 1) or 1),
    )


def _beam_to_input(beam: Any, cover_mm: Optional[float]) -> BeamSpacerInput:
    geom = dict(getattr(beam, "geometry", None) or {})
    width = geom.get("width_mm")
    try:
        width_f = float(width) if width is not None else None
    except (TypeError, ValueError):
        width_f = None

    span_mm = None
    try:
        if geom.get("clear_span_mm") is not None:
            span_mm = float(geom["clear_span_mm"])
    except (TypeError, ValueError):
        span_mm = None

    groups: List[LongitudinalGroup] = []
    already = False
    for bar in getattr(beam, "bars", None) or []:
        role = str(getattr(bar, "bar_role", "") or "").upper()
        if role == "SPACER_BAR":
            # Only treat M.2-emitted or true spacers as dedup triggers.
            # Legacy misclassified bars (no SpacerRuleEngine source) do NOT block emission.
            meta = _meta(bar)
            if meta.get("source") == "SpacerRuleEngine" or meta.get("rule_version") == "M.2":
                already = True
            continue
        g = _bar_to_group(bar, span_mm=span_mm)
        if g is not None:
            if g.clear_length_mm is None and span_mm is not None and span_mm > 0:
                g.clear_length_mm = span_mm
            groups.append(g)

    return BeamSpacerInput(
        beam_id=str(getattr(beam, "beam_id", "")),
        beam_width_mm=width_f,
        cover_mm=cover_mm,
        groups=groups,
        already_has_spacer=already,
    )


def _row_to_engineering_bar(row: SpacerRow, bar_cls: type, cover_mm: float) -> Any:
    zone = "TOP_ZONE" if row.face == "TOP" else "BOTTOM_ZONE"
    return bar_cls(
        beam_id=row.beam_id,
        bar_role="SPACER_BAR",
        diameter_mm=float(SPACER_DIA_MM),
        quantity=int(row.quantity),
        zone=zone,
        spacing_mm=float(SPACER_SPACING_MM),
        cover_mm=int(round(cover_mm)),
        steel_grade="Y",
        source_phase="M.2",
        bar_label=f"SPACER {SPACER_DIA_MM}@{SPACER_SPACING_MM}",
        engineering_metadata=row.to_engineering_metadata(),
    )


def inject_spacers(
    beam_models: Sequence[Any],
    cover_mm: Optional[float],
    *,
    bar_model_cls: type,
) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Append SPACER_BAR rows to each beam model. Returns (new_list, report).
    `beam_models` items must expose beam_id, bars, geometry like BeamEngineeringModel.
    Caller must pass EngineeringBarModel (keeps this module free of R.1.3 imports).
    """
    out: List[Any] = []
    report: Dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "rule_version": RULE_VERSION,
        "enabled": True,
        "beams_processed": 0,
        "beams_skipped": 0,
        "rows_emitted": 0,
        "extent_fallback_rows": 0,
        "cover_fallback": cover_mm is None,
        "cover_mm_used": cover_mm,
        "warnings": [],
        "per_beam": [],
    }

    for beam in beam_models:
        report["beams_processed"] += 1
        inp = _beam_to_input(beam, cover_mm)
        result = compute_spacers_for_beam(inp)
        report["warnings"].extend(result.warnings)

        # Shallow-copy beam with extended bars list (do not mutate caller's list in-place unexpectedly)
        new_bars = list(getattr(beam, "bars", None) or [])
        if result.skipped:
            report["beams_skipped"] += 1
            for w in result.warnings:
                logger.warning("[M.2 SpacerRule] %s", w)
            out.append(beam)
            report["per_beam"].append({
                "beam_id": result.beam_id,
                "skipped": True,
                "skip_reason": result.skip_reason,
                "rows": 0,
            })
            continue

        cover_used = float(cover_mm) if cover_mm is not None else (
            result.rows[0].cover_mm if result.rows else 30.0
        )
        for row in result.rows:
            new_bars.append(_row_to_engineering_bar(row, bar_model_cls, cover_used))
            report["rows_emitted"] += 1
            if row.extent_fallback:
                report["extent_fallback_rows"] += 1

        # Reconstruct beam with same type if possible
        try:
            rebuilt = type(beam)(
                beam_id=beam.beam_id,
                beam_name=getattr(beam, "beam_name", beam.beam_id),
                bars=new_bars,
                geometry=dict(getattr(beam, "geometry", None) or {}),
                source_phase=getattr(beam, "source_phase", "R.1.3"),
                classification_complete=getattr(beam, "classification_complete", True),
            )
            out.append(rebuilt)
        except Exception:
            beam.bars = new_bars  # type: ignore[attr-defined]
            out.append(beam)

        report["per_beam"].append({
            "beam_id": result.beam_id,
            "skipped": False,
            "rows": len(result.rows),
            "quantities": [r.quantity for r in result.rows],
            "faces": [r.face for r in result.rows],
        })
        for w in result.warnings:
            logger.warning("[M.2 SpacerRule] %s", w)

    return out, report


def load_enable_flag(engine_root: Any) -> bool:
    """Read enable_spacer_rule from Version9/config/estimator_rules.yaml (default True)."""
    try:
        import pathlib
        import yaml  # type: ignore
        root = pathlib.Path(engine_root)
        path = root / "config" / "estimator_rules.yaml"
        if not path.is_file():
            return True
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        spacer = data.get("spacer") or {}
        if "enable_spacer_rule" in spacer:
            return bool(spacer["enable_spacer_rule"])
        return True
    except Exception:
        return True
