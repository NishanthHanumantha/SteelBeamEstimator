"""
Phase R.1.1B — Production Integration of Engineering Interpretation
MODEL_VERSION: 8.2.1

Ensures that the complete engineering interpretation pipeline is the ONLY
production data source consumed by Steel/BBS/Workbook estimation.

Single source of truth:
  R.1.1A (annotation discovery) → R.1.3 (EngineeringBarModel) → V.B.1 (Steel/BBS/Excel)
"""

MODEL_VERSION = "8.2.1"
PHASE_ID = "R.1.1B"
PHASE_TITLE = "Production Integration of Engineering Interpretation"

__all__ = ["MODEL_VERSION", "PHASE_ID", "PHASE_TITLE"]
