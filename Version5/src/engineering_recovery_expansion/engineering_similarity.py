"""Deterministic engineering similarity scoring."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.engineering_recovery.recovery_decision_engine import VALID_RECOVERY_ROLES


WEIGHTS: Dict[str, int] = {
    "beam_id": 15,
    "bar_role": 15,
    "diameter": 15,
    "quantity": 10,
    "station": 5,
    "support": 5,
    "coordinates": 5,
    "leader": 5,
    "text": 10,
    "geometry": 5,
    "region": 5,
    "specification": 5,
    "context": 5,
}


class EngineeringSimilarity:
    """Compute deterministic engineering similarity scores (0-100)."""

    def score(
        self,
        inventory: dict[str, Any],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        contexts_by_beam = snapshot.get("contexts_by_beam") or {}
        existing_bars = snapshot.get("existing_bars") or []
        beam_id = str(inventory.get("beam_association") or "")
        role = str(inventory.get("role") or "")
        reference_bar = self._best_reference_bar(inventory, existing_bars)

        components: Dict[str, float] = {}
        components["beam_id"] = WEIGHTS["beam_id"] if beam_id and beam_id in contexts_by_beam else 0.0
        components["bar_role"] = WEIGHTS["bar_role"] if role in VALID_RECOVERY_ROLES else 0.0
        components["diameter"] = (
            WEIGHTS["diameter"]
            if inventory.get("diameter_mm") is not None
            else 0.0
        )
        components["quantity"] = WEIGHTS["quantity"] if inventory.get("quantity") is not None else 0.0
        components["station"] = self._station_score(inventory, contexts_by_beam.get(beam_id, {}))
        components["support"] = self._support_score(inventory, contexts_by_beam.get(beam_id, {}))
        components["coordinates"] = self._coordinate_score(inventory)
        components["leader"] = WEIGHTS["leader"] if inventory.get("leader") or inventory.get("text_source") else 0.0
        components["text"] = WEIGHTS["text"] if inventory.get("original_text") else 0.0
        components["geometry"] = WEIGHTS["geometry"] if inventory.get("geometry_id") else 0.0
        components["region"] = WEIGHTS["region"] if inventory.get("region") else 0.0
        components["specification"] = (
            WEIGHTS["specification"]
            if self._specification_complete(inventory)
            else 0.0
        )
        components["context"] = WEIGHTS["context"] if beam_id in contexts_by_beam else 0.0

        production_match = self._production_match_score(inventory, reference_bar)
        total = round(min(100.0, sum(components.values())), 2)

        return {
            "similarity_score": total,
            "components": components,
            "reference_bar_id": (reference_bar or {}).get("bar_id"),
            "production_match_score": production_match,
            "beam_id": beam_id,
            "role": role,
        }

    @staticmethod
    def _best_reference_bar(
        inventory: dict[str, Any],
        existing_bars: List[dict[str, Any]],
    ) -> dict[str, Any] | None:
        beam_id = str(inventory.get("beam_association") or "")
        role = str(inventory.get("role") or "")
        diameter = inventory.get("diameter_mm")
        best: Tuple[float, dict[str, Any] | None] = (0.0, None)
        for bar in existing_bars:
            if str(bar.get("beam_id") or "") != beam_id:
                continue
            score = 0.0
            if str(bar.get("role") or "") == role:
                score += 50.0
            if bar.get("diameter_mm") == diameter:
                score += 30.0
            if bar.get("quantity") == inventory.get("quantity"):
                score += 20.0
            if score > best[0]:
                best = (score, bar)
        return best[1]

    @staticmethod
    def _production_match_score(
        inventory: dict[str, Any],
        reference_bar: dict[str, Any] | None,
    ) -> float:
        if not reference_bar:
            return 0.0
        score = 0.0
        if str(reference_bar.get("beam_id") or "") == str(inventory.get("beam_association") or ""):
            score += 40.0
        if str(reference_bar.get("role") or "") == str(inventory.get("role") or ""):
            score += 30.0
        if reference_bar.get("diameter_mm") == inventory.get("diameter_mm"):
            score += 20.0
        if reference_bar.get("quantity") == inventory.get("quantity"):
            score += 10.0
        return score

    @staticmethod
    def _specification_complete(inventory: dict[str, Any]) -> bool:
        return all(
            [
                inventory.get("beam_association"),
                inventory.get("diameter_mm") is not None,
                inventory.get("quantity") is not None,
                inventory.get("role"),
            ]
        )

    @staticmethod
    def _coordinate_score(inventory: dict[str, Any]) -> float:
        coordinates = inventory.get("coordinates") or {}
        if coordinates.get("x") is None or coordinates.get("y") is None:
            return 0.0
        return float(WEIGHTS["coordinates"])

    @staticmethod
    def _station_score(inventory: dict[str, Any], template: dict[str, Any]) -> float:
        coordinates = inventory.get("coordinates") or {}
        span = float(template.get("effective_span_mm") or template.get("clear_span_mm") or 0.0)
        if coordinates.get("x") is None or not span:
            return 0.0
        return float(WEIGHTS["station"])

    @staticmethod
    def _support_score(inventory: dict[str, Any], template: dict[str, Any]) -> float:
        coordinates = inventory.get("coordinates") or {}
        span = template.get("effective_span_mm") or template.get("clear_span_mm")
        if coordinates.get("x") is None or not span:
            return 3.0 if inventory.get("region") else 0.0
        return float(WEIGHTS["support"])
