"""Engineering trace registry — Phase QA.2."""

from __future__ import annotations

from typing import Any, Dict, List

from src.estimator_validation.object_trace.trace_types import (
    ENGINEERING_TRACE_NAMESPACE,
    ENGINEERING_TRACE_REGISTRY,
    ObjectTrace,
)


class TraceRegistry:
    """Indexed registry of engineering object traces."""

    namespace = ENGINEERING_TRACE_NAMESPACE
    registry_name = ENGINEERING_TRACE_REGISTRY

    def build(self, traces: List[ObjectTrace]) -> dict[str, Any]:
        by_beam: Dict[str, List[dict[str, Any]]] = {}
        by_role: Dict[str, List[dict[str, Any]]] = {}
        by_diameter: Dict[str, List[dict[str, Any]]] = {}
        by_fabrication_mark: Dict[str, List[dict[str, Any]]] = {}
        by_shape_code: Dict[str, List[dict[str, Any]]] = {}
        by_identity: List[str] = []
        by_trace_status: Dict[str, int] = {}
        by_first_missing_layer: Dict[str, int] = {}
        by_confidence: Dict[str, int] = {}

        entries: List[dict[str, Any]] = []
        for trace in traces:
            payload = trace.to_dict()
            entries.append(payload)
            identity = trace.identity
            by_beam.setdefault(identity.beam_mark, []).append(payload)
            by_role.setdefault(identity.role, []).append(payload)
            diameter_key = str(identity.diameter_mm) if identity.diameter_mm is not None else "UNKNOWN"
            by_diameter.setdefault(diameter_key, []).append(payload)
            fab = identity.fabrication_mark or "UNKNOWN"
            by_fabrication_mark.setdefault(fab, []).append(payload)
            shape = identity.shape_code or "UNKNOWN"
            by_shape_code.setdefault(shape, []).append(payload)
            by_identity.append(identity.identity_key())
            by_trace_status[trace.trace_status] = by_trace_status.get(trace.trace_status, 0) + 1
            layer = trace.first_missing_layer or "NONE"
            by_first_missing_layer[layer] = by_first_missing_layer.get(layer, 0) + 1
            bucket = self._confidence_bucket(trace.confidence)
            by_confidence[bucket] = by_confidence.get(bucket, 0) + 1

        return {
            "namespace": self.namespace,
            "registry": self.registry_name,
            "entry_count": len(entries),
            "indexes": {
                "beam": {key: len(value) for key, value in sorted(by_beam.items())},
                "role": {key: len(value) for key, value in sorted(by_role.items())},
                "diameter": {key: len(value) for key, value in sorted(by_diameter.items())},
                "fabrication_mark": {key: len(value) for key, value in sorted(by_fabrication_mark.items())},
                "shape_code": {key: len(value) for key, value in sorted(by_shape_code.items())},
                "identity": by_identity,
                "trace_status": by_trace_status,
                "first_missing_layer": by_first_missing_layer,
                "confidence": by_confidence,
            },
            "entries": entries,
            "by_beam": by_beam,
            "by_role": by_role,
            "by_diameter": by_diameter,
        }

    @staticmethod
    def _confidence_bucket(confidence: int) -> str:
        if confidence >= 100:
            return "100"
        if confidence >= 95:
            return "95"
        if confidence >= 90:
            return "90"
        if confidence >= 80:
            return "80"
        return "UNMATCHED"
