"""Vision execution planner + live loop. Checkpointed. No beam-ID exceptions."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.hybrid_runner_adapter import execute_hybrid_beam
from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.vision_artifact_loader import discover_vision_artefacts

from .artefact_reuse import decide_action, load_e2_row, provenance_from_live, save_e2_row
from .checkpoint import write_checkpoint
from .config import KIND_FALLBACK, KIND_HYBRID, MODE_LIVE, PROV_BLOCKED, PROV_FALLBACK
from .live_caller import call_live_beam


def historical_by_id(v10: Path) -> Dict[str, Dict[str, Any]]:
    vis = discover_vision_artefacts(v10)
    return vis.get("by_id") or {}


def execute_one(
    *,
    v10: Path,
    out_root: Path,
    beam_id: str,
    model: Optional[Dict[str, Any]],
    catalog: Dict[str, Any],
    elig_row: Dict[str, Any],
    mode: str,
    hist: Optional[Dict[str, Any]],
    client_override: Optional[Callable],
) -> Dict[str, Any]:
    visual = (elig_row.get("visual") or {})
    eligible = bool((elig_row.get("eligibility") or {}).get("eligible"))
    existing = load_e2_row(out_root, beam_id)
    decision = decide_action(eligible=eligible, e2_row=existing, source_sha=visual.get("sha256"), historical=hist)
    live_row: Dict[str, Any] = {
        "beam_id": beam_id,
        "complete": True,
        "mode": mode,
        "action": decision["action"],
        "call_provenance": decision["provenance"],
        "eligible": eligible,
        "gate_status": (elig_row.get("gate") or {}).get("status"),
        "visual": {"path": visual.get("path"), "sha256": visual.get("sha256"), "source": visual.get("source")},
        "called": False,
        "semantic_usable": False,
        "failure_category": None,
    }
    parsed = None
    extracted = None
    if decision["action"] == "BLOCK":
        live_row["failure_category"] = "VISUAL_NOT_READY"
        live_row["call_provenance"] = PROV_BLOCKED
    elif decision["action"] == "REUSE" and existing:
        live_row = dict(existing)
        live_row["call_provenance"] = decision["provenance"]
        live_row["action"] = "REUSE"
        parsed = existing.get("parsed")
        extracted = existing.get("extracted")
        live_row["semantic_usable"] = bool(existing.get("semantic_usable"))
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
            context_source=str(visual.get("source") or "QA30_FIFTH_SHARED_RENDER"),
            detail_source=str(visual.get("source") or "QA30_FIFTH_SHARED_RENDER"),
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
                "call_provenance": provenance_from_live(str(result.get("failure_category")), intended=decision["provenance"]),
            }
        )
        parsed = result.get("parsed")
        extracted = result.get("extracted")
        save_e2_row(out_root, live_row)

    vision_row = None
    if live_row.get("semantic_usable") and extracted:
        vision_row = {
            "usable": True,
            "source": "E2_LIVE" if live_row.get("called") else "E2_REUSED",
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
    calc["live"] = {k: v for k, v in live_row.items() if k not in ("parsed", "extracted", "audit")}
    calc["live_full"] = live_row
    if decision["action"] != "REUSE" and live_row.get("complete") and live_row.get("failure_category") != "LIVE_DISABLED":
        save_e2_row(out_root, live_row)
    return calc


def execute_all(
    *,
    v10: Path,
    out_root: Path,
    beam_ids: List[str],
    catalog: Dict[str, Any],
    eligibility: Dict[str, Any],
    mode: str,
    client_override: Optional[Callable] = None,
) -> List[Dict[str, Any]]:
    hist = historical_by_id(v10)
    rows = []
    completed = []
    elig_by = eligibility.get("by_id") or {}
    total = len(beam_ids)
    for i, bid in enumerate(beam_ids, start=1):
        calc = execute_one(
            v10=v10,
            out_root=out_root,
            beam_id=bid,
            model=catalog.get(bid) if isinstance(catalog.get(bid), dict) else None,
            catalog=catalog,
            elig_row=elig_by.get(bid) or {},
            mode=mode,
            hist=hist.get(bid),
            client_override=client_override,
        )
        rows.append(calc)
        completed.append(bid)
        write_checkpoint(out_root, beam_ids=beam_ids, completed_ids=completed, status="IN_PROGRESS")
        live = calc.get("live") or {}
        print(
            f"  [{i}/{total}] {bid} kind={calc.get('provenance_kind')} "
            f"prov={live.get('call_provenance')} usable={live.get('semantic_usable')}",
            flush=True,
        )
    rows.sort(key=lambda r: str(r.get("beam_id") or ""))
    write_checkpoint(out_root, beam_ids=beam_ids, completed_ids=completed, status="COMPLETE")
    return rows


__all__ = ["execute_all", "execute_one", "historical_by_id"]
