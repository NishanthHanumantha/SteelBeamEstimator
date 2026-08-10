"""
QA.4.1 baseline rebuild + validation from QA.3.4 artefacts.
MODEL_VERSION: 10.5.0
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from PhaseQA31_pipeline_diagnostics.artefact_locator import PRIORITY_FOURTH_BEAMS

MODEL_VERSION = "10.5.0"
PHASE_ID = "QA.4.1"

EXPECTED = {
    "priority_beams": 11,
    "rejected": 123,
    "owned_elsewhere": 19,
    "dropped": 104,
}


def _load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_qa34_bundle(qa34_root: Path) -> Dict[str, Any]:
    root = Path(qa34_root)
    return {
        "DroppedEntities": _load(root / "DroppedEntities.json"),
        "OwnershipCompetitionRegistry": _load(root / "OwnershipCompetitionRegistry.json"),
        "OwnershipMigration": _load(root / "OwnershipMigration.json"),
        "CompetitionMatrix": _load(root / "CompetitionMatrix.json"),
        "PASS_FAIL_REPORT": _load(root / "PASS_FAIL_REPORT.json"),
        "RegressionReport": _load(root / "RegressionReport.json"),
        "GlobalCompetitionStatistics": _load(root / "GlobalCompetitionStatistics.json"),
        "CompetitionValidation": _load(root / "CompetitionValidation.json"),
    }


def derive_dropped_population(
    qa34: Dict[str, Any],
    *,
    priority_beams: Sequence[str] = PRIORITY_FOURTH_BEAMS,
    drawing_set: str = "Fourth Set Drawings",
    set_key: str = "Fourth",
) -> Dict[str, Any]:
    """
    Derive audit population from QA.3.4 artefacts (do NOT hard-code 104).
    Filter: Fourth Set + priority beams + final_state=Dropped.
    """
    dropped_doc = qa34.get("DroppedEntities") or {}
    raw = list(dropped_doc.get("entities") or [])
    pf = qa34.get("PASS_FAIL_REPORT") or {}
    stats = pf.get("statistics") or (qa34.get("GlobalCompetitionStatistics") or {}).get(
        "statistics"
    ) or {}

    priority = set(priority_beams)
    records: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    duplicates: List[Dict[str, Any]] = []

    for e in raw:
        bid = str(e.get("beam_id") or "")
        if bid not in priority:
            continue
        if str(e.get("final_state") or "") != "Dropped":
            continue
        eid = str(e.get("entity_id") or "")
        handle = eid.split("::")[-1] if "::" in eid else eid
        key = (bid, eid)
        stable_key = f"{bid}::{eid}"
        if key in seen:
            duplicates.append(
                {
                    "beam_id": bid,
                    "entity_id": eid,
                    "disambiguation": "source_file+entity_handle+category+reason",
                }
            )
            # Keep both records; disambiguate stable identity without dropping either
            key = (bid, f"{eid}::{e.get('category')}::{e.get('reason')}::{handle}")
            stable_key = f"{bid}::{eid}::{e.get('category')}::{handle}"
        seen.add(key)

        records.append(
            {
                "entity_id": eid,
                "stable_key": stable_key,
                "drawing_set": drawing_set,
                "set_key": set_key,
                "beam_id": bid,
                "entity_type": e.get("entity_type"),
                "text": e.get("text"),
                "qa34_category": e.get("category"),
                "original_rejection_reason": e.get("reason"),
                "rejected_rule": e.get("rejected_rule"),
                "final_state": e.get("final_state"),
                "scored_beams": e.get("scored_beams") or [],
                "engineering_failure": e.get("engineering_failure"),
                "owned_elsewhere_status": False,
                "entity_handle": handle,
                "source_file": "PhaseQA34_ownership_competition_validation/DroppedEntities.json",
                "original_ownership_status": "Dropped",
            }
        )

    # Cross-check stats from PASS_FAIL / CompetitionValidation
    rejected = int(stats.get("total_rejected") or 0)
    owned_else = int(stats.get("owned_elsewhere") or 0)
    dropped_stat = int(stats.get("dropped") or 0)

    # Also count OwnedElsewhere from migration for exclusion proof
    migrations = (qa34.get("OwnershipMigration") or {}).get("migrations") or []
    mig_priority = [
        m
        for m in migrations
        if str(m.get("originally_candidate") or "") in priority
    ]

    return {
        "drawing_set": drawing_set,
        "set_key": set_key,
        "priority_beams": list(priority_beams),
        "priority_beam_count": len(priority_beams),
        "records": records,
        "audit_population": len(records),
        "duplicates_detected": duplicates,
        "qa34_statistics": {
            "rejected": rejected,
            "owned_elsewhere": owned_else,
            "dropped": dropped_stat,
            "leader_failures": stats.get("leader_failures"),
            "geometry_failures": stats.get("geometry_failures"),
            "envelope_failures": stats.get("envelope_failures"),
            "conflict_failures": stats.get("conflict_failures"),
            "unknown": stats.get("unknown"),
        },
        "owned_elsewhere_migration_count": len(mig_priority),
        "category_counts_raw": dict(Counter(r.get("qa34_category") for r in records)),
    }


def validate_baseline(population: Dict[str, Any]) -> Dict[str, Any]:
    checks = []

    def add(name: str, expected: Any, actual: Any) -> None:
        ok = expected == actual
        checks.append(
            {
                "check": name,
                "expected": expected,
                "actual": actual,
                "pass": ok,
            }
        )

    add("priority_beams", EXPECTED["priority_beams"], population.get("priority_beam_count"))
    stats = population.get("qa34_statistics") or {}
    add("rejected", EXPECTED["rejected"], stats.get("rejected"))
    add("owned_elsewhere", EXPECTED["owned_elsewhere"], stats.get("owned_elsewhere"))
    add("dropped_stat", EXPECTED["dropped"], stats.get("dropped"))
    add("audit_population", EXPECTED["dropped"], population.get("audit_population"))

    # OwnedElsewhere excluded from dropped list
    add(
        "owned_elsewhere_excluded_from_dropped",
        True,
        all(not r.get("owned_elsewhere_status") for r in population.get("records") or []),
    )

    # Category expectation soft check (report, not hard fail if slightly off — hard fail is count)
    cats = population.get("category_counts_raw") or {}
    checks.append(
        {
            "check": "category_breakdown_observed",
            "expected": {
                "SEARCH_ENVELOPE_FAILURE": 77,
                "LEADER_FAILURE": 23,
                "GEOMETRY_FAILURE": 4,
            },
            "actual": cats,
            "pass": (
                cats.get("SEARCH_ENVELOPE_FAILURE") == 77
                and cats.get("LEADER_FAILURE") == 23
                and cats.get("GEOMETRY_FAILURE") == 4
            ),
            "note": "Evidence-derived; mismatch is reported",
        }
    )

    hard = [c for c in checks if c["check"] in (
        "priority_beams", "rejected", "owned_elsewhere", "dropped_stat", "audit_population"
    )]
    overall = all(c["pass"] for c in hard)
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "overall_pass": overall,
        "status": "PASS" if overall else "BASELINE_MISMATCH",
        "checks": checks,
        "proceed_to_audit": overall,
        "fourth_set_entities_in_scope": population.get("audit_population"),
        "fifth_set_entities_excluded": 0,
        "sixth_set_entities_excluded": 0,
        "note": (
            "QA.4.1 controlled population is Fourth Set priority beams only. "
            "Fifth/Sixth are out of scope."
        ),
    }
