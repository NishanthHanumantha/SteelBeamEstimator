"""Engineering Calculation Integration Repair — production registry integration for recovered bars."""

from src.engineering_calculation_integration.integration_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
)
from src.engineering_calculation_integration.integration_engine import IntegrationEngine

__all__ = [
    "ENGINE_VERSION",
    "MODEL_VERSION",
    "PHASE",
    "IntegrationEngine",
]
