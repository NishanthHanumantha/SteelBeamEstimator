"""
propagation_models.py — Data models for V.TEST.3.3.
MODEL_VERSION: 8.1.4
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class PropagationTraceResult:
    model_version: str
    phase_id: str
    timestamp: str
    annotation_matrix: List[Dict[str, Any]] = field(default_factory=list)
    beam_matrix: List[Dict[str, Any]] = field(default_factory=list)
    engineering_bar_creation_trace: List[Dict[str, Any]] = field(default_factory=list)
    filter_audit: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    lifecycle_traces: List[Dict[str, Any]] = field(default_factory=list)
    set3_summary: Dict[str, Any] = field(default_factory=dict)
    root_cause_ranking: List[Dict[str, Any]] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = "A"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
