"""
normalized_position_builder.py — Compute normalized position (0.0 → 1.0).
MODEL_VERSION: 8.0.0

Normalized position maps the annotation's local_x to [0.0, 1.0]:
  0.0 = left end of beam
  0.5 = midspan
  1.0 = right end of beam

Clamped to [0.0, 1.0] to handle annotation text placed slightly outside
the drawn beam extent due to leader lines or dimension offsets.
"""
from __future__ import annotations

from .geometry_models import ProjectionResult


_CLAMP_WARN_THRESHOLD = 0.05  # outside by more than 5% of span → note


class NormalizedPositionBuilder:
    """Compute and clamp normalized position from ProjectionResult."""

    def compute(
        self,
        projection: ProjectionResult,
        beam_length_mm: float,
    ) -> tuple:
        """
        Returns (normalized_position: float, notes: list[str]).
        normalized_position is clamped to [0.0, 1.0].
        """
        notes = []
        if beam_length_mm <= 0:
            return 0.5, ["Beam length zero — normalized position set to 0.5"]

        raw = projection.local_x / beam_length_mm
        clamped = max(0.0, min(1.0, raw))

        overshoot = abs(raw - clamped)
        if overshoot > _CLAMP_WARN_THRESHOLD:
            notes.append(
                f"Annotation local_x={projection.local_x:.1f}mm gives "
                f"raw normalized={raw:.3f}; clamped to {clamped:.3f} "
                f"(overshoot={overshoot:.3f} — annotation outside beam extent)"
            )
        else:
            notes.append(
                f"Normalized position: {clamped:.4f} "
                f"(local_x={projection.local_x:.1f}mm / span={beam_length_mm:.1f}mm)"
            )

        return round(clamped, 6), notes
