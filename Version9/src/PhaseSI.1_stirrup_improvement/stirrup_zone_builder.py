"""
Engineering Zone Builder — Phase SI.1 MODULE 2

Builds engineering shear zones from beam geometry and spacing pattern.

Zone allocation rules (IS 456 / estimator convention):
  UNIFORM (1 spacing):
    One zone covering the full span.

  VARIABLE (N spacings):
    N equal zones, each of length = span / N.
    Zone 0           → LEFT_SUPPORT
    Zones 1..N-2     → MIDSPAN
    Zone N-1         → RIGHT_SUPPORT

  This equal-thirds (or equal-N) allocation matches the estimator's
  behaviour confirmed for the reference workbook:
    B2: @100/200/100, span=4280mm → zone=1426.7mm → support merged=29, middle=7 ✓
"""
from typing import List

from stirrup_models import ParsedStirrupNotation, StirrupZone, StirrupType, ZoneRole


class StirrupZoneBuilder:
    """Creates StirrupZone objects from parsed notation and beam geometry."""

    def build(
        self,
        parsed: ParsedStirrupNotation,
        span_mm: float,
        beam_id: str = "",
    ) -> List[StirrupZone]:
        """
        Returns a list of StirrupZone objects.
        Returns [] if parsed.is_parseable is False or spacings are empty.

        T1.4: when residual geometry gives confident pitch-change boundaries,
        use those instead of equal-N fallback.
        """
        if not parsed.is_parseable or not parsed.spacings_mm or span_mm <= 0:
            return []

        n = len(parsed.spacings_mm)

        if n == 1 or parsed.stirrup_type == StirrupType.UNIFORM:
            return [
                StirrupZone(
                    zone_id=f"ZONE_FULL",
                    zone_index=0,
                    role=ZoneRole.MIDSPAN,
                    start_mm=0.0,
                    end_mm=span_mm,
                    length_mm=span_mm,
                    spacing_mm=parsed.spacings_mm[0],
                )
            ]

        # T1.4 pitch-change boundaries (residual only; soft-fallback to equal-N)
        bounds = None
        if beam_id:
            try:
                import importlib.util
                import os
                from pathlib import Path
                eng = (os.environ.get("STEEL_ENGINE_ROOT") or "").strip()
                if eng:
                    tpath = (
                        Path(eng) / "src" / "PhaseT1_geometric_stirrup_evidence"
                        / "type3_label_repair.py"
                    )
                    if tpath.exists():
                        spec = importlib.util.spec_from_file_location(
                            "t1_type3_zb", tpath
                        )
                        mod = importlib.util.module_from_spec(spec)
                        assert spec and spec.loader
                        spec.loader.exec_module(mod)
                        bounds = mod.load_t14_boundaries(beam_id, n)
            except Exception:
                bounds = None

        zones: List[StirrupZone] = []
        for i, spacing in enumerate(parsed.spacings_mm):
            if bounds is not None:
                start, end = bounds[i]
            else:
                zone_length = span_mm / n
                start = i * zone_length
                end = (i + 1) * zone_length

            if i == 0:
                role = ZoneRole.LEFT_SUPPORT
            elif i == n - 1:
                role = ZoneRole.RIGHT_SUPPORT
            else:
                role = ZoneRole.MIDSPAN

            length = max(0.0, end - start)
            zones.append(StirrupZone(
                zone_id=f"ZONE_{i}",
                zone_index=i,
                role=role,
                start_mm=round(start, 1),
                end_mm=round(end, 1),
                length_mm=round(length, 1),
                spacing_mm=spacing,
            ))

        return zones
