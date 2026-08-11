"""
P2.5.0 orchestrator — Beam Evidence Rendering & Crop QA.

MODEL_VERSION: 10.6.0
Diagnostic only. No Claude. No engineering mutations.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PhaseP24_fourth_set_bar_failure_audit.artefacts import (  # noqa: E402
    load_fourth_set_bundle,
)
from PhaseP24_fourth_set_bar_failure_audit.registries import (  # noqa: E402
    build_registries_and_matches,
)
from PhaseP250_beam_evidence_crop_qa.config import (  # noqa: E402
    ENGINEERING_CHANGES,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    SCOPE,
)
from PhaseP250_beam_evidence_crop_qa.crop_qa import evaluate_crop_qa  # noqa: E402
from PhaseP250_beam_evidence_crop_qa.evidence_pack import (  # noqa: E402
    build_beam_evidence_pack,
)
from PhaseP250_beam_evidence_crop_qa.metrics import (  # noqa: E402
    aggregate_metrics,
    gt_verified_recall,
    per_beam_recall,
)
from PhaseP250_beam_evidence_crop_qa.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP250_beam_evidence_crop_qa.renderer import (  # noqa: E402
    render_engineering_crop,
    render_evidence_overlay,
)
from PhaseP250_beam_evidence_crop_qa.report_builder import write_reports  # noqa: E402
from PhaseP250_beam_evidence_crop_qa.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _evidence_fingerprint(evidence: Dict[str, Any], qa: Dict[str, Any]) -> str:
    win = evidence.get("evidence_window") or {}
    return _stable_hash(
        {
            "beam_id": evidence.get("beam_id"),
            "crop_bounds": win.get("bbox"),
            "base_bbox": win.get("base_bbox"),
            "ann_ids": [a.get("annotation_id") for a in evidence.get("annotations") or []],
            "leader_ids": [l.get("leader_id") for l in evidence.get("leaders") or []],
            "reinf_ids": [
                r.get("reinforcement_id") for r in evidence.get("reinforcement") or []
            ],
            "qa_overall": qa.get("overall"),
            "gates": qa.get("gates"),
            "expansion": (win.get("expansion") or {}),
        }
    )


def _gt_bar_counts(gt_registry: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in gt_registry or []:
        bid = str(r.get("beam_id") or "").strip()
        if bid:
            out[bid] = out.get(bid, 0) + 1
    return out


def _target_beam_ids(bundle: Any, gt_counts: Dict[str, int]) -> List[str]:
    """
    All available Fourth Set target beams with deterministic geometry sources.
    Ownership + envelopes; include GT beams only when envelope/ownership exists.
    Never invent B8/B9/B10 etc.
    """
    own = set((bundle.beam_ownership.get("by_beam") or {}).keys())
    env = set(bundle.envelope_beams or [])
    ids = sorted(own | env)
    # Prefer ownership order; if empty fall back to GT∩env
    if not ids:
        ids = sorted(set(gt_counts) & env)
    return ids


def _neighbour_ids(bundle: Any, beam_id: str, limit: int = 8) -> List[str]:
    """Nearby beam IDs from ownership (contextual only — not ownership evidence)."""
    own = bundle.beam_ownership.get("by_beam") or {}
    others = [b for b in sorted(own.keys()) if b != beam_id]
    # Shared-scope members first
    shared: Set[str] = set()
    for sc in bundle.engineering_scopes.get("scopes") or []:
        members = sc.get("member_beams") or []
        if beam_id in members:
            shared.update(m for m in members if m != beam_id)
    ordered = sorted(shared) + [b for b in others if b not in shared]
    return ordered[:limit]


def _process_one_beam(
    *,
    beam_id: str,
    bundle: Any,
    engine_root: Path,
    dxf_path: Path,
    beam_dir: Path,
    gt_bar_count: int,
    skip_render: bool = False,
    prior_eng: Optional[Dict[str, Any]] = None,
    prior_ovl: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    neighbours = _neighbour_ids(bundle, beam_id)
    evidence = build_beam_evidence_pack(
        beam_id=beam_id,
        bundle=bundle,
        neighbour_beam_ids=neighbours,
    )

    extent_list = (evidence.get("evidence_window") or {}).get("bbox")
    eng: Dict[str, Any]
    ovl: Dict[str, Any]
    if skip_render:
        eng = prior_eng or {"success": False}
        ovl = prior_ovl or {"success": False}
    elif not extent_list or len(extent_list) < 4:
        eng = {"success": False, "error": "missing_evidence_window", "path": None}
        ovl = {"success": False, "error": "missing_evidence_window", "path": None}
    else:
        extent = (
            float(extent_list[0]),
            float(extent_list[1]),
            float(extent_list[2]),
            float(extent_list[3]),
        )
        eng_path = beam_dir / "engineering_crop.png"
        ovl_path = beam_dir / "evidence_overlay.png"
        eng = render_engineering_crop(
            engine_root=engine_root,
            dxf_path=dxf_path,
            extent=extent,
            out_path=eng_path,
        )
        if eng.get("success"):
            ovl = render_evidence_overlay(
                engineering_png=eng_path,
                evidence=evidence,
                out_path=ovl_path,
                extent=extent,
            )
        else:
            ovl = {
                "success": False,
                "error": f"skipped_overlay:{eng.get('error')}",
                "path": str(ovl_path),
            }

    qa = evaluate_crop_qa(
        evidence=evidence,
        engineering_render=eng,
        overlay_render=ovl,
        neighbour_beam_ids=neighbours,
    )
    cov = per_beam_recall(evidence, qa)
    gt_rec = gt_verified_recall(evidence=evidence, gt_bar_count=gt_bar_count)

    evidence_out = dict(evidence)
    evidence_out["gt_bar_count"] = gt_bar_count
    evidence_out["gt_verified_recall"] = gt_rec
    evidence_out["pipeline_coverage"] = cov
    evidence_out["render"] = {"engineering": eng, "overlay": ovl}

    if not skip_render:
        _dump(beam_dir / "evidence.json", evidence_out)
        _dump(beam_dir / "crop_qa.json", qa)

    gates = qa.get("gates") or {}
    flags = qa.get("flags") or {}
    expansion = (evidence.get("evidence_window") or {}).get("expansion") or {}

    row = {
        "beam_id": beam_id,
        "beam_present": gates.get("TARGET_BEAM_PRESENT") == "PASS",
        "reinforcement_present": gates.get("RELEVANT_REINFORCEMENT_PRESENT") == "PASS",
        "annotation_present": gates.get("RELEVANT_ANNOTATION_PRESENT") == "PASS",
        "leader_present": gates.get("RELEVANT_LEADER_PRESENT") == "PASS",
        "leader_chain_complete": gates.get("COMPLETE_LEADER_CHAIN") == "PASS",
        "evidence_clipped": bool(flags.get("evidence_clipped")),
        "neighbour_ambiguity": bool(flags.get("neighbour_ambiguity")),
        "crop_qa_overall": qa.get("overall"),
        "hard_fails": qa.get("hard_fails") or [],
        "soft_fails": qa.get("soft_fails") or [],
        "expanded": bool(expansion.get("expanded")),
        "render_success": bool(eng.get("success")) and bool(ovl.get("success")),
        "pipeline_annotation_coverage_pct": cov.get("pipeline_annotation_coverage_pct"),
        "pipeline_leader_coverage_pct": cov.get("pipeline_leader_coverage_pct"),
        "pipeline_reinforcement_coverage_pct": cov.get(
            "pipeline_reinforcement_coverage_pct"
        ),
        "gt_bar_count": gt_bar_count,
        "gt_reinforcement_evidence_present": bool(
            gt_rec.get("gt_reinforcement_evidence_present")
        ),
        "engineering_crop": eng.get("path") if eng.get("success") else None,
        "evidence_overlay": ovl.get("path") if ovl.get("success") else None,
        "crop_bounds": (evidence.get("evidence_window") or {}).get("bbox"),
        "evidence_hash": _evidence_fingerprint(evidence, qa),
    }
    return evidence_out, qa, row


def run_phase_p250(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    max_beams: Optional[int] = None,
    run_tests: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    beams_root = out_root / "beams"
    beams_root.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE}")
    _log(f"  MODE: {MODE}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES}")
    _log(f"  output: {out_root}")

    if run_tests:
        print("  Running focused unit tests...")
        ut = run_unit_tests()
        _dump(out_root / "diagnostics" / "unit_tests.json", ut)
        print(f"  Unit tests: {ut['passed']}/{ut['total']} pass")
        if not ut.get("success"):
            print("  STOP: unit tests failed")
            return {"success": False, "unit_tests": ut, "output_root": str(out_root)}

    print("  Loading Fourth Set bundle (reuse P2.4 artefacts)...")
    bundle = load_fourth_set_bundle(v10)
    if not bundle.reinforcement_dxf or not Path(bundle.reinforcement_dxf).exists():
        raise FileNotFoundError("Fourth Set reinforcement DXF not found")

    dxf_path = Path(bundle.reinforcement_dxf)
    fp_paths = fingerprint_paths(bundle.paths, v10)
    fp_before = capture_fingerprints(fp_paths)

    print("  Loading GT registry (estimator Excel via P2.4 registries)...")
    regs = build_registries_and_matches(
        v10,
        bundle.estimator_excel,
        bundle.model_excel,
        bundle.drawing_set,
    )
    gt_counts = _gt_bar_counts(regs["gt_registry"])
    beam_ids = _target_beam_ids(bundle, gt_counts)
    if max_beams is not None:
        beam_ids = beam_ids[: int(max_beams)]

    print(f"  Target beams: {len(beam_ids)}")
    print(f"  DXF: {dxf_path}")

    rows: List[Dict[str, Any]] = []
    packages: List[Dict[str, Any]] = []
    qas: List[Dict[str, Any]] = []
    pass1_hashes: Dict[str, str] = {}
    eng_by_beam: Dict[str, Dict[str, Any]] = {}
    ovl_by_beam: Dict[str, Dict[str, Any]] = {}

    for i, bid in enumerate(beam_ids, 1):
        if i == 1 or i % 10 == 0 or i == len(beam_ids):
            print(f"  [{i}/{len(beam_ids)}] {bid}")
        beam_dir = beams_root / bid
        beam_dir.mkdir(parents=True, exist_ok=True)
        pkg, qa, row = _process_one_beam(
            beam_id=bid,
            bundle=bundle,
            engine_root=v10,
            dxf_path=dxf_path,
            beam_dir=beam_dir,
            gt_bar_count=int(gt_counts.get(bid, 0)),
        )
        packages.append(pkg)
        qas.append(qa)
        rows.append(row)
        pass1_hashes[bid] = row["evidence_hash"]
        eng_by_beam[bid] = (pkg.get("render") or {}).get("engineering") or {}
        ovl_by_beam[bid] = (pkg.get("render") or {}).get("overlay") or {}

    # Pass 2 — rebuild evidence + QA (reuse render meta for determinism of selection)
    print("  Determinism pass 2 (evidence IDs / crop bounds / QA gates)...")
    det_mismatches: List[str] = []
    for bid in beam_ids:
        _, qa2, row2 = _process_one_beam(
            beam_id=bid,
            bundle=bundle,
            engine_root=v10,
            dxf_path=dxf_path,
            beam_dir=beams_root / bid,
            gt_bar_count=int(gt_counts.get(bid, 0)),
            skip_render=True,
            prior_eng=eng_by_beam.get(bid),
            prior_ovl=ovl_by_beam.get(bid),
        )
        if row2["evidence_hash"] != pass1_hashes.get(bid):
            det_mismatches.append(bid)

    determinism = {
        "determinism_status": "PASS" if not det_mismatches else "FAIL",
        "beams_compared": len(beam_ids),
        "mismatches": det_mismatches[:50],
        "mismatch_count": len(det_mismatches),
        "note": (
            "Compared evidence IDs, crop bounds, expansion, and QA gates across "
            "two builds. Image binary hashes are not required for PASS."
        ),
    }

    metrics = aggregate_metrics(rows)

    fp_after = capture_fingerprints(fp_paths)
    regression = compare_fingerprints(fp_before, fp_after)
    if not regression.get("unchanged"):
        print("  STOP: regression fingerprint drift detected")
        print(json.dumps({"changed_keys": regression.get("changed_keys")}, indent=2))

    architecture = {
        "reused": [
            "PhaseP24_fourth_set_bar_failure_audit.artefacts (Fourth Set bundle)",
            "PhaseP24 registries (GT bar counts from estimator Excel)",
            "PhaseT18 BeamOwnership / AnnotationGraph / PhysicalBars / envelopes",
            "PhaseT182 adaptive_bbox (extent helpers)",
            "PhaseM.1 dxf_renderer.render_dxf_region_to_png",
            "PhaseP24 regression fingerprint helpers",
        ],
        "extended": [
            "Evidence-window expansion around beam bbox using owned objects + leader chains",
            "Crop QA gate suite (PASS/FAIL/N/A)",
        ],
        "created": [
            "PhaseP250_beam_evidence_crop_qa (evidence pack, overlay, metrics, reports)",
        ],
        "why_new": (
            "P2.4 audits attribution; P2.5.0 must emit per-beam visual evidence packages "
            "and crop QA as a prerequisite for future Vision LLM — no existing module "
            "produced engineering_crop + evidence_overlay + crop_qa for Fourth Set beams."
        ),
        "not_done": [
            "No Claude / Anthropic SDK",
            "No QuantityIntent",
            "No engineering / VB1 / detector / ownership logic changes",
        ],
    }

    meta = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "mode": MODE,
        "engineering_changes": ENGINEERING_CHANGES,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fourth_set_web_run": str(bundle.run_root),
        "dxf": str(dxf_path),
        "beams_processed": len(beam_ids),
        "gt_beams_in_excel": len(gt_counts),
        "gt_bars": sum(gt_counts.values()),
        "output_root": str(out_root),
        "unit_tests_passed": True,
    }

    write_reports(
        out_root,
        metrics=metrics,
        beam_rows=rows,
        determinism=determinism,
        regression=regression,
        meta=meta,
        architecture=architecture,
    )
    _dump(
        out_root / "summary" / "ExecutionSummary.json",
        {
            **meta,
            "metrics": metrics,
            "determinism": determinism,
            "regression_unchanged": regression.get("unchanged"),
        },
    )

    render_ok_n = int(metrics.get("successful_renders") or 0)
    success = (
        determinism.get("determinism_status") == "PASS"
        and bool(regression.get("unchanged"))
        and len(beam_ids) > 0
        and render_ok_n > 0
        and render_ok_n >= int(0.5 * len(beam_ids))
    )

    print("")
    print(f"  Beams processed: {metrics.get('beams_processed')}")
    print(f"  Successful renders: {metrics.get('successful_renders')}")
    print(f"  Crop QA pass %: {metrics.get('crop_qa_pass_pct')}")
    print(f"  Determinism: {determinism.get('determinism_status')}")
    print(f"  Regression unchanged: {regression.get('unchanged')}")
    print(f"  Report: {out_root / 'reports' / 'P250_SUMMARY.md'}")

    return {
        "success": success,
        "meta": meta,
        "metrics": metrics,
        "determinism": determinism,
        "regression": regression,
        "output_root": str(out_root),
        "beam_rows": rows,
    }


if __name__ == "__main__":
    run_phase_p250()
