"""Centralized prompt execution path."""

from __future__ import annotations

from typing import Any

from src.llm.claude_client import ClaudeClient
from src.llm.context.engineering_context_builder import EngineeringContextBuilder
from src.llm.exceptions import ClaudeResponseFormatError
from src.llm.json_engine.response_models import StructuredResponse
from src.llm.json_engine.response_retry import ResponseRetryEngine
from src.llm.prompts.prompt_manager import PromptManager
from src.llm.response_parser import extract_text, normalize_whitespace, strip_code_blocks, strip_markdown


class PromptExecutor:
    """Execute prompts through the centralized Claude client."""

    def __init__(
        self,
        client: ClaudeClient | None = None,
        prompt_manager: PromptManager | None = None,
        retry_engine: ResponseRetryEngine | None = None,
        context_builder: EngineeringContextBuilder | None = None,
    ) -> None:
        self._client = client or ClaudeClient()
        self._prompt_manager = prompt_manager or PromptManager()
        self._retry_engine = retry_engine or ResponseRetryEngine()
        self._context_builder = context_builder or EngineeringContextBuilder()

    def execute(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
        *,
        normalize: bool = True,
        strip_md: bool = False,
        strip_code: bool = False,
    ) -> str:
        """Run a raw prompt and return plain text only."""
        text = self._client.generate_response(user_prompt, system_prompt=system_prompt)
        return self._post_process(text, normalize=normalize, strip_md=strip_md, strip_code=strip_code)

    def execute_template(
        self,
        template_name: str,
        variables: dict[str, Any] | None = None,
        system_template: str | None = None,
        *,
        system_variables: dict[str, Any] | None = None,
        normalize: bool = True,
        strip_md: bool = False,
        strip_code: bool = False,
    ) -> str:
        """Render a registered template and execute it through Claude."""
        prompt = self._prompt_manager.get_prompt(template_name, variables)
        system_prompt = self._build_system_prompt(system_template, system_variables)
        text = self._client.generate_response(prompt.rendered_prompt, system_prompt=system_prompt)
        return self._post_process(text, normalize=normalize, strip_md=strip_md, strip_code=strip_code)

    def execute_json(
        self,
        template_name: str,
        schema_name: str,
        variables: dict[str, Any] | None = None,
        system_template: str | None = "JSON_RESPONSE_RULES",
        *,
        system_variables: dict[str, Any] | None = None,
    ) -> StructuredResponse:
        """Render a template, execute Claude, and return a validated structured response."""
        prompt = self._prompt_manager.get_prompt(template_name, variables)
        system_prompt = self._build_system_prompt(system_template, system_variables)

        def fetch_response(correction: str | None) -> str:
            user_prompt = prompt.rendered_prompt
            if correction:
                user_prompt = f"{user_prompt}\n\n{correction}"
            return self._client.generate_response(user_prompt, system_prompt=system_prompt)

        return self._retry_engine.execute(fetch_response, schema_name)

    def execute_engineering(
        self,
        template_name: str,
        schema_name: str,
        task_type: str,
        engineering_objects: dict[str, Any],
        variables: dict[str, Any] | None = None,
        system_template: str | None = "JSON_RESPONSE_RULES",
        *,
        system_variables: dict[str, Any] | None = None,
    ) -> StructuredResponse:
        """Build deterministic engineering context and execute a structured JSON prompt."""
        context = self._context_builder.build_context(task_type, engineering_objects)
        merged_variables = dict(variables or {})
        merged_variables.update(self._context_builder.to_prompt_variables(context))
        return self.execute_json(
            template_name,
            schema_name,
            merged_variables,
            system_template,
            system_variables=system_variables,
        )

    def _build_system_prompt(
        self,
        system_template: str | None,
        system_variables: dict[str, Any] | None,
    ) -> str | None:
        if not system_template:
            return None
        return self._prompt_manager.get_prompt(system_template, system_variables).rendered_prompt

    @staticmethod
    def extract_text_from_response(response: object) -> str:
        """Deterministic helper for SDK response objects."""
        return extract_text(response)

    @staticmethod
    def _post_process(
        text: str,
        *,
        normalize: bool,
        strip_md: bool,
        strip_code: bool,
    ) -> str:
        if strip_code:
            text = strip_code_blocks(text)
        if strip_md:
            text = strip_markdown(text)
        if normalize:
            text = normalize_whitespace(text)
        if not text:
            raise ClaudeResponseFormatError("Claude returned an empty response.")
        return text
