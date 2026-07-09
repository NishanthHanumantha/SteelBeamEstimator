"""Orchestrate engineering reasoning execution and output persistence."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from reasoning_cache import ReasoningCache
from reasoning_context_mapper import ReasoningContextMapper
from reasoning_exceptions import ReasoningOutputError, UnsupportedReasoningTaskError
from reasoning_logger import ReasoningLogEntry, ReasoningLogger
from reasoning_metrics import ReasoningMetricsCollector, ReasoningMetricsEntry
from reasoning_models import MODEL_VERSION, OUTPUT_DIR, EngineeringReasoningResult
from reasoning_registry import TaskRegistry
from reasoning_result_builder import ReasoningResultBuilder
from reasoning_validator import ReasoningValidator
from src.llm.claude_config import ClaudeConfig
from src.llm.context.engineering_context_builder import EngineeringContextBuilder
from src.llm.json_engine.response_retry import ResponseRetryEngine
from src.llm.prompt_executor import PromptExecutor


class TrackingRetryEngine(ResponseRetryEngine):
    """Track JSON retry attempts without modifying the shared retry engine."""

    def __init__(self) -> None:
        super().__init__()
        self.last_retry_count = 0

    def execute(self, fetch_response, schema_name):  # type: ignore[no-untyped-def]
        corrections = {"count": 0}

        def wrapped(correction: str | None) -> str:
            if correction:
                corrections["count"] += 1
            return fetch_response(correction)

        result = super().execute(wrapped, schema_name)
        self.last_retry_count = corrections["count"]
        return result


class OutputWriter:
    """Persist deterministic reasoning outputs to the phase output folder."""

    def __init__(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def write_results(self, results: list[EngineeringReasoningResult]) -> None:
        payload = {
            "model_version": MODEL_VERSION,
            "results": sorted(
                [result.to_dict() for result in results],
                key=lambda item: str(item["reasoning_id"]),
            ),
        }
        self._write_json("reasoning_results.json", payload)

    def write_validation_report(self, report: Dict[str, Any]) -> None:
        self._write_json("validation_report.json", report)

    def write_cache_statistics(self, statistics: Dict[str, Any]) -> None:
        payload = {"model_version": MODEL_VERSION, **statistics}
        self._write_json("cache_statistics.json", payload)

    def _write_json(self, filename: str, payload: Dict[str, Any]) -> None:
        path = OUTPUT_DIR / filename
        try:
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise ReasoningOutputError(f"Failed to write {path}: {exc}") from exc


class ReasoningManager:
    """Select tasks, execute prompts, validate, cache, and persist reasoning."""

    def __init__(
        self,
        *,
        prompt_executor: PromptExecutor | None = None,
        context_builder: EngineeringContextBuilder | None = None,
        context_mapper: ReasoningContextMapper | None = None,
        result_builder: ReasoningResultBuilder | None = None,
        validator: ReasoningValidator | None = None,
        cache: ReasoningCache | None = None,
        metrics: ReasoningMetricsCollector | None = None,
        logger: ReasoningLogger | None = None,
        output_writer: OutputWriter | None = None,
    ) -> None:
        self._retry_engine = TrackingRetryEngine()
        self._prompt_executor = prompt_executor or PromptExecutor(retry_engine=self._retry_engine)
        self._context_builder = context_builder or EngineeringContextBuilder()
        self._context_mapper = context_mapper or ReasoningContextMapper(self._context_builder)
        self._result_builder = result_builder or ReasoningResultBuilder()
        self._validator = validator or ReasoningValidator()
        self._cache = cache or ReasoningCache()
        self._metrics = metrics or ReasoningMetricsCollector()
        self._logger = logger or ReasoningLogger()
        self._output_writer = output_writer or OutputWriter()
        self._results: list[EngineeringReasoningResult] = []

    def execute(
        self,
        task_type: str,
        engineering_objects: Dict[str, Any],
        variables: Dict[str, Any] | None = None,
        system_template: str = "ENGINEERING_SYSTEM",
    ) -> EngineeringReasoningResult:
        started = time.perf_counter()
        try:
            task = TaskRegistry.get(task_type)
        except KeyError as exc:
            raise UnsupportedReasoningTaskError(str(exc)) from exc

        context = self._context_builder.build_context(task.context_task_type, engineering_objects)
        cache_key = self._cache.build_key(task.task_type, context.checksum, task.template_version)
        cached = self._cache.get(cache_key)
        if cached is not None:
            if not any(item.reasoning_id == cached.reasoning_id for item in self._results):
                self._results.append(cached)
            duration_ms = (time.perf_counter() - started) * 1000
            self._record_execution(
                cached,
                task,
                duration_ms=duration_ms,
                cache_hit=True,
                retry_count=0,
                prompt_tokens=context.estimated_tokens,
                completion_tokens=self._estimate_tokens(cached.summary),
            )
            self._persist_outputs(validation_status="PASS")
            return cached

        mapped_variables = self._context_mapper.map(
            context,
            variables,
            task_type=task.task_type,
        )
        self._apply_template_defaults(mapped_variables, task.task_type)

        structured = self._prompt_executor.execute_engineering(
            task.prompt_template,
            task.schema_name,
            task.context_task_type,
            engineering_objects,
            mapped_variables,
            system_template=system_template,
        )

        result = self._result_builder.build(
            task.task_type,
            structured,
            context_checksum=context.checksum,
            template_version=task.template_version,
        )
        self._validator.validate(result)

        self._cache.set(cache_key, result)
        self._results.append(result)

        duration_ms = (time.perf_counter() - started) * 1000
        completion_tokens = self._estimate_tokens(json.dumps(structured.raw_json, sort_keys=True))
        prompt_tokens = context.estimated_tokens + self._estimate_tokens(json.dumps(mapped_variables, sort_keys=True))
        self._record_execution(
            result,
            task,
            duration_ms=duration_ms,
            cache_hit=False,
            retry_count=self._retry_engine.last_retry_count,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        self._persist_outputs(validation_status="PASS")
        return result

    def _record_execution(
        self,
        result: EngineeringReasoningResult,
        task: Any,
        *,
        duration_ms: float,
        cache_hit: bool,
        retry_count: int,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        self._metrics.record(
            ReasoningMetricsEntry(
                reasoning_id=result.reasoning_id,
                task_type=result.task_type,
                execution_time_ms=round(duration_ms, 3),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cache_hit=cache_hit,
                retry_count=retry_count,
                confidence=result.confidence,
                reasoning_length=len(result.summary),
                model_name=ClaudeConfig.MODEL_NAME,
                template_version=task.template_version,
            )
        )
        self._logger.log(
            ReasoningLogEntry(
                reasoning_id=result.reasoning_id,
                task_type=result.task_type,
                duration_ms=round(duration_ms, 3),
                confidence=result.confidence,
                cache_hit=cache_hit,
                retry_count=retry_count,
                model_name=ClaudeConfig.MODEL_NAME,
                template_version=task.template_version,
                validation_status="PASS",
            )
        )

    def _persist_outputs(self, *, validation_status: str) -> None:
        self._output_writer.write_results(self._results)
        self._metrics.persist()
        self._logger.persist()
        self._output_writer.write_cache_statistics(self._cache.statistics())
        self._output_writer.write_validation_report(
            {
                "model_version": MODEL_VERSION,
                "validation_status": validation_status,
                "result_count": len(self._results),
            }
        )

    @staticmethod
    def _apply_template_defaults(variables: Dict[str, Any], task_type: str) -> None:
        defaults = {
            "beam_id": "GENERAL",
            "beam_name": "GENERAL",
            "annotation_id": "GENERAL",
            "region_id": "GENERAL",
            "annotation_text": "GENERAL",
            "artifact_name": "engineering_artifact",
        }
        for key, value in defaults.items():
            variables.setdefault(key, value)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    @property
    def results(self) -> list[EngineeringReasoningResult]:
        return list(self._results)
