"""Vision execution planner + live loop. Checkpointed per set. No beam-ID exceptions."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.hybrid_runner_adapter import execute_hybrid_beam
from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.live_caller import call_live_beam

from .artefact_reuse import (
    contract_compatible,
    decide_action,
    e2_fifth_ids,
    fifth_population_compatible,
    load_e2_row,
    load_e3_row,
    provenance_from_live,
    save_e3_row,
)
from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.checkpoint import write_checkpoint
from .config import FIFTH_SET_KEY, KIND_FALLBACK, KIND_HYBRID, MODE_LIVE, PROV_FALLBACK, PROV_NOT_AVAILABLE


def execute_one(
    *,
    v10: Path,
    out_root: Path,
    set_key: str,
    beam_id: str,
    model: Optional[Dict[str, Any]],
    catalog: Dict[str, Any],
    elig_row: Dict[str, Any],
    mode: str,
    hist: Optional[Dict[str, Any]],
    client_override: Optional[Callable],
    e2_reuse_allowed: bool,
) -> Dict[str, Any]:
    visual = elig_row.get("visual") or {}
    eligible = bool((elig_row.get("eligibility") or {}).get("eligible"))
    existing = load_e3_row(out_root, set_key, beam_id)
    e2_row = load_e2_row(v10, beam_id) if set_key == FIFTH_SET_KEY else None
    decision = decide_action(
        set_key=set_key,
        eligible=eligible,
        e3_row=existing,
        e2_row=e2_row,
        source_sha=visual.get("sha256"),
        historical=hist,
        e2_reuse_allowed=e2_reuse_allowed,
    )
    live_row: Dict[str, Any] = {
        "beam_id": beam_id,
        "set_key": set_key,
        "complete": True,
        "mode": mode,
        "action": decision["action"],
        "call_provenance": decision["provenance"],
        "reuse_source": decision.get("reuse_source"),
        "eligible": eligible,
        "gate_status": (elig_row.get("gate") or {}).get("status"),
        "visual": {
            "path": visual.get("path"),
            "sha256": visual.get("sha256"),
            "source": visual.get("source"),
        },
        "called": False,
        "semantic_usable": False,
        "failure_category": None,
    }
    parsed = None
    extracted = None
    reused_row = existing if decision.get("reuse_source") == "E3_CHECKPOINT" else e2_row
    if decision["action"] == "BLOCK":
        live_row["failure_category"] = "VISUAL_NOT_READY"
        live_row["call_provenance"] = PROV_NOT_AVAILABLE
    elif decision["action"] == "REUSE" and reused_row:
        live_row = dict(reused_row)
        live_row["beam_id"] = beam_id
        live_row["set_key"] = set_key
        live_row["call_provenance"] = decision["provenance"]
        live_row["action"] = "REUSE"
        live_row["reuse_source"] = decision.get("reuse_source")
        live_row["called"] = False
        parsed = reused_row.get("parsed")
        extracted = reused_row.get("extracted")
        live_row["semantic_usable"] = bool(reused_row.get("semantic_usable"))
        live_row["api_success"] = reused_row.get("api_success")
        live_row["schema_valid"] = reused_row.get("schema_valid")
        live_row["failure_category"] = reused_row.get("failure_category")
        live_row["usage"] = reused_row.get("usage")
        live_row["model"] = reused_row.get("model")
        save_e3_row(out_root, set_key, {k: v for k, v in live_row.items() if k != "audit"})
    elif mode != MODE_LIVE:
        live_row["complete"] = False
        live_row["failure_category"] = "LIVE_DISABLED"
        live_row["called"] = False
        live_row["call_provenance"] = PROV_FALLBACK
    else:
        result = call_live_beam(
            version10_root=v10,
            beam_id=beam_id,
            render_path=Path(visual.get("path") or ""),
            context_source=str(visual.get("source") or f"{set_key.upper()}_RENDER"),
            detail_source=str(visual.get("source") or f"{set_key.upper()}_RENDER"),
            client_override=client_override,
        )
        live_row.update(
            {
                "called": True,
                "complete": True,
                "attempts": result.get("attempts"),
                "retry_count": result.get("retry_count"),
                "audit": result.get("audit"),
                "parsed": result.get("parsed"),
                "extracted": result.get("extracted"),
                "failure_category": result.get("failure_category"),
                "semantic_usable": result.get("semantic_usable"),
                "schema_valid": result.get("schema_valid"),
                "api_success": result.get("api_success"),
                "model": result.get("model"),
                "usage": result.get("usage"),
                "call_provenance": provenance_from_live(
                    str(result.get("failure_category")), intended=decision["provenance"]
                ),
            }
        )
        parsed = result.get("parsed")
        extracted = result.get("extracted")
        save_e3_row(out_root, set_key, live_row)

    vision_row = None
    if live_row.get("semantic_usable") and extracted:
        vision_row = {
            "usable": True,
            "source": live_row.get("reuse_source") or "E3_LIVE",
            "extracted": extracted,
            "parsed": parsed,
        }
    calc = execute_hybrid_beam(beam_id=beam_id, model=model, vision_row=vision_row, catalog=catalog)
    if vision_row:
        calc["provenance_kind"] = KIND_HYBRID
        calc["vision_used"] = True
    else:
        calc["provenance_kind"] = KIND_FALLBACK
        calc["vision_used"] = False
        if not live_row.get("call_provenance"):
            live_row["call_provenance"] = PROV_FALLBACK
    if isinstance(calc.get("hybrid_semantic"), dict):
        calc["hybrid_semantic"].setdefault("source_provenance", {})
        calc["hybrid_semantic"]["source_provenance"]["mode"] = mode
        calc["hybrid_semantic"]["source_provenance"]["call_provenance"] = live_row.get("call_provenance")
        calc["hybrid_semantic"]["source_provenance"]["set_key"] = set_key
    calc["set_key"] = set_key
    calc["live"] = {k: v for k, v in live_row.items() if k not in ("parsed", "extracted", "audit")}
    calc["live_full"] = live_row
    if (
        decision["action"] != "REUSE"
        and live_row.get("complete")
        and live_row.get("failure_category") != "LIVE_DISABLED"
    ):
        save_e3_row(out_root, set_key, live_row)
    return calc


def fifth_reuse_gate(*, v10: Path, current_ids: List[str]) -> Dict[str, Any]:
    contract = contract_compatible(v10)
    pop = fifth_population_compatible(current_ids=current_ids, e2_ids=e2_fifth_ids(v10))
    allowed = bool(contract.get("ok") and pop.get("ok"))
    return {
        "allowed": allowed,
        "contract": contract,
        "population": pop,
        "decision": "VISION_REUSED_CURRENT_ARCHITECTURE" if allowed else "RERUN_AFFECTED_BEAMS",
    }


def execute_set(
    *,
    v10: Path,
    out_root: Path,
    set_key: str,
    beam_ids: List[str],
    catalog: Dict[str, Any],
    eligibility: Dict[str, Any],
    mode: str,
    client_override: Optional[Callable] = None,
    e2_reuse_allowed: bool = False,
    historical_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    rows = []
    completed = []
    elig_by = eligibility.get("by_id") or {}
    hist_map = historical_by_id or {}
    total = len(beam_ids)
    for i, bid in enumerate(beam_ids, start=1):
        calc = execute_one(
            v10=v10,
            out_root=out_root,
            set_key=set_key,
            beam_id=bid,
            model=catalog.get(bid) if isinstance(catalog.get(bid), dict) else None,
            catalog=catalog,
            elig_row=elig_by.get(bid) or {},
            mode=mode,
            hist=hist_map.get(bid),
            client_override=client_override,
            e2_reuse_allowed=e2_reuse_allowed,
        )
        rows.append(calc)
        completed.append(bid)
        write_checkpoint(
            out_root,
            beam_ids=beam_ids,
            completed_ids=completed,
            status="IN_PROGRESS",
            extra={"set_key": set_key},
        )
        live = calc.get("live") or {}
        print(
            f"  [{set_key} {i}/{total}] {bid} kind={calc.get('provenance_kind')} "
            f"prov={live.get('call_provenance')} usable={live.get('semantic_usable')}",
            flush=True,
        )
    rows.sort(key=lambda r: str(r.get("beam_id") or ""))
    write_checkpoint(
        out_root,
        beam_ids=beam_ids,
        completed_ids=completed,
        status="COMPLETE",
        extra={"set_key": set_key},
    )
    return rows


__all__ = ["execute_one", "execute_set", "fifth_reuse_gate"]
