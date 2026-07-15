"""
PhaseR.2A — General Notes Runtime Parsing & Engineering Context Injection
MODEL_VERSION: 7.5.0

Parses the General Notes DXF dynamically and builds an immutable
EngineeringContext that becomes the single source of truth for every
project-specific engineering parameter used by the pipeline.

No engineering calculations are modified in this phase.
"""

MODEL_VERSION = "7.5.3"
PHASE_TAG = "R.2A"
PHASE_NAME = "General Notes Runtime Parsing & Engineering Context Injection"
