"""
Derive P2 leader recovery population from QA.4.1 artefacts.
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PhaseQA31_pipeline_diagnostics.artefact_locator import PRIORITY_FOURTH_BEAMS

from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID, LeaderRecoveryConfig


def _load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_qa41_bundle(qa41_root: Path) -> Dict[str, Any]:
    root = Path(qa41_root)
    return {
        "DroppedEntityAudit": _load(root / "DroppedEntityAudit.json"),
        "LeaderChainAudit": _load(root / "LeaderChainAudit.json"),
        "QA41BaselineValidation": _load(root / "QA41BaselineValidation.json"),
        "PASS_FAIL_REPORT": _load(root / "PASS_FAIL_REPORT.json"),
    }


def load_qa42_summary(qa42_root: Path) -> Optional[Dict[str, Any]]:
    return _load(Path(qa42_root) / "QA42_recovery_summary.json")


def derive_leader_population(
    qa41: Dict[str, Any],
    *,
    config: LeaderRecoveryConfig = DEFAULT_CONFIG,
    priority_beams: Sequence[str] = PRIORITY_FOURTH_BEAMS,
) -> Dict[str, Any]:
    doc = qa41.get("DroppedEntityAudit") or {}
    entities = list(doc.get("entities") or [])
    priority = set(priority_beams)
    fifth = sixth = 0
    fourth: List[Dict[str, Any]] = []
    for e in entities:
        ds = str(e.get("drawing_set") or e.get("set_key") or "").lower()
        if "fifth" in ds:
            fifth += 1
            continue
        if "sixth" in ds:
            sixth += 1
            continue
        if str(e.get("beam_id") or "") not in priority:
            continue
        fourth.append(e)

    leaders = [
        e
        for e in fourth
        if e.get("primary_audit_category") == config.target_audit_category
    ]

    def _key(e: Dict[str, Any]):
        return (
            str(e.get("beam_id") or ""),
            str(e.get("entity_id") or ""),
            str(e.get("stable_key") or ""),
        )

    leaders = sorted(leaders, key=_key)
    high = [e for e in leaders if e.get("recovery_potential") == "HIGH"]
    medium = [e for e in leaders if e.get("recovery_potential") == "MEDIUM"]
    low = [e for e in leaders if e.get("recovery_potential") == "LOW"]
    unknown = [
        e
        for e in leaders
        if e.get("recovery_potential") not in ("HIGH", "MEDIUM", "LOW")
    ]

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "priority_beams": list(priority_beams),
        "original_dropped": len(fourth),
        "leader_population": leaders,
        "leader_count": len(leaders),
        "high_count": len(high),
        "medium_count": len(medium),
        "low_count": len(low),
        "unknown_count": len(unknown),
        "high_population": high,
        "medium_population": medium,
        "low_population": low,
        "unknown_population": unknown,
        "fourth_set_recovery_population": len(leaders),
        "fifth_set_recovery_population": fifth,
        "sixth_set_recovery_population": sixth,
    }
