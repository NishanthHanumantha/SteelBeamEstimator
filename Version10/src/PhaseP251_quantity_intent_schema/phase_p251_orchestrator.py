"""
P2.5.1 orchestrator — Quantity Intent Schema.

Consumes P2.5.0 evidence packages. Deterministic only. No Claude.
No T18 / R.3.1 / engineering mutations.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PhaseP24_fourth_set_bar_failure_audit.artefacts import (  # noqa: E402
    load_fourth_set_bundle,
)
from PhaseP251_quantity_intent_schema.config import (  # noqa: E402
    CLAUDE,
    ENGINEERING_CHANGES,
    GOLDEN_B97A,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    P250_EVIDENCE_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    ROLE_TOP_BAR,
    SCOPE,
    SEM_LONGITUDINAL_BAR,
    STATUS_EXPLICIT,
    VALIDATION_PASS,
)
from PhaseP251_quantity_intent_schema.intent_builder import (  # noqa: E402
    build_intents_for_beam,
)
from PhaseP251_quantity_intent_schema.metrics import compute_metrics  # noqa: E402
from PhaseP251_quantity_intent_schema.models import QuantityIntent  # noqa: E402
from PhaseP251_quantity_intent_schema.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP251_quantity_intent_schema.report_builder import write_reports  # noqa: E402
from PhaseP251_quantity_intent_schema.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_evidence_packages(v10: Path) -> Dict[str, Dict[str, Any]]:
    root = v10 / "data" / "output" / P250_EVIDENCE_DIRNAME / "beams"
    packages: Dict[str, Dict[str, Any]] = {}
    if not root.exists():
        return packages
    for beam_dir in sorted(root.iterdir()):
        if not beam_dir.is_dir():
            continue
        path = beam_dir / "evidence.json"
        if not path.exists():
            continue
        packages[beam_dir.name] = json.loads(path.read_text(encoding="utf-8"))
    return packages


def _fingerprint_intents(intents: List[QuantityIntent]) -> str:
    rows = [
        {
            "intent_id": i.intent_id,
            "beam_id": i.beam_id,
            "annotation_id": i.annotation_id,
            "raw_text": i.raw_text,
            "normalized_text": i.normalized_text,
            "quantity_status": i.quantity_status,
            "quantity_value": i.quantity_value,
            "diameter_value_mm": i.diameter_value_mm,
            "leg_count": i.leg_count,
            "spacing_values_mm": i.spacing_values_mm,
            "semantic_type": i.semantic_type,
            "role": i.reinforcement_role,
            "validation_status": i.validation_status,
            "validation_reasons": i.validation_reasons,
            "links": i.evidence_links.to_dict() if i.evidence_links else None,
            "components": [c.to_dict() for c in i.components],
        }
        for i in intents
    ]
    return _stable_hash(rows)


def _check_golden_b97a(intents: List[QuantityIntent]) -> Dict[str, Any]:
    g = GOLDEN_B97A
    hit = next(
        (
            i
            for i in intents
            if i.beam_id == g["beam_id"] and i.annotation_id == g["annotation_id"]
        ),
        None,
    )
    ok = bool(
        hit
        and hit.raw_text.replace(" ", "") == "4-Y25"
        and hit.quantity_value == g["quantity_value"]
        and hit.diameter_value_mm == g["diameter_value_mm"]
        and hit.semantic_type == SEM_LONGITUDINAL_BAR
        and hit.reinforcement_role == ROLE_TOP_BAR
        and hit.quantity_status == STATUS_EXPLICIT
        and hit.evidence_links
        and hit.evidence_links.leader_id == g["leader_id"]
        and hit.evidence_links.ownership_id == g["ownership_id"]
        and hit.validation_status == VALIDATION_PASS
    )
    return {
        "pass": ok,
        "intent": hit.to_dict() if hit else None,
        "expected": g,
    }


def _check_golden_stirrup(intents: List[QuantityIntent]) -> Dict[str, Any]:
    # Prefer B97A 4L-Y8@100C/C if present
    candidates = [
        i
        for i in intents
        if "Y8@100" in (i.normalized_text or "")
        or (i.raw_text or "").replace(" ", "").upper().startswith("4L-Y8@100")
    ]
    if not candidates:
        candidates = [
            i
            for i in intents
            if i.semantic_type == "STIRRUP" and i.quantity_status == "SPACING_BASED"
        ]
    hit = candidates[0] if candidates else None
    ok = bool(
        hit
        and hit.semantic_type == "STIRRUP"
        and hit.leg_count == 4
        and hit.diameter_value_mm == 8.0
        and (
            hit.spacing_value_mm == 100.0
            or (hit.spacing_values_mm and hit.spacing_values_mm[0] == 100.0)
        )
        and hit.quantity_value is None
    )
    return {
        "pass": ok,
        "expression": hit.raw_text if hit else None,
        "intent": hit.to_dict() if hit else None,
    }


def _acceptance(
    *,
    unit: Dict[str, Any],
    determinism: Dict[str, Any],
    regression: Dict[str, Any],
    golden_b97: Dict[str, Any],
    golden_st: Dict[str, Any],
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    checks = [
        ("unit_tests", bool(unit.get("success"))),
        ("determinism", determinism.get("determinism_status") == "PASS"),
        ("regression", bool(regression.get("unchanged"))),
        ("golden_b97a", bool(golden_b97.get("pass"))),
        ("golden_stirrup", bool(golden_st.get("pass"))),
        ("intents_generated", int(metrics.get("quantity_intents_generated") or 0) > 0),
        ("provenance_coverage", float(metrics.get("PROVENANCE_COVERAGE") or 0) >= 99.0),
    ]
    detail = [{"name": n, "pass": p} for n, p in checks]
    return {"pass": all(p for _, p in checks), "checks": detail}


def run_phase_p251(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {MODE}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES} CLAUDE: {CLAUDE}")
    _log(f"  output: {out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "diagnostics" / "unit_tests.json", unit)
        _log(f"  Unit tests: {unit['passed']}/{unit['total']}")
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            _log(f"  FAIL details: {failed[:5]}")
            return {"success": False, "unit_tests": unit, "output_root": str(out_root)}

    bundle = load_fourth_set_bundle(v10)
    fp_paths = fingerprint_paths(v10, bundle.paths)
    fp_before = capture_fingerprints(fp_paths)

    packages = _load_evidence_packages(v10)
    _log(f"  Evidence packages loaded: {len(packages)}")

    all_intents: List[QuantityIntent] = []
    eligible = 0
    accepted_chains = 0
    owned_n = 0
    for bid in sorted(packages.keys()):
        ev = packages[bid]
        anns = ev.get("annotations") or []
        eligible += len(anns)
        accepted_chains += len((ev.get("leader_chains") or {}).get("accepted") or [])
        owned_n += len(ev.get("owned_geometry") or [])
        all_intents.extend(build_intents_for_beam(ev))

    all_intents.sort(key=lambda x: (x.beam_id, x.annotation_id, x.intent_id))
    hash1 = _fingerprint_intents(all_intents)

    # Determinism pass 2 — rebuild from same packages
    all_intents2: List[QuantityIntent] = []
    for bid in sorted(packages.keys()):
        all_intents2.extend(build_intents_for_beam(packages[bid]))
    all_intents2.sort(key=lambda x: (x.beam_id, x.annotation_id, x.intent_id))
    hash2 = _fingerprint_intents(all_intents2)
    determinism = {
        "determinism_status": "PASS" if hash1 == hash2 else "FAIL",
        "hash1": hash1,
        "hash2": hash2,
    }
    _log(f"  Determinism: {determinism['determinism_status']}")

    metrics = compute_metrics(
        intents=all_intents,
        eligible_annotation_count=eligible,
    )
    validation_summary = {
        "pass": sum(1 for i in all_intents if i.validation_status == VALIDATION_PASS),
        "partial": sum(1 for i in all_intents if i.validation_status == "PARTIAL"),
        "fail": sum(1 for i in all_intents if i.validation_status == "FAIL"),
        "total": len(all_intents),
    }
    golden_b97 = _check_golden_b97a(all_intents)
    golden_st = _check_golden_stirrup(all_intents)
    golden = {"b97a_4y25": golden_b97, "stirrup": golden_st}
    _log(f"  Golden B97A: {golden_b97.get('pass')} Stirrup: {golden_st.get('pass')}")

    fp_after = capture_fingerprints(fp_paths)
    regression = compare_fingerprints(fp_before, fp_after)
    soft = [c for c in (regression.get("changed") or []) if str(c).startswith("p251")]
    hard = [c for c in (regression.get("changed") or []) if c not in soft]
    regression = {
        **regression,
        "changed": hard,
        "soft_changed": soft,
        "unchanged": len(hard) == 0,
    }

    acceptance = _acceptance(
        unit=unit,
        determinism=determinism,
        regression=regression,
        golden_b97=golden_b97,
        golden_st=golden_st,
        metrics=metrics,
    )
    decision = "READY_FOR_P2.5.2" if acceptance["pass"] else "BLOCKED"

    meta = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "mode": MODE,
        "engineering_changes": ENGINEERING_CHANGES,
        "claude": CLAUDE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    input_stats = {
        "accepted_annotations": eligible,
        "accepted_chains": accepted_chains,
        "owned_geometry": owned_n,
        "beams": len(packages),
    }
    write_reports(
        out_root=out_root,
        meta=meta,
        intents=all_intents,
        metrics=metrics,
        validation_summary=validation_summary,
        golden=golden,
        regression=regression,
        determinism=determinism,
        unit_tests=unit,
        decision=decision,
        beam_count=len(packages),
        input_stats=input_stats,
    )
    _dump(out_root / "diagnostics" / "acceptance.json", acceptance)
    _dump(out_root / "RunSummary.json", {
        "meta": meta,
        "decision": decision,
        "metrics": metrics,
        "golden": golden,
        "determinism": determinism,
        "regression": regression,
        "acceptance": acceptance,
        "input_stats": input_stats,
    })

    _log(f"  intents={len(all_intents)} coverage={metrics.get('QUANTITY_INTENT_COVERAGE')}%")
    _log(f"  decision={decision}")
    return {
        "success": bool(acceptance["pass"]),
        "decision": decision,
        "meta": meta,
        "metrics": metrics,
        "golden": golden,
        "determinism": determinism,
        "regression": regression,
        "unit_tests": unit,
        "acceptance": acceptance,
        "input_stats": input_stats,
        "output_root": str(out_root),
    }
