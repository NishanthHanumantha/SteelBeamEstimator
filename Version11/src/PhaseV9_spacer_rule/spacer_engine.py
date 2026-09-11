"""
spacer_engine.py — Pure deterministic spacer-bar rule (no I/O).
MODEL_VERSION: 9.2.0  (W.18B: geometric overlap, round-half-up qty)

Estimation-team ruling (hardcoded, exceptional):
  SPACER_DIA_MM = 25, SPACER_SPACING_MM = 1000
  Trigger: ≥2 longitudinal groups on the SAME face (MAIN+EXTRA).
  Cover is the ONLY context input (from R.2A).
  Overlap length is piece extent intersection, never fabrication cut.
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Sequence, Tuple

from .spacer_models import (
    BeamSpacerInput,
    BeamSpacerResult,
    Extent,
    LongitudinalGroup,
    SpacerRow,
    SpacerZone,
)

MODEL_VERSION = "9.2.0"
RULE_VERSION = "M.2"

# --- HARDCODED, NON-NEGOTIABLE (do not read from General Notes / context) ---
SPACER_DIA_MM: int = 25
SPACER_SPACING_MM: int = 1000

COVER_FALLBACK_MM: float = 30.0
EXTENT_EPSILON_MM: float = 1.0

_LONGITUDINAL_ROLES = frozenset({
    "TOP_MAIN", "TOP_EXTRA", "BOTTOM_MAIN", "BOTTOM_EXTRA",
})
_TOP_ROLES = frozenset({"TOP_MAIN", "TOP_EXTRA"})
_BOTTOM_ROLES = frozenset({"BOTTOM_MAIN", "BOTTOM_EXTRA"})

_LABEL_STRIP = re.compile(r"(?:#(?:L|R|LEFT|RIGHT)\b.*)$", re.IGNORECASE)


def round_half_up(value: float) -> int:
    """Nearest integer; .5 always rounds upward. Not banker's rounding."""
    if value < 0:
        return -int(math.floor(-float(value) + 0.5))
    return int(math.floor(float(value) + 0.5))


def spacer_raw_quantity(zone_length_mm: float) -> float:
    """raw = (overlap_mm / 1000) + 1. Zero when overlap is non-positive."""
    if zone_length_mm <= 0:
        return 0.0
    return (float(zone_length_mm) / float(SPACER_SPACING_MM)) + 1.0


def spacer_quantity(zone_length_mm: float) -> int:
    """N = round_half_up((overlap_length_mm / SPACER_SPACING_MM) + 1)."""
    raw = spacer_raw_quantity(zone_length_mm)
    if raw <= 0:
        return 0
    return round_half_up(raw)


def cut_length_mm(beam_width_mm: float, cover_mm: float) -> float:
    return float(beam_width_mm) - 2.0 * float(cover_mm)


def compute_overlap_zones(
    extents: Sequence[Extent],
    epsilon_mm: float = EXTENT_EPSILON_MM,
) -> List[Tuple[float, float]]:
    """
    Maximal intervals where ≥2 groups coexist (sweep-line merge).
    Distinct layers that share a numeric interval still each contribute
    +1 (do not unique-collapse before calling this).
    """
    events: List[Tuple[float, int]] = []
    for start, end in extents:
        s, e = float(start), float(end)
        if e - s < epsilon_mm:
            continue
        events.append((s, +1))
        events.append((e, -1))
    if not events:
        return []

    events.sort(key=lambda ev: (ev[0], -ev[1]))

    zones: List[Tuple[float, float]] = []
    active = 0
    zone_start: Optional[float] = None
    for pos, delta in events:
        prev = active
        active += delta
        if prev < 2 and active >= 2:
            zone_start = pos
        elif prev >= 2 and active < 2 and zone_start is not None:
            if pos - zone_start >= epsilon_mm:
                zones.append((zone_start, pos))
            zone_start = None
    return zones


def _face_of_role(role: str) -> Optional[str]:
    r = (role or "").upper()
    if r in _TOP_ROLES:
        return "TOP"
    if r in _BOTTOM_ROLES:
        return "BOTTOM"
    return None


def _norm_extra_label(label: str) -> str:
    s = _LABEL_STRIP.sub("", str(label or ""))
    return re.sub(r"[\s\-]", "", s).upper()


def _extra_family_key(group: LongitudinalGroup) -> Tuple:
    dia = None
    if group.diameter_mm is not None:
        try:
            dia = int(round(float(group.diameter_mm)))
        except (TypeError, ValueError):
            dia = None
    return (group.face, (group.role or "").upper(), dia, _norm_extra_label(group.bar_label))


def _extra_kind(group: LongitudinalGroup, span_mm: Optional[float]) -> str:
    pt = str(group.piece_type or "").upper()
    if pt.endswith("_LEFT") or pt in ("TOP_EXTRA_LEFT", "BOTTOM_EXTRA_LEFT"):
        return "LEFT"
    if pt.endswith("_RIGHT") or pt in ("TOP_EXTRA_RIGHT", "BOTTOM_EXTRA_RIGHT"):
        return "RIGHT"
    if "CONTINUOUS" in pt or pt in ("CONTINUOUS_BAR", "CONTINUOUS"):
        return "CONTINUOUS"
    if not group.has_extent() or span_mm is None or float(span_mm) <= 0:
        return "OTHER"
    start, end = float(group.start_mm), float(group.end_mm)
    span = float(span_mm)
    tol = max(EXTENT_EPSILON_MM, 0.05 * span)
    if abs(start) <= EXTENT_EPSILON_MM and abs(end - span) <= EXTENT_EPSILON_MM:
        return "CONTINUOUS"
    if abs(start) <= EXTENT_EPSILON_MM and abs(end - 0.25 * span) <= tol:
        return "LEFT"
    if abs(end - span) <= EXTENT_EPSILON_MM and abs(start - 0.75 * span) <= tol:
        return "RIGHT"
    return "OTHER"


def _dedupe_extra_piece_representations(
    extras: List[LongitudinalGroup],
    span_mm: Optional[float],
    warnings: List[str],
) -> List[LongitudinalGroup]:
    """
    CONTINUOUS_BAR + LEFT + RIGHT of the same extra family are piece
    representations of one reinforcement condition. Keep LEFT/RIGHT
    (distinct physical zones); drop the CONTINUOUS duplicate.
    """
    if len(extras) < 2:
        return extras
    families: Dict[Tuple, List[LongitudinalGroup]] = {}
    for g in extras:
        families.setdefault(_extra_family_key(g), []).append(g)
    out: List[LongitudinalGroup] = []
    for key, members in families.items():
        kinds = {id(g): _extra_kind(g, span_mm) for g in members}
        has_support = any(k in ("LEFT", "RIGHT") for k in kinds.values())
        has_continuous = any(k == "CONTINUOUS" for k in kinds.values())
        kept: List[LongitudinalGroup] = []
        if has_support and has_continuous:
            warnings.append(
                f"{key[0]}: dropping CONTINUOUS extra piece representation "
                f"for family {key} (LEFT/RIGHT extents retained)"
            )
            for g in members:
                if kinds[id(g)] != "CONTINUOUS":
                    kept.append(g)
        else:
            kept = list(members)
        # Identical extents within the family (true duplicates) → one copy
        uniq: List[LongitudinalGroup] = []
        seen: List[Extent] = []
        for g in kept:
            ext = g.extent()
            if ext is not None and any(
                abs(ext[0] - s) <= EXTENT_EPSILON_MM
                and abs(ext[1] - e) <= EXTENT_EPSILON_MM
                for s, e in seen
            ):
                continue
            if ext is not None:
                seen.append(ext)
            uniq.append(g)
        out.extend(uniq)
    return out


def _dedupe_zones(zones: List[SpacerZone], epsilon_mm: float = EXTENT_EPSILON_MM) -> List[SpacerZone]:
    """Collapse zones with identical intervals on the same face (not same length)."""
    if not zones:
        return []
    ranked = sorted(zones, key=lambda z: (z.face, z.start_mm, z.end_mm, z.extent_fallback))
    out: List[SpacerZone] = []
    for z in ranked:
        if out:
            prev = out[-1]
            if (
                prev.face == z.face
                and abs(prev.start_mm - z.start_mm) <= epsilon_mm
                and abs(prev.end_mm - z.end_mm) <= epsilon_mm
            ):
                if prev.extent_fallback and not z.extent_fallback:
                    out[-1] = z
                elif prev.quantity < z.quantity:
                    out[-1] = z
                continue
        out.append(z)
    return out


def _zones_for_face(
    groups: List[LongitudinalGroup],
    face: str,
    span_mm: Optional[float] = None,
) -> Tuple[List[SpacerZone], List[str]]:
    """Compute spacer zones for one face from geometric piece extents only."""
    warnings: List[str] = []
    face_groups = [g for g in groups if g.face == face and g.role in _LONGITUDINAL_ROLES]
    if len(face_groups) < 2:
        return [], warnings

    mains = [g for g in face_groups if "MAIN" in g.role.upper()]
    extras = [g for g in face_groups if "EXTRA" in g.role.upper()]
    if not extras:
        # Existing ruling: two MAINs without EXTRA → no spacers.
        return [], warnings
    if not mains:
        return [], warnings

    extras = _dedupe_extra_piece_representations(extras, span_mm, warnings)

    with_extent: List[LongitudinalGroup] = []
    for g in mains + extras:
        if g.has_extent():
            with_extent.append(g)
        elif "EXTRA" in g.role.upper():
            warnings.append(
                f"{face}: EXTRA {g.role} missing piece_start_mm/piece_end_mm; "
                f"overlap unresolved (fabrication cut_length_mm is not used)"
            )

    extra_with_extent = [g for g in extras if g.has_extent()]
    main_with_extent = [g for g in mains if g.has_extent()]
    if not extra_with_extent or not main_with_extent:
        if extras and not extra_with_extent:
            warnings.append(
                f"{face}: no geometric extra extents — spacer not emitted"
            )
        return [], warnings

    # Keep every layer's extent. MAIN[0,span] and EXTRA[0,span] both count.
    extents: List[Extent] = []
    for g in main_with_extent + extra_with_extent:
        ext = g.extent()
        if ext is not None:
            extents.append(ext)

    zones: List[SpacerZone] = []
    for start, end in compute_overlap_zones(extents):
        length = end - start
        raw = spacer_raw_quantity(length)
        qty = spacer_quantity(length)
        if qty > 0:
            zones.append(SpacerZone(
                face=face, start_mm=start, end_mm=end,
                length_mm=length, quantity=qty, extent_fallback=False,
                raw_quantity=raw,
            ))
    return _dedupe_zones(zones), warnings


def compute_spacers_for_beam(beam: BeamSpacerInput) -> BeamSpacerResult:
    """
    Pure engine: compute SPACER_BAR rows for one beam.
    Never modifies existing groups. Additive only.
    One row per physical overlap zone (LEFT/RIGHT stay separate here).
    """
    result = BeamSpacerResult(beam_id=beam.beam_id)

    if beam.already_has_spacer:
        result.skipped = True
        result.skip_reason = "already_has_spacer"
        result.warnings.append(
            f"{beam.beam_id}: SPACER_BAR already present — skip emission (dedup)"
        )
        return result

    if beam.beam_width_mm is None or float(beam.beam_width_mm) <= 0:
        result.skipped = True
        result.skip_reason = "missing_beam_width"
        result.warnings.append(
            f"{beam.beam_id}: beam_width_mm unavailable — skip spacer emission"
        )
        return result

    cover_fallback = False
    cover = beam.cover_mm
    if cover is None:
        cover = COVER_FALLBACK_MM
        cover_fallback = True
        result.warnings.append(
            f"{beam.beam_id}: cover_beam_mm absent — using fallback {COVER_FALLBACK_MM} mm"
        )

    width = float(beam.beam_width_mm)
    cut = cut_length_mm(width, float(cover))
    if cut <= 0:
        result.skipped = True
        result.skip_reason = "non_positive_cut_length"
        result.warnings.append(
            f"{beam.beam_id}: cut_length_mm={cut} non-positive — skip"
        )
        return result

    span_mm = beam.clear_span_mm
    if span_mm is None:
        ends = [g.end_mm for g in beam.groups if g.has_extent()]
        span_mm = max(ends) if ends else None

    for face in ("TOP", "BOTTOM"):
        zones, face_warns = _zones_for_face(beam.groups, face, span_mm=span_mm)
        result.warnings.extend(face_warns)
        for z in zones:
            result.rows.append(SpacerRow(
                beam_id=beam.beam_id,
                face=face,
                diameter_mm=SPACER_DIA_MM,
                quantity=z.quantity,
                spacing_mm=SPACER_SPACING_MM,
                cut_length_mm=cut,
                zone_start_mm=z.start_mm,
                zone_end_mm=z.end_mm,
                zone_length_mm=z.length_mm,
                cover_mm=float(cover),
                beam_width_mm=width,
                extent_fallback=z.extent_fallback,
                cover_fallback=cover_fallback,
                raw_quantity=z.raw_quantity,
            ))

    return result


def compute_spacers(
    beams: Sequence[BeamSpacerInput],
) -> List[BeamSpacerResult]:
    return [compute_spacers_for_beam(b) for b in beams]


def face_for_role(role: str) -> Optional[str]:
    return _face_of_role(role)


def is_longitudinal_role(role: str) -> bool:
    return (role or "").upper() in _LONGITUDINAL_ROLES


def aggregate_equivalent_spacer_rows(rows: Sequence[SpacerRow]) -> List[SpacerRow]:
    """
    Combine LEFT/RIGHT (or other) zones that share spacer specification:
    same beam, face, diameter, spacing, cut length.
    Preserves component_zones for audit.
    """
    grouped: Dict[Tuple, List[SpacerRow]] = {}
    order: List[Tuple] = []
    for row in rows:
        key = (
            row.beam_id,
            row.face,
            int(row.diameter_mm),
            int(row.spacing_mm),
            round(float(row.cut_length_mm), 3),
        )
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)

    out: List[SpacerRow] = []
    for key in order:
        members = grouped[key]
        if len(members) == 1:
            only = members[0]
            if not only.component_zones:
                only.component_zones = [
                    {
                        "zone_start_mm": only.zone_start_mm,
                        "zone_end_mm": only.zone_end_mm,
                        "zone_length_mm": only.zone_length_mm,
                        "quantity": only.quantity,
                        "raw_quantity": only.raw_quantity,
                        "extent_fallback": only.extent_fallback,
                    }
                ]
            out.append(only)
            continue
        qty = sum(int(m.quantity) for m in members)
        raw = sum(float(m.raw_quantity) for m in members)
        length = sum(float(m.zone_length_mm) for m in members)
        zones_meta = []
        for m in members:
            zones_meta.append({
                "zone_start_mm": m.zone_start_mm,
                "zone_end_mm": m.zone_end_mm,
                "zone_length_mm": m.zone_length_mm,
                "quantity": m.quantity,
                "raw_quantity": m.raw_quantity,
                "extent_fallback": m.extent_fallback,
            })
        first = members[0]
        out.append(SpacerRow(
            beam_id=first.beam_id,
            face=first.face,
            diameter_mm=first.diameter_mm,
            quantity=qty,
            spacing_mm=first.spacing_mm,
            cut_length_mm=first.cut_length_mm,
            zone_start_mm=min(m.zone_start_mm for m in members),
            zone_end_mm=max(m.zone_end_mm for m in members),
            zone_length_mm=length,
            cover_mm=first.cover_mm,
            beam_width_mm=first.beam_width_mm,
            source=first.source,
            rule_version=first.rule_version,
            extent_fallback=any(m.extent_fallback for m in members),
            cover_fallback=first.cover_fallback,
            raw_quantity=raw,
            component_zones=zones_meta,
        ))
    return out
