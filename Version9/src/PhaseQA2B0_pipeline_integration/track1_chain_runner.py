"""
QA.2B.0 — Track1 visual / ownership chain (existing orchestrators only).
MODEL_VERSION: 9.6.0

Order: T16 → T17 → T18 → T181 → T182 → T183 → T1831
Skips stages whose success artefacts already exist. Does not edit phase sources.

Beams with incomplete geometry envelopes (null extents) are excluded from the
chain so upstream null-extent data cannot abort later phases — integration only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

MODEL_VERSION = "9.6.0"


def _artefact_ok(run_root: Path, rel: str, *, directory_glob: Optional[str] = None) -> bool:
    path = Path(run_root) / "data" / "output" / rel
    if directory_glob:
        return path.is_dir() and any(path.glob(directory_glob))
    return path.is_file()


def envelope_has_numeric_extent(env: Dict[str, Any]) -> bool:
    ext = env.get("extent")
    if isinstance(ext, (list, tuple)) and len(ext) >= 4:
        return all(v is not None for v in ext[:4])
    vals = [env.get("xmin"), env.get("ymin"), env.get("xmax"), env.get("ymax")]
    return all(v is not None for v in vals)


def list_processable_beam_ids(run_root: Path) -> Tuple[List[str], List[str]]:
    """Return (processable_ids, skipped_null_extent_ids)."""
    path = (
        Path(run_root)
        / "data"
        / "output"
        / "PhaseT1_geometric_stirrup_evidence"
        / "geometry_envelopes.json"
    )
    if not path.exists():
        return [], []
    data = json.loads(path.read_text(encoding="utf-8"))
    ok: List[str] = []
    skip: List[str] = []
    for bid, env in sorted((data.get("by_beam") or {}).items()):
        if envelope_has_numeric_extent(env or {}):
            ok.append(str(bid))
        else:
            skip.append(str(bid))
    return ok, skip


def ensure_t1_envelopes(engine_root: Path, run_root: Path) -> Dict[str, Any]:
    """Re-run T1 if geometry_envelopes.json is missing (required by T16+)."""
    env_path = (
        Path(run_root)
        / "data"
        / "output"
        / "PhaseT1_geometric_stirrup_evidence"
        / "geometry_envelopes.json"
    )
    if env_path.exists():
        return {
            "stage": "T1",
            "skipped": True,
            "success": True,
            "reason": "geometry_envelopes_present",
        }
    print(f"[QA.2B.0] T1 geometry_envelopes missing — re-running T1 on {run_root.name}")
    from PhaseT1_geometric_stirrup_evidence.phase_t1_orchestrator import (
        PhaseT1Orchestrator,
    )

    result = PhaseT1Orchestrator(engine_root, run_root).run()
    ok = bool(result.get("success", result.get("soft_exit"))) and env_path.exists()
    return {
        "stage": "T1",
        "skipped": False,
        "success": ok,
        "error": None
        if ok
        else (result.get("error") or result.get("message") or "envelopes_missing_after_t1"),
        "t1_keys": sorted(result.keys())[:12],
    }


def _stage_specs(
    engine_root: Path,
    run_root: Path,
    beam_ids: Optional[Sequence[str]],
) -> List[Tuple[str, str, Optional[str], Callable[[], Dict[str, Any]]]]:
    ids = list(beam_ids) if beam_ids is not None else None

    def t16():
        from PhaseT16_entity_ownership.phase_t16_orchestrator import PhaseT16Orchestrator

        return PhaseT16Orchestrator(engine_root, run_root).run(
            write_overlays=False, beam_ids=ids
        )

    def t17():
        from PhaseT17_annotation_graph.phase_t17_orchestrator import PhaseT17Orchestrator

        return PhaseT17Orchestrator(engine_root, run_root).run(beam_ids=ids)

    def t18():
        from PhaseT18_beam_ownership.phase_t18_orchestrator import PhaseT18Orchestrator

        return PhaseT18Orchestrator(engine_root, run_root).run(beam_ids=ids)

    def t181():
        from PhaseT181_beam_render_validation.phase_t181_orchestrator import (
            PhaseT181Orchestrator,
        )

        return PhaseT181Orchestrator(engine_root, run_root).run(beam_ids=ids)

    def t182():
        from PhaseT182_adaptive_render_extent.phase_t182_orchestrator import (
            PhaseT182Orchestrator,
        )

        return PhaseT182Orchestrator(engine_root, run_root).run(beam_ids=ids)

    def t183():
        from PhaseT183_shared_engineering_ownership.phase_t183_orchestrator import (
            PhaseT183Orchestrator,
        )

        return PhaseT183Orchestrator(
            engine_root, run_root, enable_shared_ownership=True
        ).run(beam_ids=ids)

    def t1831():
        from PhaseT1831_shared_scope_dedup.phase_t1831_orchestrator import (
            PhaseT1831Orchestrator,
        )

        return PhaseT1831Orchestrator(engine_root, run_root).run()

    return [
        ("T1.6", "PhaseT16_entity_ownership/beam_entity_ownership.json", None, t16),
        ("T1.7", "PhaseT17_annotation_graph/AnnotationGraph.json", None, t17),
        ("T1.8", "PhaseT18_beam_ownership/BeamOwnership.json", None, t18),
        ("T1.8.1", "PhaseT181_render_validation/RenderedBeams", "*.png", t181),
        ("T1.8.2", "PhaseT182_adaptive_render_extent/RenderedBeams", "*.png", t182),
        (
            "T1.8.3",
            "PhaseT183_shared_engineering_ownership/MergedOwnership.json",
            None,
            t183,
        ),
        (
            "T1.8.3.1",
            "PhaseT1831_shared_scope_dedup/SharedAnnotationRegistry.json",
            None,
            t1831,
        ),
    ]


def run_track1_visual_chain(
    engine_root: Path,
    run_root: Path,
    *,
    force: bool = False,
    ensure_envelopes: bool = True,
    beam_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    engine_root = Path(engine_root)
    run_root = Path(run_root)
    stages: List[Dict[str, Any]] = []

    if ensure_envelopes:
        stages.append(ensure_t1_envelopes(engine_root, run_root))
        if not stages[-1].get("success"):
            return {
                "model_version": MODEL_VERSION,
                "run_root": str(run_root),
                "success": False,
                "stages": stages,
                "error": "T1 envelopes unavailable",
            }

    processable, skipped_null = list_processable_beam_ids(run_root)
    if beam_ids is not None:
        want = set(beam_ids)
        processable = [b for b in processable if b in want]
        skipped_null = [b for b in skipped_null if b in want]
    if skipped_null:
        print(
            f"[QA.2B.0] skipping null-extent beams (integration filter): {skipped_null}"
        )
    if not processable:
        return {
            "model_version": MODEL_VERSION,
            "run_root": str(run_root),
            "success": False,
            "stages": stages,
            "skipped_null_extent": skipped_null,
            "error": "no_processable_beams",
        }

    # If T18 artefact exists but is incomplete vs processable set, force re-run from T18
    own_path = (
        run_root / "data" / "output" / "PhaseT18_beam_ownership" / "BeamOwnership.json"
    )
    force_from_t18 = False
    if own_path.exists() and not force:
        try:
            own = json.loads(own_path.read_text(encoding="utf-8"))
            have = set((own.get("by_beam") or {}).keys())
            if not set(processable).issubset(have):
                force_from_t18 = True
                print(
                    "[QA.2B.0] BeamOwnership incomplete vs processable beams — "
                    "re-running from T1.8"
                )
        except Exception:  # noqa: BLE001
            force_from_t18 = True

    reached_t18 = False
    for stage_id, rel, dglob, fn in _stage_specs(engine_root, run_root, processable):
        if stage_id == "T1.8":
            reached_t18 = True
        must_run = force or (force_from_t18 and reached_t18)
        if not must_run and _artefact_ok(run_root, rel, directory_glob=dglob):
            print(f"[QA.2B.0] skip {stage_id} (artefact present)")
            stages.append(
                {
                    "stage": stage_id,
                    "skipped": True,
                    "success": True,
                    "reason": f"artefact_present:{rel}",
                }
            )
            continue
        print(f"[QA.2B.0] run {stage_id} on {run_root.name} ({len(processable)} beams)...")
        try:
            result = fn()
            ok = bool(result.get("success", True))
            stages.append(
                {
                    "stage": stage_id,
                    "skipped": False,
                    "success": ok,
                    "error": result.get("error"),
                }
            )
            if not ok:
                break
        except Exception as exc:  # noqa: BLE001
            stages.append(
                {
                    "stage": stage_id,
                    "skipped": False,
                    "success": False,
                    "error": str(exc),
                }
            )
            break

    ok = all(s.get("success") for s in stages)
    return {
        "model_version": MODEL_VERSION,
        "run_root": str(run_root),
        "success": ok,
        "stages": stages,
        "processable_beam_ids": processable,
        "skipped_null_extent": skipped_null,
    }
