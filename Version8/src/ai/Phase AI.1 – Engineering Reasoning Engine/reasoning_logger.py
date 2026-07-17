"""Structured logging for engineering reasoning execution."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from reasoning_models import MODEL_VERSION, OUTPUT_DIR


@dataclass
class ReasoningLogEntry:
    reasoning_id: str
    task_type: str
    duration_ms: float
    confidence: float
    cache_hit: bool
    retry_count: int
    model_name: str
    template_version: str
    validation_status: str


@dataclass
class ReasoningLogger:
    entries: List[ReasoningLogEntry] = field(default_factory=list)

    def log(self, entry: ReasoningLogEntry) -> None:
        self.entries.append(entry)

    def to_dict(self) -> Dict[str, Any]:
        sorted_entries = sorted(self.entries, key=lambda item: (item.task_type, item.reasoning_id))
        return {
            "model_version": MODEL_VERSION,
            "logs": [asdict(item) for item in sorted_entries],
        }

    def persist(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / "reasoning_logs.json"
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
