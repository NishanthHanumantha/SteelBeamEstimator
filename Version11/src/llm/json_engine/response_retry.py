"""Automatic retry for invalid Claude JSON responses."""

from __future__ import annotations

from typing import Callable

from loguru import logger

from src.llm.claude_config import ClaudeConfig
from src.llm.json_engine.json_response_engine import JSONResponseEngine
from src.llm.json_engine.response_models import JSONEngineError, ResponseRetryError, StructuredResponse

RETRY_SUFFIX = (
    "The previous response was invalid.\n"
    "Return ONLY valid JSON."
)


class ResponseRetryEngine:
    """Retry Claude responses that fail JSON extraction or schema validation."""

    def __init__(
        self,
        json_engine: JSONResponseEngine | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._json_engine = json_engine or JSONResponseEngine()
        self._max_retries = max_retries or ClaudeConfig.MAX_RETRIES

    def execute(
        self,
        fetch_response: Callable[[str | None], str],
        schema_name: str,
    ) -> StructuredResponse:
        correction: str | None = None
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response_text = fetch_response(correction)
                result = self._json_engine.parse_response(response_text, schema_name)
                logger.info(
                    "JSON response retry success schema={} retry_count={} confidence={}",
                    schema_name,
                    attempt - 1,
                    result.confidence,
                )
                return result
            except JSONEngineError as exc:
                last_error = exc
                correction = RETRY_SUFFIX
                logger.warning(
                    "JSON response retry failure schema={} retry_count={} error_type={}",
                    schema_name,
                    attempt,
                    type(exc).__name__,
                )
                if attempt >= self._max_retries:
                    break

        raise ResponseRetryError(
            f"Failed to obtain valid JSON for schema {schema_name} after "
            f"{self._max_retries} attempts: {last_error}"
        ) from last_error
