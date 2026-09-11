"""Central prompt management orchestrator."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from loguru import logger

from src.llm.prompts.prompt_models import PromptTemplate
from src.llm.prompts.prompt_registry import PromptRegistry
from src.llm.prompts.template_loader import TemplateLoader
from src.llm.prompts.template_renderer import TemplateRenderer
from src.llm.prompts.template_validator import TemplateValidator


class PromptManager:
    """Load, render, validate, and cache prompt templates."""

    def __init__(
        self,
        registry: type[PromptRegistry] = PromptRegistry,
        loader: TemplateLoader | None = None,
    ) -> None:
        self._registry = registry
        self._loader = loader or TemplateLoader()

    def get_prompt(
        self,
        template_name: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> PromptTemplate:
        started = time.perf_counter()
        entry = self._registry.get(template_name)
        loaded = self._loader.load(entry)
        values = dict(variables or {})

        TemplateValidator.validate(loaded.body, values, require_resolved=True)
        rendered = TemplateRenderer.render(loaded.body, values)

        elapsed = time.perf_counter() - started
        logger.info(
            "Prompt template rendered template_name={} template_version={} "
            "variable_count={} rendered_size={} render_duration_s={:.4f}",
            entry.template_name,
            loaded.metadata.version,
            len(values),
            len(rendered),
            elapsed,
        )

        return PromptTemplate(
            template_name=entry.template_name,
            template_path=str(entry.absolute_path),
            raw_template=loaded.body,
            rendered_prompt=rendered,
            variables=values,
            checksum=loaded.checksum,
            version=loaded.metadata.version,
            created_timestamp=PromptTemplate.now_timestamp(),
            metadata=loaded.metadata,
        )
