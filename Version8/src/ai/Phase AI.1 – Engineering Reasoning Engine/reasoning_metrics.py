"""Collect and persist engineering reasoning metrics."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from reasoning_models import MODEL_VERSION, OUTPUT_DIR


@dataclass
class ReasoningMetricsEntry:
    reasoning_id: str
    task_type: str
    execution_time_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cache_hit: bool
    retry_count: int
    confidence: float
    reasoning_length: int
    model_name: str
    template_version: str


@dataclass
class ReasoningMetricsCollector:
    entries: List[ReasoningMetricsEntry] = field(default_factory=list)

    def record(self, entry: ReasoningMetricsEntry) -> None:
        self.entries.append(entry)

    def to_dict(self) -> Dict[str, Any]:
        sorted_entries = sorted(self.entries, key=lambda item: item.reasoning_id)
        return {
            "model_version": MODEL_VERSION,
            "metrics": [asdict(item) for item in sorted_entries],
        }

    def persist(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / "reasoning_metrics.json"
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
