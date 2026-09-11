"""
Phase T1.6 orchestrator — entity inventory + ownership + filtered renders.
MODEL_VERSION: 9.3.6
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .entity_inventory import build_entity_inventory, inventory_index
from .ownership_engine import (
    MODEL_VERSION,
    high_handles_for_beam,
    resolve_ownership,
)
from .ownership_renderer import render_owned_entities_to_png, render_ownership_overlay

PHASE_ID = "T1.6"
_OUT_NAME = "PhaseT16_entity_ownership"


class PhaseT16Orchestrator:
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
        render_beams: Optional[Sequence[str]] = None,
        write_overlays: bool = True,
    ) -> Dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        dxf = self._find_reinforcement_dxf()
        if not dxf:
            return {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "no_reinforcement_dxf",
            }

        import ezdxf

        doc = ezdxf.readfile(str(dxf))
        msp = doc.modelspace()

        print("[T1.6] Building entity inventory...")
        inventory = build_entity_inventory(msp)
        inv_path = self.out_dir / "entity_inventory.json"
        # Write a compact summary + full entities (may be large)
        inv_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

        envelopes = self._load_envelopes()
        annotations = self._load_annotations()
        bars = self._load_physical_bars()
        leaders = self._load_leaders()
        geometries = self._load_geometries()

        ids = list(beam_ids) if beam_ids else sorted(envelopes.keys())
        ids = [b for b in ids if b in envelopes]

        print(f"[T1.6] Resolving ownership for {len(ids)} beams...")
        ownership = resolve_ownership(
            inventory,
            envelopes,
            annotations,
            bars,
            leaders,
            geometries_by_beam=geometries,
            beam_ids=ids,
        )
        own_path = self.out_dir / "beam_entity_ownership.json"
        own_path.write_text(json.dumps(ownership, indent=2), encoding="utf-8")

        stats = self._compute_statistics(inventory, ownership, envelopes, ids)
        (self.out_dir / "ownership_statistics.json").write_text(
            json.dumps(stats, indent=2), encoding="utf-8"
        )

        render_ids = list(render_beams) if render_beams is not None else ids
        render_stats = []
        idx = inventory_index(inventory)
        for bid in render_ids:
            if bid not in envelopes:
                continue
            rs = self._render_beam(dxf, bid, envelopes[bid], ownership, idx, write_overlays)
            if rs:
                render_stats.append(rs)

        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": True,
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dxf": str(dxf),
            "out_dir": str(self.out_dir),
            "entity_count": inventory["entity_count"],
            "beam_count": len(ids),
            "statistics": stats,
            "render_stats": render_stats,
        }
        (self.out_dir / "t16_run_summary.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result

    def _render_beam(
        self,
        dxf: Path,
        beam_id: str,
        envelope: Dict[str, Any],
        ownership: Dict[str, Any],
        inv_index: Dict[str, Dict[str, Any]],
        write_overlays: bool,
    ) -> Optional[Dict[str, Any]]:
        ext = envelope.get("extent")
        if not ext:
            return None
        extent = (float(ext[0]), float(ext[1]), float(ext[2]), float(ext[3]))
        handles = high_handles_for_beam(ownership, beam_id)
        beam_dir = self.out_dir / beam_id
        beam_dir.mkdir(parents=True, exist_ok=True)

        filt = beam_dir / "filtered_render.png"
        notext = beam_dir / "filtered_notext.png"
        info = render_owned_entities_to_png(
            dxf, filt, extent, handles, render_text=True
        )
        info_nt = render_owned_entities_to_png(
            dxf, notext, extent, handles, render_text=False
        )

        rows = (ownership.get("by_beam") or {}).get(beam_id) or []
        if write_overlays:
            render_ownership_overlay(
                dxf,
                beam_dir / "ownership_overlay.png",
                extent,
                rows,
                inv_index,
            )

        n_high = sum(1 for r in rows if r["ownership"] == "HIGH")
        n_med = sum(1 for r in rows if r["ownership"] == "MEDIUM")
        n_low = sum(1 for r in rows if r["ownership"] == "LOW")
        return {
            "beam_id": beam_id,
            "extent": list(extent),
            "handles_high": len(handles),
            "owned_high": n_high,
            "owned_medium": n_med,
            "owned_low": n_low,
            "entities_drawn_text": info.get("entities_drawn"),
            "entities_drawn_notext": info_nt.get("entities_drawn"),
            "filtered_render": str(filt),
            "filtered_notext": str(notext),
        }

    @staticmethod
    def _compute_statistics(
        inventory: Dict[str, Any],
        ownership: Dict[str, Any],
        envelopes: Dict[str, Dict[str, Any]],
        beam_ids: List[str],
    ) -> Dict[str, Any]:
        scanned = inventory.get("entity_count") or 0
        inv_by_h = {
            str(e["entity_handle"]).upper(): e
            for e in (inventory.get("entities") or [])
            if e.get("entity_handle")
        }
        by_beam = {}
        for bid in beam_ids:
            rows = (ownership.get("by_beam") or {}).get(bid) or []
            n_high = sum(1 for r in rows if r["ownership"] == "HIGH")
            n_med = sum(1 for r in rows if r["ownership"] == "MEDIUM")
            n_low = sum(1 for r in rows if r["ownership"] == "LOW")
            accepted = n_high
            # Rejected relative to full inventory — report reduction vs scanned.
            reduction = round(100.0 * (1.0 - accepted / max(scanned, 1)), 2)
            env = envelopes.get(bid) or {}
            ext = env.get("extent")
            area = None
            if ext:
                area = abs((ext[2] - ext[0]) * (ext[3] - ext[1]))
            # Owned content bbox area vs full envelope (proxy for clutter removed)
            owned_area = None
            xs: List[float] = []
            ys: List[float] = []
            for r in rows:
                if r["ownership"] != "HIGH":
                    continue
                ent = inv_by_h.get(str(r["handle"]).upper())
                if not ent or not ent.get("bounding_box"):
                    continue
                bb = ent["bounding_box"]
                xs.extend([bb[0], bb[2]])
                ys.extend([bb[1], bb[3]])
            if xs and ys and ext:
                # Intersect owned content bbox with envelope (shared long bars
                # otherwise inflate beyond the crop and yield nonsense %).
                ox0 = max(min(xs), float(ext[0]))
                oy0 = max(min(ys), float(ext[1]))
                ox1 = min(max(xs), float(ext[2]))
                oy1 = min(max(ys), float(ext[3]))
                if ox1 > ox0 and oy1 > oy0:
                    owned_area = abs((ox1 - ox0) * (oy1 - oy0))
            area_red = None
            if area and owned_area is not None:
                area_red = round(100.0 * (1.0 - owned_area / max(area, 1e-6)), 2)
            by_beam[bid] = {
                "entities_scanned": scanned,
                "entities_accepted_high": accepted,
                "entities_medium": n_med,
                "entities_low": n_low,
                "entities_rejected_or_other": scanned - accepted,
                "entity_reduction_pct": reduction,
                "envelope_area_mm2": round(area, 1) if area else None,
                "owned_content_bbox_mm2": round(owned_area, 1) if owned_area else None,
                "render_area_reduction_pct": area_red,
                "by_role": _count_roles([r for r in rows if r["ownership"] == "HIGH"]),
            }
        return {
            "model_version": MODEL_VERSION,
            "entities_scanned_total": scanned,
            "by_type": inventory.get("by_type"),
            "by_beam": by_beam,
        }

    def _find_reinforcement_dxf(self) -> Optional[Path]:
        for p in self.run_root.rglob("*.dxf"):
            name = p.name.lower()
            parent = p.parent.name.lower()
            if "reinforc" in name or "reinforc" in parent or "stirrup" in name:
                return p
        return None

    def _load_envelopes(self) -> Dict[str, Dict[str, Any]]:
        path = (
            self.output_root
            / "PhaseT1_geometric_stirrup_evidence"
            / "geometry_envelopes.json"
        )
        if not path.exists():
            # fallback to Track1 benchmark file
            alt = (
                self.engine_root
                / "data"
                / "output"
                / "Track1_geometric_evidence"
                / "geometry_envelopes_Set1_benchmark.json"
            )
            path = alt if alt.exists() else path
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): v for k, v in (data.get("by_beam") or {}).items()}

    def _load_annotations(self) -> Dict[str, List[Dict[str, Any]]]:
        path = (
            self.output_root
            / "PhaseR.1_generalized_reinforcement_discovery"
            / "reinforcement_annotations.json"
        )
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): list(v or []) for k, v in (data.get("by_beam") or {}).items()}

    def _load_physical_bars(self) -> List[Dict[str, Any]]:
        path = (
            self.output_root
            / "PhaseR3.1_engineering_relationship_engine"
            / "PhysicalBars.json"
        )
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [b for b in (data.get("bars") or []) if isinstance(b, dict)]

    def _load_leaders(self) -> List[Dict[str, Any]]:
        path = (
            self.output_root
            / "PhaseR3.1_engineering_relationship_engine"
            / "LeaderInventory.json"
        )
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        leaders = data.get("leaders") or data.get("by_beam") or []
        if isinstance(leaders, dict):
            out = []
            for bid, lst in leaders.items():
                for L in lst or []:
                    if isinstance(L, dict):
                        L = dict(L)
                        L.setdefault("beam_id", bid)
                        out.append(L)
            return out
        return [L for L in leaders if isinstance(L, dict)]

    def _load_geometries(self) -> Dict[str, Dict[str, Any]]:
        path = (
            self.output_root
            / "PhaseR1_2A_geometry_accuracy"
            / "validated_beam_geometry.json"
        )
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): v for k, v in (data.get("geometries") or {}).items()}


def _count_roles(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in rows:
        role = str(r.get("role") or "OTHER")
        out[role] = out.get(role, 0) + 1
    return out
