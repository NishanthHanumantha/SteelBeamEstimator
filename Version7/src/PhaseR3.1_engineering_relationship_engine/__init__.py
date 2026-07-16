"""
PhaseR3.1 — Engineering Drawing Relationship Engine
MODEL_VERSION: 8.1.0

Bridges the remaining gap between Geometry Context (R.3) and
Engineering Intent Resolution (R.4).

Phase R.3.1 establishes deterministic drawing relationships:
  Annotation → Leader → Arrow → Physical Bar → Supports → Extent

It does NOT resolve engineering intent.
Intent remains UNKNOWN throughout this phase.

DXF relationship chain (verified from drawing analysis):
  MTEXT annotation (insert point)
    ↕ ~63mm distance
  LEADER tail (last vertex) — shoulder of leader
    ↓  (leader polyline path)
  LEADER tip (first vertex) — arrowhead
    ↓  (distance ≈ 0)
  Physical bar LINE on -STR-REINF layer (horizontal)
    ↓  (spatial extent)
  Bar start_x → bar end_x → beam axis comparison
    ↓
  Support crossing analysis + extent evidence

Pipeline position:
  R.3 Geometry Context Engine
  ↓
  R.3.1 Engineering Drawing Relationship Engine  ← this phase
  ↓
  R.4 Engineering Intent Resolver (future)
"""

MODEL_VERSION = "8.1.0"
PHASE_ID      = "R.3.1"

# DXF layer constants (drawing-convention, not beam-specific)
LAYER_LEADERS    = "-S-ARROW"
LAYER_REINF      = "-STR-REINF"
LAYER_REINF2     = "rein"
LAYER_TEXT       = "-STR-TEXT"
LAYER_BEAM       = "-STR-BEAM"

# Geometry thresholds
LEADER_TAIL_TO_ANN_MAX_MM   = 300.0   # max distance: leader tail → annotation
LEADER_TIP_TO_BAR_MAX_MM    = 50.0    # max distance: leader tip → physical bar
HORIZONTAL_LINE_MAX_SLOPE   = 0.05    # |dy/dx| ≤ this → treat as horizontal bar
MIN_BAR_LENGTH_MM            = 100.0  # ignore very short segments
