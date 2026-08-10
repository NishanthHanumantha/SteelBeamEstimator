"""
Load the 23 dropped leaders from QA.4.3 (derived, not hard-coded).
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PhaseQA31_pipeline_diagnostics.artefact_locator import PRIORITY_FOURTH_BEAMS

from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID, P21Config


def _load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_inputs(
    *,
    qa43_root: Path,
    qa41_root: Path,
    qa42_root: Path,
) -> Dict[str, Any]:
    return {
        "qa43_audit": _load(Path(qa43_root) / "leader_recovery_audit.json"),
        "qa43_candidates": _load(Path(qa43_root) / "QA43_recovery_candidates.json"),
        "qa43_summary": _load(Path(qa43_root) / "QA43_recovery_summary.json"),
        "qa41_audit": _load(Path(qa41_root) / "DroppedEntityAudit.json"),
        "qa41_leader": _load(Path(qa41_root) / "LeaderChainAudit.json"),
        "qa42_summary": _load(Path(qa42_root) / "QA42_recovery_summary.json"),
    }


def derive_leader_rows(
    inputs: Dict[str, Any],
    *,
    priority_beams: Sequence[str] = PRIORITY_FOURTH_BEAMS,
    config: P21Config = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    qa43 = inputs.get("qa43_audit") or {}
    rows = list(qa43.get("rows") or [])
    priority = set(priority_beams)
    leaders = [r for r in rows if str(r.get("beam_id") or "") in priority]
    leaders = sorted(
        leaders,
        key=lambda r: (
            str(r.get("beam_id") or ""),
            str(r.get("entity_id") or ""),
            str(r.get("stable_key") or ""),
        ),
    )
    eligible = [r for r in leaders if r.get("recovery_eligible")]
    excluded = [r for r in leaders if not r.get("recovery_eligible")]

    # Index QA.4.1 for geometry enrichment
    qa41_by_key = {}
    for e in ((inputs.get("qa41_audit") or {}).get("entities") or []):
        if e.get("primary_audit_category") == "LEADER_CHAIN_FAILURE":
            qa41_by_key[str(e.get("stable_key") or f"{e.get('beam_id')}::{e.get('entity_id')}")] = e
    leader_audit_by_key = {}
    for e in ((inputs.get("qa41_leader") or {}).get("entities") or []):
        leader_audit_by_key[str(e.get("stable_key") or f"{e.get('beam_id')}::{e.get('entity_id')}")] = e

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "leaders": leaders,
        "leader_count": len(leaders),
        "eligible": eligible,
        "eligible_count": len(eligible),
        "excluded": excluded,
        "excluded_count": len(excluded),
        "qa41_by_key": qa41_by_key,
        "leader_audit_by_key": leader_audit_by_key,
        "fifth_set_count": 0,
        "sixth_set_count": 0,
    }
