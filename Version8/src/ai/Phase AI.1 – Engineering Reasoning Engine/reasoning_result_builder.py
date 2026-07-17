"""Build typed engineering reasoning results from validated JSON."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from confidence_engine import ConfidenceEngine
from reasoning_models import (
    AnnotationReasoningResult,
    BeamReasoningResult,
    EngineeringReasoningResult,
    QAReasoningResult,
    ReinforcementReasoningResult,
    RESULT_MODEL_MAP,
)
from src.llm.json_engine.response_models import StructuredResponse


class ReasoningResultBuilder:
    """Convert validated JSON responses into typed reasoning models."""

    def build(
        self,
        task_type: str,
        structured: StructuredResponse,
        *,
        context_checksum: str,
        template_version: str,
    ) -> EngineeringReasoningResult:
        key = task_type.upper()
        confidence = ConfidenceEngine.validate(structured.confidence)
        payload = dict(structured.validated_data)

        if key == "BEAM_REASONING":
            result = self._build_beam(payload, key, confidence, context_checksum, template_version, structured)
        elif key == "ANNOTATION_CLASSIFICATION":
            result = self._build_annotation(payload, key, confidence, context_checksum, template_version, structured)
        elif key == "REINFORCEMENT_INTERPRETATION":
            result = self._build_reinforcement(payload, key, confidence, context_checksum, template_version, structured)
        elif key == "QA_REASONING":
            result = self._build_qa(payload, key, confidence, context_checksum, template_version, structured)
        elif key == "GENERAL_ENGINEERING_REASONING":
            result = self._build_general(payload, key, confidence, context_checksum, template_version, structured)
        else:
            model_cls = RESULT_MODEL_MAP.get(key, EngineeringReasoningResult)
            result = self._build_generic(model_cls, payload, key, confidence, context_checksum, template_version, structured)

        return result

    def _build_beam(
        self,
        payload: Dict[str, Any],
        task_type: str,
        confidence: float,
        context_checksum: str,
        template_version: str,
        structured: StructuredResponse,
    ) -> BeamReasoningResult:
        summary = str(payload.get("reasoning", "")).strip()
        observations = self._as_string_list(payload.get("evidence"))
        return BeamReasoningResult(
            reasoning_id=self._reasoning_id(task_type, context_checksum, template_version),
            task_type=task_type,
            confidence=confidence,
            summary=summary,
            observations=observations,
            recommendations=[],
            assumptions=[],
            warnings=[],
            metadata=self._metadata(structured, template_version, context_checksum),
            checksum=self._checksum(payload),
            generated_timestamp=EngineeringReasoningResult.timestamp(),
            beam_id=str(payload.get("beam_id", "")),
            beam_name=str(payload.get("beam_name", "")),
        )

    def _build_annotation(
        self,
        payload: Dict[str, Any],
        task_type: str,
        confidence: float,
        context_checksum: str,
        template_version: str,
        structured: StructuredResponse,
    ) -> AnnotationReasoningResult:
        summary = str(payload.get("interpretation", "")).strip()
        return AnnotationReasoningResult(
            reasoning_id=self._reasoning_id(task_type, context_checksum, template_version),
            task_type=task_type,
            confidence=confidence,
            summary=summary,
            observations=[],
            recommendations=[],
            assumptions=[],
            warnings=[],
            metadata=self._metadata(structured, template_version, context_checksum),
            checksum=self._checksum(payload),
            generated_timestamp=EngineeringReasoningResult.timestamp(),
            annotation_id=str(payload.get("annotation_id", "")),
            region_id=str(payload.get("region_id", "")),
        )

    def _build_reinforcement(
        self,
        payload: Dict[str, Any],
        task_type: str,
        confidence: float,
        context_checksum: str,
        template_version: str,
        structured: StructuredResponse,
    ) -> ReinforcementReasoningResult:
        parsed = payload.get("parsed_result") or {}
        summary = json.dumps(parsed, sort_keys=True, separators=(",", ":")) if parsed else str(payload.get("annotation_text", ""))
        return ReinforcementReasoningResult(
            reasoning_id=self._reasoning_id(task_type, context_checksum, template_version),
            task_type=task_type,
            confidence=confidence,
            summary=summary,
            observations=[],
            recommendations=[],
            assumptions=[],
            warnings=[],
            metadata=self._metadata(structured, template_version, context_checksum),
            checksum=self._checksum(payload),
            generated_timestamp=EngineeringReasoningResult.timestamp(),
            beam_id=str(payload.get("beam_id", "")),
            annotation_text=str(payload.get("annotation_text", "")),
        )

    def _build_qa(
        self,
        payload: Dict[str, Any],
        task_type: str,
        confidence: float,
        context_checksum: str,
        template_version: str,
        structured: StructuredResponse,
    ) -> QAReasoningResult:
        status = str(payload.get("validation_status", ""))
        issues = self._as_string_list(payload.get("issues"))
        return QAReasoningResult(
            reasoning_id=self._reasoning_id(task_type, context_checksum, template_version),
            task_type=task_type,
            confidence=confidence,
            summary=status,
            observations=issues,
            recommendations=[],
            assumptions=[],
            warnings=issues,
            metadata=self._metadata(structured, template_version, context_checksum),
            checksum=self._checksum(payload),
            generated_timestamp=EngineeringReasoningResult.timestamp(),
            artifact_name=str(payload.get("artifact_name", "")),
            validation_status=status,
        )

    def _build_general(
        self,
        payload: Dict[str, Any],
        task_type: str,
        confidence: float,
        context_checksum: str,
        template_version: str,
        structured: StructuredResponse,
    ) -> EngineeringReasoningResult:
        summary = str(payload.get("message", "")).strip()
        warnings: List[str] = []
        if payload.get("status") == "error":
            warnings.append("status:error")
        return EngineeringReasoningResult(
            reasoning_id=self._reasoning_id(task_type, context_checksum, template_version),
            task_type=task_type,
            confidence=confidence,
            summary=summary,
            observations=[],
            recommendations=[],
            assumptions=[],
            warnings=warnings,
            metadata=self._metadata(structured, template_version, context_checksum),
            checksum=self._checksum(payload),
            generated_timestamp=EngineeringReasoningResult.timestamp(),
        )

    def _build_generic(
        self,
        model_cls: type[EngineeringReasoningResult],
        payload: Dict[str, Any],
        task_type: str,
        confidence: float,
        context_checksum: str,
        template_version: str,
        structured: StructuredResponse,
    ) -> EngineeringReasoningResult:
        summary = str(payload.get("summary") or payload.get("reasoning") or payload.get("message", "")).strip()
        return model_cls(
            reasoning_id=self._reasoning_id(task_type, context_checksum, template_version),
            task_type=task_type,
            confidence=confidence,
            summary=summary,
            observations=self._as_string_list(payload.get("observations")),
            recommendations=self._as_string_list(payload.get("recommendations")),
            assumptions=self._as_string_list(payload.get("assumptions")),
            warnings=self._as_string_list(payload.get("warnings")),
            metadata=self._metadata(structured, template_version, context_checksum),
            checksum=self._checksum(payload),
            generated_timestamp=EngineeringReasoningResult.timestamp(),
        )

    @staticmethod
    def _as_string_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    @staticmethod
    def _metadata(
        structured: StructuredResponse,
        template_version: str,
        context_checksum: str,
    ) -> Dict[str, Any]:
        return {
            "schema_name": structured.schema_name,
            "schema_version": structured.schema_version,
            "template_version": template_version,
            "context_checksum": context_checksum,
            "confidence_band": ConfidenceEngine.classify(structured.confidence),
        }

    @staticmethod
    def _checksum(payload: Dict[str, Any]) -> str:
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _reasoning_id(task_type: str, context_checksum: str, template_version: str) -> str:
        digest = hashlib.sha256(
            f"{task_type}:{context_checksum}:{template_version}".encode("utf-8")
        ).hexdigest()
        return digest[:16]
