"""
normalized_fact.py — Helpers for working with EngineeringFact collections.
MODEL_VERSION: 7.12.0
"""
from __future__ import annotations

import dataclasses
from typing import Any, Dict, List

from .fact_models import EngineeringFact


def fact_to_dict(fact: EngineeringFact) -> Dict[str, Any]:
    """Convert EngineeringFact to JSON-serializable dict."""
    return dataclasses.asdict(fact)


def facts_by_beam(facts: List[EngineeringFact]) -> Dict[str, List[EngineeringFact]]:
    """Group a flat list of facts by beam_id."""
    result: Dict[str, List[EngineeringFact]] = {}
    for f in facts:
        result.setdefault(f.beam_id, []).append(f)
    return result


def flat_facts(facts_by_beam_dict: Dict[str, List[EngineeringFact]]) -> List[EngineeringFact]:
    """Flatten beam-keyed fact dict to a single list."""
    return [f for fl in facts_by_beam_dict.values() for f in fl]
