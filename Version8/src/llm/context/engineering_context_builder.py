"""Orchestrate deterministic engineering context construction."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

from src.llm.context.context_cache import ContextCache
from src.llm.context.context_collector import ContextCollector
from src.llm.context.context_compressor import ContextCompressor
from src.llm.context.context_filter import ContextFilter
from src.llm.context.context_models import ContextMetadata, ContextSection, EngineeringContext
from src.llm.context.context_registry import MODEL_VERSION
from src.llm.context.context_serializer import ContextSerializer
from src.llm.context.context_validator import ContextValidator
from src.llm.context.token_budget_manager import TokenBudgetManager

logger = logging.getLogger(__name__)


class EngineeringContextBuilder:
    """Build deterministic, task-aware engineering context blocks."""

    def __init__(
        self,
        *,
        collector: ContextCollector | None = None,
        context_filter: ContextFilter | None = None,
        serializer: ContextSerializer | None = None,
        compressor: ContextCompressor | None = None,
        token_manager: TokenBudgetManager | None = None,
        validator: ContextValidator | None = None,
        cache: ContextCache | None = None,
    ) -> None:
        self._collector = collector or ContextCollector()
        self._filter = context_filter or ContextFilter()
        self._serializer = serializer or ContextSerializer()
        self._compressor = compressor or ContextCompressor()
        self._token_manager = token_manager or TokenBudgetManager()
        self._validator = validator or ContextValidator()
        self._cache = cache or ContextCache()

    def build_context(
        self,
        task_type: str,
        engineering_objects: Dict[str, Any],
        metadata: Dict[str, Any] | None = None,
    ) -> EngineeringContext:
        started = time.perf_counter()
        normalized_task = task_type.upper()
        input_checksum = self._input_checksum(normalized_task, engineering_objects)
        cache_key = self._cache.build_key(normalized_task, engineering_objects)

        cached = self._cache.get(cache_key, input_checksum)
        if cached is not None:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "Engineering context cache hit task=%s sections=%s tokens=%s duration_ms=%.2f validation=PASS",
                normalized_task,
                len(cached.sections),
                cached.estimated_tokens,
                duration_ms,
            )
            return cached

        collected = self._collector.collect(engineering_objects)
        filtered = self._filter.filter(normalized_task, collected)

        serialized_sections = [
            {
                "section_name": section["section_name"],
                "priority": section["priority"],
                "content": self._serializer.serialize(section["content"]),
            }
            for section in filtered
        ]

        original_size = len(self._serializer.to_text({"sections": serialized_sections}))
        compressed_sections = self._compressor.compress_sections(serialized_sections)
        compressed_size = len(self._serializer.to_text({"sections": compressed_sections}))
        compression_ratio = self._compressor.compression_ratio(original_size, compressed_size)

        budgeted_sections = self._token_manager.apply_budget(normalized_task, compressed_sections)
        context_sections = self._to_context_sections(budgeted_sections)
        estimated_tokens = self._token_manager.estimate_total(budgeted_sections)

        context_payload = {
            "task_type": normalized_task,
            "sections": [
                {
                    "section_name": section.section_name,
                    "priority": section.priority,
                    "content": section.content,
                    "token_estimate": section.token_estimate,
                }
                for section in context_sections
            ],
        }
        context_checksum = self._serializer.checksum(context_payload)
        context_id = hashlib.sha256(f"{normalized_task}:{input_checksum}".encode("utf-8")).hexdigest()[:16]

        context = EngineeringContext(
            context_id=context_id,
            context_version=MODEL_VERSION,
            task_type=normalized_task,
            sections=context_sections,
            estimated_tokens=estimated_tokens,
            checksum=context_checksum,
            metadata=ContextMetadata(
                generated_timestamp=EngineeringContext.timestamp(),
                source_modules=sorted(collected.keys()),
                schema_version=MODEL_VERSION,
                builder_version=MODEL_VERSION,
                extra=dict(metadata or {}),
            ),
        )

        self._validator.validate(context)
        self._cache.set(cache_key, input_checksum, context)

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "Engineering context built task=%s sections=%s tokens=%s compression_ratio=%.4f cache=MISS duration_ms=%.2f validation=PASS",
            normalized_task,
            len(context.sections),
            context.estimated_tokens,
            compression_ratio,
            duration_ms,
        )
        return context

    def to_prompt_variables(self, context: EngineeringContext) -> Dict[str, str]:
        payload = self._serializer.sections_to_prompt_payload(
            [
                {
                    "section_name": section.section_name,
                    "content": section.content,
                }
                for section in context.sections
            ]
        )
        return {
            "engineering_context": self._serializer.to_text(payload),
            "estimated_tokens": str(context.estimated_tokens),
            "context_version": context.context_version,
            "context_checksum": context.checksum,
        }

    def _to_context_sections(self, sections: List[Dict[str, Any]]) -> List[ContextSection]:
        result: List[ContextSection] = []
        for section in sections:
            content = section["content"]
            checksum = self._serializer.checksum(content if isinstance(content, dict) else {"value": content})
            result.append(
                ContextSection(
                    section_name=str(section["section_name"]),
                    priority=str(section["priority"]),
                    content=content,
                    token_estimate=int(section["token_estimate"]),
                    checksum=checksum,
                )
            )
        return result

    def _input_checksum(self, task_type: str, engineering_objects: Dict[str, Any]) -> str:
        payload = {
            "task_type": task_type,
            "engineering_objects": self._serializer.serialize(engineering_objects),
        }
        return self._serializer.checksum(payload)
