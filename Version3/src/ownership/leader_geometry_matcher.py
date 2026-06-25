"""Phase D.3.3 — leader endpoint detection from DXF geometry."""

from typing import Dict, Optional, Tuple

from loguru import logger

from src.geometry.beam_geometry_classifier import BeamGeometryClassifier


class LeaderGeometryMatcher:
    """Resolve leader endpoints for annotation ownership scoring."""

    def __init__(self, dxf_path: str | None = None) -> None:
        self._classifier: BeamGeometryClassifier | None = None
        self._cache: Dict[Tuple[float, float], Optional[Tuple[float, float]]] = {}
        if dxf_path:
            try:
                self._classifier = BeamGeometryClassifier(dxf_path)
            except Exception as exc:
                logger.warning("Leader matcher: DXF unavailable — {}", exc)

    def resolve(
        self, x: float, y: float
    ) -> Tuple[float, float, bool, Optional[Tuple[float, float]]]:
        """
        Return evaluation point, has_leader flag, and leader endpoint if found.

        Priority: leader endpoint > insertion point.
        """
        leader = self._find_leader(x, y)
        if leader is not None:
            return leader[0], leader[1], True, leader
        return x, y, False, None

    def _find_leader(self, x: float, y: float) -> Optional[Tuple[float, float]]:
        key = (round(x, 1), round(y, 1))
        if key in self._cache:
            return self._cache[key]
        if self._classifier is None:
            self._cache[key] = None
            return None
        target = self._classifier.find_leader_target(x, y)
        self._cache[key] = target
        return target
