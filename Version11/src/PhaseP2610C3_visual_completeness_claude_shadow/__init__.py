"""V11 package init: do not import experimental orchestrators at import time.

Production code imports named submodules. Loading research orchestrators from
__init__ would pull excluded benchmark packages.
"""
from .config import GATE_VERSION, MODEL_VERSION, PHASE_ID, PHASE_NAME

__all__ = ["GATE_VERSION", "MODEL_VERSION", "PHASE_ID", "PHASE_NAME"]
