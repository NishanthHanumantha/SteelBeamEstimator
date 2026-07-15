"""
Phase V.TRACE.2 — Runtime Input Verification
MODEL_VERSION : 7.1.3
Type          : Read-Only Runtime Diagnostics

Determines EXACTLY what Phase L.2 loads at runtime by:
  1. Inspecting every file the InterpretationCollector opens
  2. Calling InterpretationCollector.collect() and BeamContextBuilder._discover_beams()
     with the live adapter files (read-only, no output written)
  3. Comparing input timestamps vs L.2 output timestamps
  4. Identifying stale outputs with hard evidence

NO engineering logic is modified.
NO pipeline outputs are regenerated.
"""

MODEL_VERSION = "7.1.3"
PHASE_ID      = "V.TRACE.2"
PHASE_TITLE   = "Runtime Input Verification"

__all__ = ["MODEL_VERSION", "PHASE_ID", "PHASE_TITLE"]
