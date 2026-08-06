"""
Phase T1.7 — Annotation Graph Resolver.
MODEL_VERSION: 9.4.0

Additive engineering relationship layer between beam geometry, physical bars,
leaders, annotations, and semantic interpretation. Does not modify R.3 / R.3.1 /
T1.5 / T1.6 logic.
"""
MODEL_VERSION = "9.4.0"
PHASE_ID = "T1.7"

from .graph_models import AnnotationGraph  # noqa: E402
from .phase_t17_orchestrator import PhaseT17Orchestrator  # noqa: E402

__all__ = [
    "MODEL_VERSION",
    "PHASE_ID",
    "AnnotationGraph",
    "PhaseT17Orchestrator",
]
