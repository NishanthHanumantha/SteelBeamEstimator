"""
Phase T1.8 orchestrator — Beam Ownership Envelope Resolver.
MODEL_VERSION: 9.5.0
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .ownership_filter import build_scoped_annotations, filter_beam_ownership
from .ownership_validator import validate_beam_ownership
from .qa_diagnostics import write_qa_report

MODEL_VERSION = "9.5.0"
PHASE_ID = "T1.8"
_OUT_NAME = "PhaseT18_beam_ownership"


class PhaseT18Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        run_root: Path,
        output_root: Optional[Path] = None,
    ):
        self.engine_root = Path(engine_root)
        self.run_root = Path(run_root)
        self.output_root = (
            Path(output_root) if output_root else self.run_root / "data" / "output"
        )
        self.out_dir = self.output_root / _OUT_NAME

    def run(self, *, beam_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)

        graph_path = (
            self.output_root / "PhaseT17_annotation_graph" / "AnnotationGraph.json"
        )
        if not graph_path.exists():
            return {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "AnnotationGraph.json missing",
            }
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        envelopes = self._load_envelopes()
        annotations = self._load_annotations()
        bars = self._load_physical_bars()
        inv_ys = self._load_inventory_bar_ys()
        inv_by_h = self._load_inventory_index()

        ids = list(beam_ids) if beam_ids else sorted(envelopes.keys())
        by_beam_own: Dict[str, Any] = {}
        by_beam_scoped: Dict[str, Any] = {}
        diagnostics: Dict[str, Any] = {}
        validations: List[Dict[str, Any]] = []

        for bid in ids:
            if bid not in envelopes:
                continue
            print(f"[T1.8] Ownership filter {bid}...")
            own = filter_beam_ownership(
                bid,
                graph,
                envelopes[bid],
                [b for b in bars if str(b.get("beam_id")) == bid],
                annotations.get(bid) or [],
                inventory_bar_ys=inv_ys.get(bid),
                inventory_by_handle=inv_by_h,
            )
            scoped = build_scoped_annotations(bid, graph, own)
            val = validate_beam_ownership(own)
            by_beam_own[bid] = own
            by_beam_scoped[bid] = scoped
            diagnostics[bid] = {
                "envelope": own.get("envelope"),
                "stats": own.get("stats"),
                "validation": val,
                "rejected_chains": own.get("rejected_chains"),
                "accepted_chains": own.get("accepted_chains"),
            }
            validations.append({"ownership": own, "validation": val})
            print(
                f"  {bid} -> {val['validation']} "
                f"acc={own['stats']['accepted_annotation_count']} "
                f"rej={own['stats']['rejected_annotation_count']} "
                f"leak={val['leakage_count']}"
            )

        ownership_doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "beam_count": len(by_beam_own),
            "by_beam": by_beam_own,
        }
        scoped_doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": ownership_doc["generated_at"],
            "by_beam": by_beam_scoped,
            "note": "ONLY accepted graph nodes — consume instead of full AnnotationGraph for beam-scoped rendering",
        }
        diag_doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": ownership_doc["generated_at"],
            "by_beam": diagnostics,
        }

        (self.out_dir / "BeamOwnership.json").write_text(
            json.dumps(ownership_doc, indent=2), encoding="utf-8"
        )
        (self.out_dir / "BeamScopedAnnotations.json").write_text(
            json.dumps(scoped_doc, indent=2), encoding="utf-8"
        )
        (self.out_dir / "OwnershipDiagnostics.json").write_text(
            json.dumps(diag_doc, indent=2), encoding="utf-8"
        )

        write_qa_report(
            self.out_dir / "T18_BEAM_OWNERSHIP_QA_REPORT.md",
            rows=validations,
            generated_at=ownership_doc["generated_at"],
            out_dir=self.out_dir,
        )

        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": True,
            "generated_at": ownership_doc["generated_at"],
            "out_dir": str(self.out_dir),
            "beam_count": len(by_beam_own),
            "pass_count": sum(
                1 for v in validations if v["validation"]["validation"] == "PASS"
            ),
            "fail_count": sum(
                1 for v in validations if v["validation"]["validation"] != "PASS"
            ),
        }
        (self.out_dir / "t18_run_summary.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result

    def _load_json(self, *parts: str) -> Any:
        path = self.output_root.joinpath(*parts)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_envelopes(self) -> Dict[str, Dict[str, Any]]:
        data = self._load_json(
            "PhaseT1_geometric_stirrup_evidence", "geometry_envelopes.json"
        )
        if not data:
            alt = (
                self.engine_root
                / "data"
                / "output"
                / "Track1_geometric_evidence"
                / "geometry_envelopes_Set1_benchmark.json"
            )
            if alt.exists():
                data = json.loads(alt.read_text(encoding="utf-8"))
        if not data:
            return {}
        return {str(k): v for k, v in (data.get("by_beam") or {}).items()}

    def _load_annotations(self) -> Dict[str, List[Dict[str, Any]]]:
        data = self._load_json(
            "PhaseR.1_generalized_reinforcement_discovery",
            "reinforcement_annotations.json",
        )
        if not data:
            return {}
        return {str(k): list(v or []) for k, v in (data.get("by_beam") or {}).items()}

    def _load_physical_bars(self) -> List[Dict[str, Any]]:
        data = self._load_json(
            "PhaseR3.1_engineering_relationship_engine", "PhysicalBars.json"
        )
        if not data:
            return []
        return [b for b in (data.get("bars") or []) if isinstance(b, dict)]

    def _load_inventory_index(self) -> Dict[str, Dict[str, Any]]:
        inv = self._load_json("PhaseT16_entity_ownership", "entity_inventory.json")
        if not inv:
            return {}
        return {
            str(e["entity_handle"]).upper(): e
            for e in (inv.get("entities") or [])
            if e.get("entity_handle")
        }

    def _load_inventory_bar_ys(self) -> Dict[str, List[float]]:
        """Optional: T1.6 HIGH longitudinal line Ys per beam."""
        own = self._load_json(
            "PhaseT16_entity_ownership", "beam_entity_ownership.json"
        )
        by_h = self._load_inventory_index()
        if not own or not by_h:
            return {}
        out: Dict[str, List[float]] = {}
        for bid, rows in (own.get("by_beam") or {}).items():
            ys = []
            for r in rows or []:
                if r.get("ownership") != "HIGH":
                    continue
                if r.get("type") not in ("LINE", "LWPOLYLINE"):
                    continue
                if str(r.get("role") or "") not in (
                    "TOP_BAR",
                    "BOTTOM_BAR",
                    "LONGITUDINAL_BAR",
                ):
                    continue
                ent = by_h.get(str(r.get("handle") or "").upper()) or {}
                sp, ep = ent.get("start_point"), ent.get("end_point")
                if sp and ep:
                    ys.append(0.5 * (float(sp[1]) + float(ep[1])))
            out[str(bid)] = ys
        return out
