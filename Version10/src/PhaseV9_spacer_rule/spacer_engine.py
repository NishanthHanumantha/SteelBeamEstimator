"""
spacer_engine.py — Pure deterministic spacer-bar rule (no I/O).
MODEL_VERSION: 9.1.0

Estimation-team ruling (hardcoded, exceptional):
  SPACER_DIA_MM = 25, SPACER_SPACING_MM = 1000
  Trigger: ≥2 longitudinal groups on the SAME face (MAIN+EXTRA).
  Cover is the ONLY context input (from R.2A).
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .spacer_models import (
    BeamSpacerInput,
    BeamSpacerResult,
    Extent,
    LongitudinalGroup,
    SpacerRow,
    SpacerZone,
)

MODEL_VERSION = "9.1.0"
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


def spacer_quantity(zone_length_mm: float) -> int:
    """N = ceil(zone_length_mm / SPACER_SPACING_MM) + 1."""
    if zone_length_mm <= 0:
        return 0
    return int(math.ceil(zone_length_mm / float(SPACER_SPACING_MM))) + 1


def cut_length_mm(beam_width_mm: float, cover_mm: float) -> float:
    return float(beam_width_mm) - 2.0 * float(cover_mm)


def compute_overlap_zones(
    extents: Sequence[Extent],
    epsilon_mm: float = EXTENT_EPSILON_MM,
) -> List[Tuple[float, float]]:
    """
    Maximal intervals where ≥2 groups coexist (sweep-line merge).
    Three stacked bars with intersecting extents → ONE zone over the
    union where ≥2 coexist — never double-emit.
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

    # At equal positions: process starts (+1) before ends (-1)
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


def _dedupe_zones(zones: List[SpacerZone], epsilon_mm: float = EXTENT_EPSILON_MM) -> List[SpacerZone]:
    """Collapse zones with identical (or epsilon-equal) intervals on the same face."""
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
                # Keep the non-fallback copy when possible; else keep larger qty
                if prev.extent_fallback and not z.extent_fallback:
                    out[-1] = z
                elif prev.quantity < z.quantity:
                    out[-1] = z
                continue
            # Fallback zones with same length but both start at 0 → same physical zone
            if (
                prev.face == z.face
                and prev.extent_fallback
                and z.extent_fallback
                and abs(prev.length_mm - z.length_mm) <= epsilon_mm
            ):
                if prev.quantity < z.quantity:
                    out[-1] = z
                continue
        out.append(z)
    return out


def _zones_for_face(
    groups: List[LongitudinalGroup],
    face: str,
) -> Tuple[List[SpacerZone], List[str]]:
    """Compute spacer zones for one face. Returns (zones, warnings)."""
    warnings: List[str] = []
    face_groups = [g for g in groups if g.face == face and g.role in _LONGITUDINAL_ROLES]
    if len(face_groups) < 2:
        return [], warnings

    mains = [g for g in face_groups if "MAIN" in g.role.upper()]
    extras = [g for g in face_groups if "EXTRA" in g.role.upper()]
    if not mains or not extras:
        # Spec: need MAIN+EXTRA (or ≥2 longitudinal layers). Two MAINs alone → no spacers.
        # Two EXTRAs alone without MAIN also → no spacers (a face with only extras is rare).
        if len(mains) + len(extras) < 2:
            return [], warnings
        if not extras:
            return [], warnings

    with_extent = [g for g in face_groups if g.has_extent()]
    without_extent = [g for g in face_groups if not g.has_extent()]
    zones: List[SpacerZone] = []

    # Prefer geometric overlap when ≥2 extents are known
    if len(with_extent) >= 2:
        # Unique extents only (Y16+Y12 extras sharing the same span → one interval)
        seen_ext: List[Extent] = []
        for g in with_extent:
            ext = g.extent()
            if ext is None:
                continue
            if any(
                abs(ext[0] - s) <= EXTENT_EPSILON_MM and abs(ext[1] - e) <= EXTENT_EPSILON_MM
                for s, e in seen_ext
            ):
                continue
            seen_ext.append(ext)
        for start, end in compute_overlap_zones(seen_ext):
            length = end - start
            qty = spacer_quantity(length)
            if qty > 0:
                zones.append(SpacerZone(
                    face=face, start_mm=start, end_mm=end,
                    length_mm=length, quantity=qty, extent_fallback=False,
                ))
        # EXTRAs without extent: one fallback zone per distinct clear_length
        seen_cl: List[float] = []
        for g in without_extent:
            if "EXTRA" not in g.role.upper():
                continue
            cl = float(g.clear_length_mm or 0.0)
            if cl <= 0:
                warnings.append(
                    f"{face}: EXTRA {g.role} missing extent and clear_length; skipped"
                )
                continue
            if any(abs(cl - prev) <= EXTENT_EPSILON_MM for prev in seen_cl):
                continue
            seen_cl.append(cl)
            qty = spacer_quantity(cl)
            if qty > 0:
                zones.append(SpacerZone(
                    face=face, start_mm=0.0, end_mm=cl,
                    length_mm=cl, quantity=qty, extent_fallback=True,
                ))
                warnings.append(
                    f"{face}: extent_fallback for {g.role} using clear_length={cl}"
                )
        return _dedupe_zones(zones), warnings

    # One known extent + groups without — usually MAIN full-span + EXTRA clear length
    if len(with_extent) == 1 and without_extent:
        seen_cl: List[float] = []
        for g in without_extent:
            if "EXTRA" not in g.role.upper():
                continue
            cl = float(g.clear_length_mm or 0.0)
            if cl <= 0:
                warnings.append(
                    f"{face}: group {g.role} missing clear_length; skipped"
                )
                continue
            if any(abs(cl - prev) <= EXTENT_EPSILON_MM for prev in seen_cl):
                continue
            seen_cl.append(cl)
            qty = spacer_quantity(cl)
            if qty > 0:
                zones.append(SpacerZone(
                    face=face, start_mm=0.0, end_mm=cl,
                    length_mm=cl, quantity=qty, extent_fallback=True,
                ))
                warnings.append(
                    f"{face}: extent_fallback for {g.role} using clear_length={cl}"
                )
        return _dedupe_zones(zones), warnings

    # No geometric extents — one fallback zone per distinct EXTRA clear_length
    if not extras:
        return [], warnings
    seen_cl: List[float] = []
    for g in extras:
        cl = float(g.clear_length_mm or 0.0)
        if cl <= 0:
            warnings.append(f"{face}: EXTRA missing clear_length; skipped")
            continue
        if any(abs(cl - prev) <= EXTENT_EPSILON_MM for prev in seen_cl):
            continue
        seen_cl.append(cl)
        qty = spacer_quantity(cl)
        if qty > 0:
            zones.append(SpacerZone(
                face=face, start_mm=0.0, end_mm=cl,
                length_mm=cl, quantity=qty, extent_fallback=True,
            ))
            warnings.append(
                f"{face}: extent_fallback for {g.role} using clear_length={cl}"
            )
    return _dedupe_zones(zones), warnings


def compute_spacers_for_beam(beam: BeamSpacerInput) -> BeamSpacerResult:
    """
    Pure engine: compute SPACER_BAR rows for one beam.
    Never modifies existing groups. Additive only.
    """
    result = BeamSpacerResult(beam_id=beam.beam_id)

    # R4 — idempotent re-run guard
    if beam.already_has_spacer:
        result.skipped = True
        result.skip_reason = "already_has_spacer"
        result.warnings.append(
            f"{beam.beam_id}: SPACER_BAR already present — skip emission (dedup)"
        )
        return result

    # R3 — beam width required
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

    for face in ("TOP", "BOTTOM"):
        zones, face_warns = _zones_for_face(beam.groups, face)
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
