"""STEP 1 loader — read ALL TEXT/MTEXT/ATTRIB/ATTDEF using R.2.0 recovery."""
from __future__ import annotations

import importlib.util
import math
import pathlib
import sys
import types
from typing import Any, Dict, List, Optional

from .notation_models import RawTextEntity

_ENTITY_TYPES = ("TEXT", "MTEXT", "ATTRIB", "ATTDEF")


def _load_r20_recovery():
    """Read-only import of Phase R.2.0 EngineeringTextRecovery."""
    src = pathlib.Path(__file__).resolve().parent.parent
    pkg_dir = src / "PhaseR2.0_mtext_engineering_text_recovery"
    pkg_name = "PhaseR20_readonly_for_r201"

    if pkg_name not in sys.modules:
        pkg_mod = types.ModuleType(pkg_name)
        pkg_mod.__path__ = [str(pkg_dir)]
        pkg_mod.__package__ = pkg_name
        sys.modules[pkg_name] = pkg_mod

    mod_name = f"{pkg_name}.engineering_text_recovery"
    if mod_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            mod_name, pkg_dir / "engineering_text_recovery.py"
        )
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[mod_name].EngineeringTextRecovery


class NotationInventoryLoader:

    def __init__(
        self,
        dxf_path: pathlib.Path,
        beam_registry: Dict[str, Any],
        drawing_id: str = "Galera_GF_BeamReinforcementDetails",
    ):
        self._dxf = dxf_path
        self._registry = beam_registry
        self._drawing_id = drawing_id
        self._recovery = _load_r20_recovery()

    def load(self) -> List[RawTextEntity]:
        if not self._dxf.exists():
            return []
        try:
            import ezdxf
            doc = ezdxf.readfile(str(self._dxf))
        except Exception:
            return []

        entities: List[RawTextEntity] = []
        idx = 0
        for entity in doc.modelspace():
            etype = entity.dxftype()
            if etype not in _ENTITY_TYPES:
                continue
            raw = self._raw_text(entity)
            if raw is None:
                continue
            recovered = self._recovery.clean(raw) if etype == "MTEXT" else (raw or "").strip()
            x, y = self._position(entity)
            layer = str(getattr(entity.dxf, "layer", "") or "")
            entities.append(RawTextEntity(
                entity_id=f"DXF_{etype}_{idx:05d}",
                entity_type=etype,
                layer=layer,
                x=round(x, 2),
                y=round(y, 2),
                raw_text=raw,
                recovered_text=recovered,
                nearest_beam_id=self._nearest_beam(x, y),
                drawing_id=self._drawing_id,
            ))
            idx += 1
        return entities

    @staticmethod
    def _raw_text(entity) -> str:
        etype = entity.dxftype()
        if etype == "TEXT":
            return entity.dxf.text or ""
        if etype == "MTEXT":
            try:
                return entity.plain_mtext()
            except Exception:
                return getattr(entity.dxf, "text", "") or ""
        if etype in ("ATTRIB", "ATTDEF"):
            return getattr(entity.dxf, "text", "") or ""
        return ""

    @staticmethod
    def _position(entity) -> tuple:
        try:
            pt = entity.dxf.insert
            return float(pt.x), float(pt.y)
        except Exception:
            return 0.0, 0.0

    def _nearest_beam(self, x: float, y: float) -> str:
        best_id = ""
        best_dist = float("inf")
        for bid, beam in self._registry.get("beams", {}).items():
            cx = beam.get("centroid_x") or beam.get("detail_centroid_x")
            cy = beam.get("centroid_y") or beam.get("detail_centroid_y")
            if cx is None or cy is None:
                continue
            d = math.hypot(float(cx) - x, float(cy) - y)
            if d < best_dist:
                best_dist = d
                best_id = bid
        return best_id
