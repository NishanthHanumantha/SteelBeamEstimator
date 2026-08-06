"""
Phase T1.7 orchestrator — Annotation Graph Resolver.
MODEL_VERSION: 9.4.0
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .graph_builder import build_annotation_graph
from .graph_models import AnnotationGraph, MODEL_VERSION, PHASE_ID
from .qa_diagnostics import diagnose_graph

_OUT_NAME = "PhaseT17_annotation_graph"


class PhaseT17Orchestrator:
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

    def run(
        self,
        *,
        beam_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)

        envelopes = self._load_envelopes()
        annotations = self._load_annotations()
        leaders = self._load_leaders()
        bars = self._load_physical_bars()
        ownership = self._load_ownership()
        relationships = self._load_r31_relationships()
        eso = self._load_eso()
        arrows = self._load_arrows()
        inventory = self._load_inventory_index()
        supports = self._load_supports()

        ids = list(beam_ids) if beam_ids else sorted(
            set(envelopes.keys()) | set(annotations.keys())
        )
        ids = [b for b in ids if b in envelopes or b in annotations]

        print(f"[T1.7] Building AnnotationGraph for {len(ids)} beams...")
        graph = build_annotation_graph(
            beam_ids=ids,
            envelopes=envelopes,
            annotations_by_beam=annotations,
            leaders=leaders,
            physical_bars=bars,
            ownership_by_beam=ownership,
            r31_relationships=relationships,
            eso_by_ann=eso,
            arrow_inventory=arrows,
            supports_by_beam=supports,
            inventory_by_handle=inventory,
        )

        payload = graph.to_dict()
        payload["generated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        graph_path = self.out_dir / "AnnotationGraph.json"
        graph_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        # Compact per-beam view for QA readability
        compact = self._compact_by_beam(graph, ids)
        (self.out_dir / "annotation_graph_by_beam.json").write_text(
            json.dumps(compact, indent=2), encoding="utf-8"
        )

        qa = diagnose_graph(graph, ids)
        (self.out_dir / "graph_qa_diagnostics.json").write_text(
            json.dumps(qa, indent=2), encoding="utf-8"
        )

        # API smoke snapshot
        api_snap = {}
        for bid in ids:
            api_snap[bid] = {
                "annotations": [
                    (n.get("attributes") or {}).get("clean_text")
                    for n in graph.get_beam_annotations(bid)
                    if n.get("type") == "Annotation"
                ],
                "physical_bars": [n["id"] for n in graph.get_physical_bars(bid)],
                "semantics": [
                    {
                        "id": n["id"],
                        "type": n["type"],
                        "meaning": (n.get("attributes") or {}).get(
                            "engineering_meaning"
                        ),
                        "text": (n.get("attributes") or {}).get("raw_text"),
                    }
                    for n in graph.get_semantic_annotations(bid)
                ],
                "render_entity_count": len(graph.get_render_entities(bid)),
                "leaders": [n["id"] for n in graph.get_leaders(bid)],
            }
        (self.out_dir / "graph_api_snapshot.json").write_text(
            json.dumps(api_snap, indent=2), encoding="utf-8"
        )

        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": True,
            "generated_at": payload["generated_at"],
            "out_dir": str(self.out_dir),
            "beam_count": len(ids),
            "node_count": payload["node_count"],
            "edge_count": payload["edge_count"],
            "qa_totals": qa.get("totals"),
        }
        (self.out_dir / "t17_run_summary.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result

    @staticmethod
    def _compact_by_beam(
        graph: AnnotationGraph, beam_ids: Sequence[str]
    ) -> Dict[str, Any]:
        out = {}
        for bid in beam_ids:
            anns = []
            for a in graph.get_beam_annotations(bid):
                if a.get("type") != "Annotation":
                    continue
                # Find semantic + leader links
                sem = None
                leaders = []
                bars = []
                for rel in a.get("relationships") or []:
                    other = graph.nodes.get(rel["other_id"])
                    if not other:
                        continue
                    if rel["type"] == "INTERPRETS" and rel["direction"] == "in":
                        sem = {
                            "id": other["id"],
                            "type": other["type"],
                            "meaning": (other.get("attributes") or {}).get(
                                "engineering_meaning"
                            ),
                        }
                    if rel["type"] == "ATTACHED_TO" and rel["direction"] == "out":
                        leaders.append(other["id"])
                    if rel["type"] == "DESCRIBES" and rel["direction"] == "out":
                        if other.get("type") in ("PhysicalBar", "OwnedEntity"):
                            bars.append(other["id"])
                anns.append(
                    {
                        "id": a["id"],
                        "text": (a.get("attributes") or {}).get("clean_text"),
                        "semantic": sem,
                        "leaders": leaders,
                        "describes": bars,
                    }
                )
            out[bid] = {
                "beam_id": bid,
                "physical_bars": [
                    {
                        "id": b["id"],
                        "placement": (b.get("attributes") or {}).get(
                            "vertical_placement"
                        ),
                        "y": (b.get("attributes") or {}).get("y_position"),
                        "synthetic": (b.get("attributes") or {}).get("synthetic"),
                    }
                    for b in graph.get_physical_bars(bid)
                ],
                "leaders": [L["id"] for L in graph.get_leaders(bid)],
                "annotations": anns,
                "render_entities": graph.get_render_entities(bid)[:50],
            }
        return {"model_version": MODEL_VERSION, "by_beam": out}

    # ---- loaders ----------------------------------------------------------

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

    def _load_leaders(self) -> List[Dict[str, Any]]:
        data = self._load_json(
            "PhaseR3.1_engineering_relationship_engine", "LeaderInventory.json"
        )
        if not data:
            return []
        leaders = data.get("leaders") or []
        return [L for L in leaders if isinstance(L, dict)]

    def _load_physical_bars(self) -> List[Dict[str, Any]]:
        data = self._load_json(
            "PhaseR3.1_engineering_relationship_engine", "PhysicalBars.json"
        )
        if not data:
            return []
        return [b for b in (data.get("bars") or []) if isinstance(b, dict)]

    def _load_ownership(self) -> Dict[str, List[Dict[str, Any]]]:
        data = self._load_json(
            "PhaseT16_entity_ownership", "beam_entity_ownership.json"
        )
        if not data:
            return {}
        return {str(k): list(v or []) for k, v in (data.get("by_beam") or {}).items()}

    def _load_r31_relationships(self) -> List[Dict[str, Any]]:
        data = self._load_json(
            "PhaseR3.1_engineering_relationship_engine",
            "EngineeringDrawingRelationships.json",
        )
        if not data:
            return []
        return [r for r in (data.get("relationships") or []) if isinstance(r, dict)]

    def _load_eso(self) -> Dict[str, Dict[str, Any]]:
        data = self._load_json(
            "PhaseR2.1B_engineering_semantic_interpreter",
            "engineering_semantic_objects.json",
        )
        if not data:
            return {}
        out: Dict[str, Dict[str, Any]] = {}

        def _ingest(v: Dict[str, Any]) -> None:
            if v.get("annotation_id"):
                out[str(v["annotation_id"])] = v

        by_beam = data.get("by_beam")
        if isinstance(by_beam, dict):
            for lst in by_beam.values():
                if isinstance(lst, list):
                    for v in lst:
                        if isinstance(v, dict):
                            _ingest(v)
                elif isinstance(lst, dict):
                    for v in lst.values():
                        if isinstance(v, dict):
                            _ingest(v)
        objs = (
            data.get("objects")
            or data.get("semantic_objects")
            or data.get("by_annotation")
        )
        if isinstance(objs, dict):
            for v in objs.values():
                if isinstance(v, dict):
                    _ingest(v)
        elif isinstance(objs, list):
            for v in objs:
                if isinstance(v, dict):
                    _ingest(v)
        return out

    def _load_arrows(self) -> List[Dict[str, Any]]:
        data = self._load_json(
            "PhaseR3.1_engineering_relationship_engine", "ArrowInventory.json"
        )
        if not data:
            return []
        arrows = data.get("arrows") or data.get("inventory") or []
        if isinstance(arrows, dict):
            return [v for v in arrows.values() if isinstance(v, dict)]
        return [a for a in arrows if isinstance(a, dict)]

    def _load_inventory_index(self) -> Dict[str, Dict[str, Any]]:
        data = self._load_json("PhaseT16_entity_ownership", "entity_inventory.json")
        if not data:
            return {}
        return {
            str(e["entity_handle"]).upper(): e
            for e in (data.get("entities") or [])
            if e.get("entity_handle")
        }

    def _load_supports(self) -> Dict[str, List[Dict[str, Any]]]:
        # Prefer R.3 support crossings / validated geometry supports if present
        data = self._load_json(
            "PhaseR3.1_engineering_relationship_engine", "SupportCrossings.json"
        )
        out: Dict[str, List[Dict[str, Any]]] = {}
        if data:
            items = data.get("by_beam") or data.get("supports") or data.get("crossings")
            if isinstance(items, dict):
                for bid, lst in items.items():
                    out[str(bid)] = list(lst or []) if isinstance(lst, list) else []
            elif isinstance(items, list):
                for s in items:
                    if isinstance(s, dict) and s.get("beam_id"):
                        out.setdefault(str(s["beam_id"]), []).append(s)
        return out
