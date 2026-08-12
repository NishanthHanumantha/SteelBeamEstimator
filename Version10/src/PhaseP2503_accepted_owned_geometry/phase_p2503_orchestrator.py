"""
P2.5.0.3 orchestrator — Accepted OWN TOP_BAR Evidence Packaging Fix.

Updates P2.5.0 evidence packages for focus beams and emits P2503 reports.
Does not modify T18 / R.3.1 / engineering calculations. No Claude.
"""
from __future__ import annotations

import hashlib
import json
import shutil
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
from PhaseP250_beam_evidence_crop_qa.crop_qa import evaluate_crop_qa  # noqa: E402
from PhaseP250_beam_evidence_crop_qa.evidence_pack import (  # noqa: E402
    build_beam_evidence_pack,
)
from PhaseP250_beam_evidence_crop_qa.owned_geometry import build_handle_index  # noqa: E402
from PhaseP250_beam_evidence_crop_qa.renderer import (  # noqa: E402
    _get_doc,
    render_engineering_crop,
    render_evidence_overlay,
)
from PhaseP250_beam_evidence_crop_qa.render_validation import (  # noqa: E402
    validate_owned_geometry_rendered,
)
from PhaseP2503_accepted_owned_geometry.config import (  # noqa: E402
    CLAUDE,
    ENGINEERING_CHANGES,
    FOCUS,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    SCOPE,
)
from PhaseP2503_accepted_owned_geometry.crop_bound_tests import (  # noqa: E402
    negative_positive_crop_test,
)
from PhaseP2503_accepted_owned_geometry.regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
)
from PhaseP2503_accepted_owned_geometry.report_builder import write_reports  # noqa: E402
from PhaseP2503_accepted_owned_geometry.unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fp(evidence: Dict[str, Any], qa: Dict[str, Any]) -> str:
    win = evidence.get("evidence_window") or {}
    return _stable_hash(
        {
            "beam_id": evidence.get("beam_id"),
            "crop_bounds": win.get("bbox"),
            "owned": [
                {
                    "id": o.get("ownership_id"),
                    "handle": o.get("source_handle"),
                    "bbox": o.get("bbox"),
                }
                for o in evidence.get("owned_geometry") or []
            ],
            "reinf": [r.get("reinforcement_id") for r in evidence.get("reinforcement") or []],
            "gates": qa.get("gates"),
        }
    )


def _process_beam(
    *,
    beam_id: str,
    bundle: Any,
    engine_root: Path,
    dxf_path: Path,
    handle_index: Dict[str, Any],
    beam_dir: Path,
    p250_beam_dir: Path,
) -> Dict[str, Any]:
    evidence = build_beam_evidence_pack(
        beam_id=beam_id,
        bundle=bundle,
        handle_index=handle_index,
    )
    extent_list = (evidence.get("evidence_window") or {}).get("bbox")
    eng: Dict[str, Any]
    ovl: Dict[str, Any]
    if not extent_list or len(extent_list) < 4:
        eng = {"success": False, "error": "missing_evidence_window"}
        ovl = {"success": False, "error": "missing_evidence_window"}
    else:
        extent = tuple(float(x) for x in extent_list[:4])
        eng_path = beam_dir / "engineering_crop.png"
        ovl_path = beam_dir / "evidence_overlay.png"
        eng = render_engineering_crop(
            engine_root=engine_root,
            dxf_path=dxf_path,
            extent=extent,  # type: ignore[arg-type]
            out_path=eng_path,
            owned_geometry=evidence.get("owned_geometry") or [],
        )
        if eng.get("success"):
            ovl = render_evidence_overlay(
                engineering_png=eng_path,
                evidence=evidence,
                out_path=ovl_path,
                extent=extent,  # type: ignore[arg-type]
            )
        else:
            ovl = {"success": False, "error": eng.get("error"), "path": str(ovl_path)}

    rv = {}
    if eng.get("success") and eng.get("path"):
        rv = validate_owned_geometry_rendered(
            engineering_png=Path(eng["path"]),
            evidence=evidence,
            paint_meta=eng.get("owned_geometry_painted") or [],
        )

    qa = evaluate_crop_qa(
        evidence=evidence,
        engineering_render=eng,
        overlay_render=ovl,
        render_validation=rv,
    )
    neg = negative_positive_crop_test(
        beam_id=beam_id,
        bundle=bundle,
        evidence=evidence,
        handle_index=handle_index,
    )
    evidence_out = dict(evidence)
    evidence_out["render"] = {"engineering": eng, "overlay": ovl}
    evidence_out["phase_p2503"] = True

    _dump(beam_dir / "evidence.json", evidence_out)
    _dump(beam_dir / "crop_qa.json", qa)
    _dump(beam_dir / "crop_bound_test.json", neg)

    # Preserve updated packages in P2.5.0 output tree
    p250_beam_dir.mkdir(parents=True, exist_ok=True)
    _dump(p250_beam_dir / "evidence.json", evidence_out)
    _dump(p250_beam_dir / "crop_qa.json", qa)
    if eng.get("success") and eng.get("path"):
        shutil.copy2(eng["path"], p250_beam_dir / "engineering_crop.png")
    if ovl.get("success") and ovl.get("path"):
        shutil.copy2(ovl["path"], p250_beam_dir / "evidence_overlay.png")

    return {
        "beam_id": beam_id,
        "evidence": evidence_out,
        "qa": qa,
        "crop_bound_test": neg,
        "engineering_crop": eng.get("path"),
        "evidence_overlay": ovl.get("path"),
        "evidence_hash": _fp(evidence, qa),
    }


def _acceptance(beams: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "pass": ok, "detail": detail})

    for bid, foc in FOCUS.items():
        b = beams.get(bid) or {}
        ev = b.get("evidence") or {}
        neg = b.get("crop_bound_test") or {}
        qa = b.get("qa") or {}
        owned = ev.get("owned_geometry") or []
        og = next((o for o in owned if o.get("ownership_id") == foc["own_entity"]), None)
        add(f"{bid}_own_packaged", og is not None, str(og and og.get("ownership_id")))
        add(
            f"{bid}_dxf_lwpolyline",
            bool(og and og.get("dxf_resolved") and og.get("entity_type") == "LWPOLYLINE"),
            str(og and og.get("entity_type")),
        )
        add(
            f"{bid}_handle",
            bool(og and og.get("source_handle") == foc["own_handle"]),
            str(og and og.get("source_handle")),
        )
        add(
            f"{bid}_ann_linked",
            bool(
                og
                and og.get("annotation_id") == foc["ann_4y25"]
                and str(foc.get("annotation_text") or "4-Y25")
                in str(og.get("annotation_text") or "").replace(" ", "")
            ),
            f"ann={og.get('annotation_id') if og else None} text={og.get('annotation_text') if og else None}",
        )
        add(f"{bid}_leader", bool(og and og.get("leader_id") == foc["leader"]))
        add(f"{bid}_own_in_crop", bool(neg.get("own_inside_production_crop")))
        add(
            f"{bid}_rejected_excluded",
            not neg.get("rejected_bars_in_reinforcement_list"),
            str(neg.get("rejected_bars_in_reinforcement_list")),
        )
        add(f"{bid}_not_extreme", not neg.get("extreme_expansion_returned"))
        gates = qa.get("gates") or {}
        for g in (
            "OWN_TOP_BAR_PRESENT",
            "OWN_TOP_BAR_INSIDE_CROP",
            "OWN_TOP_BAR_SOURCE_VALID",
            "OWN_TOP_BAR_LINKED_TO_ACCEPTED_CHAIN",
            "REJECTED_PHYSICAL_BAR_EXCLUDED",
            "CROP_NOT_EXTREME",
        ):
            add(f"{bid}_{g}", gates.get(g) == "PASS", str(gates.get(g)))

    ok = all(c["pass"] for c in checks)
    return {"pass": ok, "checks": checks}


def run_phase_p2503(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    beams_root = out_root / "beams"
    beams_root.mkdir(parents=True, exist_ok=True)
    p250_root = v10 / "data" / "output" / "PhaseP250_beam_evidence_crop_qa" / "beams"

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE}")
    _log(f"  MODE: {MODE}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES}")
    _log(f"  CLAUDE: {CLAUDE}")
    _log(f"  output: {out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        _log("  Running unit tests...")
        unit = run_unit_tests()
        _dump(out_root / "diagnostics" / "unit_tests.json", unit)
        _log(f"  Unit tests: {unit['passed']}/{unit['total']}")
        if not unit.get("success"):
            return {"success": False, "unit_tests": unit, "output_root": str(out_root)}

    bundle = load_fourth_set_bundle(v10)
    if not bundle.reinforcement_dxf or not Path(bundle.reinforcement_dxf).exists():
        raise FileNotFoundError("Fourth Set reinforcement DXF not found")
    dxf_path = Path(bundle.reinforcement_dxf)
    doc = _get_doc(dxf_path)
    handle_index = build_handle_index(doc.modelspace())
    _log(f"  DXF handle index size: {len(handle_index)}")

    fp_paths = fingerprint_paths(v10, bundle.paths)
    fp_before = capture_fingerprints(fp_paths)

    beams: Dict[str, Dict[str, Any]] = {}
    hashes1: Dict[str, str] = {}
    for bid in FOCUS:
        _log(f"  Processing {bid}...")
        result = _process_beam(
            beam_id=bid,
            bundle=bundle,
            engine_root=v10,
            dxf_path=dxf_path,
            handle_index=handle_index,
            beam_dir=beams_root / bid,
            p250_beam_dir=p250_root / bid,
        )
        beams[bid] = result
        hashes1[bid] = result["evidence_hash"]

    # Determinism pass 2 (rebuild evidence only; re-render for byte-stable crops)
    _log("  Determinism pass 2...")
    hashes2: Dict[str, str] = {}
    det_mismatches: List[str] = []
    for bid in FOCUS:
        result2 = _process_beam(
            beam_id=bid,
            bundle=bundle,
            engine_root=v10,
            dxf_path=dxf_path,
            handle_index=handle_index,
            beam_dir=beams_root / bid,
            p250_beam_dir=p250_root / bid,
        )
        hashes2[bid] = result2["evidence_hash"]
        beams[bid] = result2
        if hashes1[bid] != hashes2[bid]:
            det_mismatches.append(bid)

    determinism = {
        "determinism_status": "PASS" if not det_mismatches else "FAIL",
        "pass1": hashes1,
        "pass2": hashes2,
        "mismatches": det_mismatches,
    }
    _dump(out_root / "diagnostics" / "determinism.json", determinism)

    fp_after = capture_fingerprints(fp_paths)
    regression = compare_fingerprints(fp_before, fp_after)
    # P250 beam evidence files for focus beams are expected to change — strip those
    # from "changed" if present; production engineering artefacts must be unchanged.
    changed = list(regression.get("changed") or [])
    expected_change_prefixes = (
        "p250_summary",  # may update if full P250 re-run; ignore soft
    )
    soft = [c for c in changed if c in expected_change_prefixes]
    hard = [c for c in changed if c not in expected_change_prefixes]
    regression = {
        **regression,
        "changed": hard,
        "soft_changed": soft,
        "unchanged": len(hard) == 0,
    }

    acceptance = _acceptance(beams)
    vision_ready = (
        acceptance["pass"]
        and determinism["determinism_status"] == "PASS"
        and regression.get("unchanged")
        and unit.get("success")
    )
    decision = "READY_FOR_P2.5.1" if vision_ready else "BLOCKED"

    meta = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "mode": MODE,
        "engineering_changes": ENGINEERING_CHANGES,
        "claude": CLAUDE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dxf": str(dxf_path),
    }
    write_reports(
        out_root=out_root,
        meta=meta,
        beams=beams,
        focus=FOCUS,
        regression=regression,
        determinism=determinism,
        unit_tests=unit,
        decision=decision,
    )
    _dump(out_root / "diagnostics" / "acceptance.json", acceptance)

    _log(f"  acceptance_pass={acceptance['pass']}")
    _log(f"  decision={decision}")
    _log(f"  determinism={determinism['determinism_status']}")
    _log(f"  regression_unchanged={regression.get('unchanged')}")

    return {
        "success": bool(acceptance["pass"] and determinism["determinism_status"] == "PASS"),
        "decision": decision,
        "meta": meta,
        "acceptance": acceptance,
        "determinism": determinism,
        "regression": regression,
        "unit_tests": unit,
        "output_root": str(out_root),
        "beams": {
            k: {
                "qa": v.get("qa"),
                "crop_bound_test": v.get("crop_bound_test"),
                "owned_geometry": (v.get("evidence") or {}).get("owned_geometry"),
            }
            for k, v in beams.items()
        },
    }
