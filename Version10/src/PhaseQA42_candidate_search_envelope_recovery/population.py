"""
Load controlled recovery population from QA.4.1 artefacts (no hard-coded IDs).
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PhaseQA31_pipeline_diagnostics.artefact_locator import PRIORITY_FOURTH_BEAMS

from .config import CandidateRecoveryConfig, DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID


def _load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_qa41_bundle(qa41_root: Path) -> Dict[str, Any]:
    root = Path(qa41_root)
    return {
        "DroppedEntityAudit": _load(root / "DroppedEntityAudit.json"),
        "EnvelopeAudit": _load(root / "EnvelopeAudit.json"),
        "RecoveryEvidence": _load(root / "RecoveryEvidence.json"),
        "QA41BaselineValidation": _load(root / "QA41BaselineValidation.json"),
        "PASS_FAIL_REPORT": _load(root / "PASS_FAIL_REPORT.json"),
        "RegressionReport": _load(root / "RegressionReport.json"),
    }


def derive_populations(
    qa41: Dict[str, Any],
    *,
    config: CandidateRecoveryConfig = DEFAULT_CONFIG,
    priority_beams: Sequence[str] = PRIORITY_FOURTH_BEAMS,
) -> Dict[str, Any]:
    """
    Derive envelope / HIGH recovery populations from QA.4.1 DroppedEntityAudit.
    Fifth/Sixth excluded by Fourth Set beam filter.
    """
    doc = qa41.get("DroppedEntityAudit") or {}
    entities = list(doc.get("entities") or [])
    priority = set(priority_beams)

    fourth: List[Dict[str, Any]] = []
    fifth = 0
    sixth = 0
    for e in entities:
        ds = str(e.get("drawing_set") or e.get("set_key") or "").lower()
        if "fifth" in ds:
            fifth += 1
            continue
        if "sixth" in ds:
            sixth += 1
            continue
        bid = str(e.get("beam_id") or "")
        if bid not in priority:
            # Non-priority Fourth beams are out of controlled population
            continue
        fourth.append(e)

    envelope = [
        e
        for e in fourth
        if e.get("primary_audit_category") == config.target_audit_category
    ]
    high = [
        e for e in envelope if e.get("recovery_potential") == "HIGH"
    ]
    medium = [
        e for e in envelope if e.get("recovery_potential") == "MEDIUM"
    ]
    low = [
        e for e in envelope if e.get("recovery_potential") == "LOW"
    ]

    # Deterministic order
    def _key(e: Dict[str, Any]):
        return (
            str(e.get("beam_id") or ""),
            str(e.get("entity_id") or ""),
            str(e.get("stable_key") or ""),
        )

    fourth = sorted(fourth, key=_key)
    envelope = sorted(envelope, key=_key)
    high = sorted(high, key=_key)
    medium = sorted(medium, key=_key)
    low = sorted(low, key=_key)

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "priority_beams": list(priority_beams),
        "original_dropped": len(fourth),
        "envelope_population": envelope,
        "envelope_count": len(envelope),
        "high_potential_population": high,
        "high_count": len(high),
        "medium_population": medium,
        "medium_count": len(medium),
        "low_population": low,
        "low_count": len(low),
        "fourth_set_recovery_population": len(high),
        "fifth_set_recovery_population": fifth,
        "sixth_set_recovery_population": sixth,
        "all_dropped_fourth": fourth,
    }
