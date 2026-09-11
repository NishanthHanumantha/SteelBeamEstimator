"""
PhaseL.2.2 — Geometry Registry Generation (web-capable, D.5.3)
MODEL_VERSION: 8.9.2

Builds R.3-compatible geometry_registry.json from the current run's
VROOT1 beam_registry (and optional dynamic_beam_geometry).

Preserves the Version7 geometry_registry entry schema and axis/support
construction rules. Does NOT depend on L.2 / L.2.1 / Version5 / Benchmark.

Pipeline position:
  R.2.1D → L.2.2 (this phase) → R.3 (later — D.5.4)
"""

MODEL_VERSION = "8.9.2"
PHASE_ID = "L.2.2"
