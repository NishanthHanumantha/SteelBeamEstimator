"""In-memory DXF region renderer. Loads the drawing once. Does not mutate M.1."""
from __future__ import annotations

import math
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .geometry import as_extent
from .timing import Timer

_TEXT_TYPES = frozenset({
    "TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION", "MULTILEADER", "LEADER",
})


class RenderSession:
    """One DXF parse + bbox cache + PNG extent cache for a whole population run."""

    def __init__(self, dxf_path: Path, *, dpi: int = 150, doc: Any = None) -> None:
        import ezdxf
        from ezdxf import bbox as ezdxf_bbox

        self.dxf_path = Path(dxf_path)
        self.dpi = int(dpi)
        self.doc = doc if doc is not None else ezdxf.readfile(str(self.dxf_path))
        self.msp = self.doc.modelspace()
        self.bbox_cache = ezdxf_bbox.Cache()
        self._png_cache: Dict[Tuple[Any, ...], Path] = {}
        self.hits = 0
        self.misses = 0
        self.render_s = 0.0

    def _key(self, extent, max_dim_px: int) -> Tuple[Any, ...]:
        e = as_extent(extent)
        return (round(e[0], 1), round(e[1], 1), round(e[2], 1), round(e[3], 1), int(max_dim_px))

    def render_crop(
        self,
        *,
        dxf_path: Path,
        output_path: Path,
        extent: Any,
        crop_type: str,
        max_dim_px: Optional[int] = None,
    ) -> Dict[str, Any]:
        from PhaseP2610A_beam_region_crop_audit.config import CONTEXT_MAX_PX, DETAIL_MAX_PX

        max_px = int(max_dim_px or (DETAIL_MAX_PX if crop_type == "detail" else CONTEXT_MAX_PX))
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        key = self._key(extent, max_px)
        cached = self._png_cache.get(key)
        if cached and cached.exists() and cached.stat().st_size > 200:
            self.hits += 1
            if cached.resolve() != output_path.resolve():
                shutil.copy2(cached, output_path)
            return {
                "path": str(output_path),
                "crop_type": crop_type,
                "dxf_bbox": list(as_extent(extent)),
                "reused_existing_png": True,
                "cache_hit": True,
            }
        self.misses += 1
        with Timer() as t:
            xf = self._render_extent(as_extent(extent), output_path, max_px)
        self.render_s += t.seconds
        self._png_cache[key] = output_path
        return {
            "path": str(output_path),
            "crop_type": crop_type,
            "dxf_bbox": list(as_extent(extent)),
            "image_dimensions": [int(xf[0]), int(xf[1])],
            "cache_hit": False,
            "render_s": t.seconds,
        }

    def _render_extent(self, extent, output_path: Path, max_dim_px: int) -> Tuple[int, int]:
        from ezdxf import bbox as ezdxf_bbox
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        xmin, ymin, xmax, ymax = extent
        w = max(xmax - xmin, 1e-6)
        h = max(ymax - ymin, 1e-6)
        aspect = w / h
        min_dim_px = 400
        if aspect >= 1.0:
            target_img_w = max_dim_px
            target_img_h = max(min_dim_px, round(max_dim_px / aspect))
        else:
            target_img_h = max_dim_px
            target_img_w = max(min_dim_px, round(max_dim_px * aspect))
        margin = max(w, h) * 0.02

        def _entity_ok(entity) -> bool:
            try:
                if entity.dxftype() in _TEXT_TYPES:
                    pass
                ext = ezdxf_bbox.extents([entity], cache=self.bbox_cache, fast=True)
            except Exception:
                return True
            if not ext.has_data:
                return True
            exmin, eymin = ext.extmin.x, ext.extmin.y
            exmax, eymax = ext.extmax.x, ext.extmax.y
            return not (
                exmax < xmin - margin
                or exmin > xmax + margin
                or eymax < ymin - margin
                or eymin > ymax + margin
            )

        fig_w_in = target_img_w / self.dpi
        fig_h_in = target_img_h / self.dpi
        fig = plt.figure(figsize=(fig_w_in, fig_h_in))
        ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ctx = RenderContext(self.doc)
        backend = MatplotlibBackend(ax)
        frontend = Frontend(ctx, backend)
        frontend.draw_layout(self.msp, finalize=False, filter_func=_entity_ok)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        fig.savefig(str(output_path), dpi=self.dpi, facecolor="white")
        plt.close(fig)
        try:
            from PIL import Image

            with Image.open(output_path) as im:
                return im.size
        except Exception:
            return (int(math.ceil(fig_w_in * self.dpi)), int(math.ceil(fig_h_in * self.dpi)))
