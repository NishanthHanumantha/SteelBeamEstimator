"""Deterministic confidence validation and normalization."""

from __future__ import annotations

from reasoning_exceptions import ReasoningValidationError

CONFIDENCE_BANDS = {
    "Very High": (0.90, 1.00),
    "High": (0.75, 0.89),
    "Medium": (0.50, 0.74),
    "Low": (0.25, 0.49),
    "Very Low": (0.00, 0.24),
}


class ConfidenceEngine:
    """Validate and normalize confidence values without inventing confidence."""

    @staticmethod
    def normalize(value: object) -> float:
        if isinstance(value, str):
            label = value.strip().title()
            if label not in CONFIDENCE_BANDS:
                raise ReasoningValidationError(f"Unsupported confidence label: {value}")
            low, high = CONFIDENCE_BANDS[label]
            return round((low + high) / 2, 4)

        try:
            numeric = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ReasoningValidationError(f"Invalid confidence value: {value}") from exc

        if numeric < 0.0 or numeric > 1.0:
            raise ReasoningValidationError(f"Confidence out of range: {numeric}")
        return round(numeric, 4)

    @staticmethod
    def classify(confidence: float) -> str:
        normalized = ConfidenceEngine.normalize(confidence)
        for label, (low, high) in CONFIDENCE_BANDS.items():
            if low <= normalized <= high:
                return label
        raise ReasoningValidationError(f"Unable to classify confidence: {normalized}")

    @staticmethod
    def validate(confidence: object) -> float:
        return ConfidenceEngine.normalize(confidence)
