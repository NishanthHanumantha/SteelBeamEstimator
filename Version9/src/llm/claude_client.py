"""Centralized Anthropic Claude client."""

from __future__ import annotations

import os
import time
from typing import Any

from anthropic import Anthropic, APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError
from dotenv import load_dotenv
from loguru import logger

from src.llm.claude_config import ClaudeConfig
from src.llm.exceptions import (
    ClaudeAPIError,
    ClaudeAuthenticationError,
    ClaudeRateLimitError,
    ClaudeResponseFormatError,
    ClaudeTimeoutError,
)
from src.llm.response_parser import extract_text


def _estimate_tokens(text: str) -> int:
    """Conservative token estimate without logging prompt content."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def load_api_key() -> str:
    """Load ANTHROPIC_API_KEY from the repository root .env file."""
    dotenv_path = ClaudeConfig.DOTENV_PATH
    if not dotenv_path.exists():
        raise ClaudeAuthenticationError(
            f".env file not found at {dotenv_path}. "
            f"Create it with {ClaudeConfig.API_KEY_ENV}=<your-key>."
        )

    load_dotenv(dotenv_path, override=True)
    api_key = os.getenv(ClaudeConfig.API_KEY_ENV)
    if not api_key:
        raise ClaudeAuthenticationError(
            f"{ClaudeConfig.API_KEY_ENV} is missing in {dotenv_path}."
        )
    return api_key


def map_sdk_exception(exc: Exception) -> ClaudeAPIError:
    """Map Anthropic SDK exceptions to project-specific errors."""
    if isinstance(exc, AuthenticationError):
        return ClaudeAuthenticationError(str(exc))
    if isinstance(exc, RateLimitError):
        return ClaudeRateLimitError(str(exc))
    if isinstance(exc, APITimeoutError):
        return ClaudeTimeoutError(str(exc))
    if isinstance(exc, APIStatusError):
        if exc.status_code == 408:
            return ClaudeTimeoutError(str(exc))
        if exc.status_code == 429:
            return ClaudeRateLimitError(str(exc))
        if exc.status_code in {401, 403}:
            return ClaudeAuthenticationError(str(exc))
        return ClaudeAPIError(str(exc))
    if isinstance(exc, APIConnectionError):
        return ClaudeAPIError(str(exc))
    if isinstance(exc, ClaudeAPIError):
        return exc
    return ClaudeAPIError(str(exc))


class ClaudeClient:
    """Single Anthropic SDK entry point for the entire project."""

    def __init__(self, config: type[ClaudeConfig] = ClaudeConfig) -> None:
        self._config = config
        api_key = load_api_key()
        self._client = Anthropic(api_key=api_key, timeout=float(config.TIMEOUT_SECONDS))

    def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Execute a Claude request with retries, timeout, and structured logging."""
        messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
        prompt_length = len(prompt)
        estimated_input_tokens = _estimate_tokens(prompt) + _estimate_tokens(system_prompt or "")

        last_error: Exception | None = None
        for attempt in range(1, self._config.MAX_RETRIES + 1):
            started = time.perf_counter()
            try:
                kwargs: dict[str, Any] = {
                    "model": self._config.MODEL_NAME,
                    "max_tokens": self._config.MAX_OUTPUT_TOKENS,
                    "temperature": self._config.TEMPERATURE,
                    "messages": messages,
                }
                if system_prompt:
                    kwargs["system"] = system_prompt

                response = self._client.messages.create(**kwargs)
                text = extract_text(response)
                elapsed = time.perf_counter() - started
                estimated_output_tokens = _estimate_tokens(text)

                logger.info(
                    "Claude request success model={} prompt_length={} "
                    "estimated_input_tokens={} estimated_output_tokens={} "
                    "execution_time_s={:.3f} retry_count={}",
                    self._config.MODEL_NAME,
                    prompt_length,
                    estimated_input_tokens,
                    estimated_output_tokens,
                    elapsed,
                    attempt - 1,
                )
                return text
            except Exception as exc:
                elapsed = time.perf_counter() - started
                mapped = map_sdk_exception(exc)
                last_error = mapped
                logger.warning(
                    "Claude request failure model={} prompt_length={} "
                    "estimated_input_tokens={} execution_time_s={:.3f} "
                    "retry_count={} error_type={} success={}",
                    self._config.MODEL_NAME,
                    prompt_length,
                    estimated_input_tokens,
                    elapsed,
                    attempt,
                    type(mapped).__name__,
                    False,
                )
                if attempt >= self._config.MAX_RETRIES:
                    break
                time.sleep(min(2 ** (attempt - 1), 8))

        assert last_error is not None
        if isinstance(last_error, ClaudeResponseFormatError):
            raise last_error
        raise last_error
