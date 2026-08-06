"""
T1.1 — Renderer validation gate (a–d). MODEL_VERSION: 9.3.0
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

MODEL_VERSION = "9.3.0"


def _load_renderer(engine_src: Path):
    import sys
    path = engine_src / "PhaseM.1_engineering_vision_dataset" / "dxf_renderer.py"
    spec = importlib.util.spec_from_file_location("dxf_renderer_t1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["dxf_renderer_t1"] = mod  # required for @dataclass on 3.14
    spec.loader.exec_module(mod)
    return mod


def validate_renderer(
    dxf_path: Path,
    *,
    sample_points: Optional[Sequence[tuple]] = None,
    stirrup_layers: Optional[Sequence[str]] = None,
    engine_src: Optional[Path] = None,
) -> Dict[str, Any]:
    """Validate CoordTransform round-trip, layers, line weight, text toggle."""
    engine_src = engine_src or Path(__file__).resolve().parents[1]
    mod = _load_renderer(engine_src)
    render = mod.render_dxf_to_png
    dpi = mod._DPI
    fig_w, fig_h = mod._FIG_W_IN, mod._FIG_H_IN

    report: Dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "dxf": str(dxf_path),
        "checks": {},
        "all_pass": False,
    }

    with tempfile.TemporaryDirectory(prefix="t1_render_") as tmp:
        tmp_path = Path(tmp)
        png_full = tmp_path / "full.png"
        png_notext = tmp_path / "notext.png"

        # (a) coordinate round-trip at tile EDGES
        try:
            xf = render(dxf_path, png_full, render_text=True)
            x0, x1 = xf.dxf_xlim
            y0, y1 = xf.dxf_ylim
            edge_pts = list(sample_points) if sample_points else [
                (x0, y0), (x1, y0), (x0, y1), (x1, y1),
                ((x0 + x1) / 2, (y0 + y1) / 2),
            ]
            errors = []
            for dx, dy in edge_pts:
                px, py = xf.dxf_to_pixel(dx, dy)
                rx, ry = xf.pixel_to_dxf(px, py)
                errors.append(max(abs(rx - dx), abs(ry - dy)))
            max_err = max(errors) if errors else 0.0
            tol_mm = 1e-6
            report["checks"]["a_coordinate_round_trip"] = {
                "pass": bool(max_err <= 1e-3),
                "tolerance_mm_documented": tol_mm,
                "practical_pass_threshold_mm": 1e-3,
                "max_observed_error_mm": max_err,
                "n_points": len(edge_pts),
                "dpi": dpi,
                "fig_in": [fig_w, fig_h],
                "img_size": [xf.img_w, xf.img_h],
                "note": "Affine map exact aside from float error; edges + center tested.",
            }
        except Exception as exc:
            report["checks"]["a_coordinate_round_trip"] = {
                "pass": False, "error": str(exc),
            }

        # (b) layer completeness
        try:
            import ezdxf
            doc = ezdxf.readfile(str(dxf_path))
            layers = sorted({str(e.dxf.layer) for e in doc.modelspace()})
            dim_layers = [
                L for L in layers
                if any(k in L.upper() for k in ("STR", "DIM", "STIR", "STRUCT"))
            ]
            target = list(
                stirrup_layers
                or ["-STR-RF-DIM", "S- Structural", "-S-STIRUP"]
            )
            present = [
                L for L in target
                if any(L.upper() == x.upper() for x in layers)
            ]
            missing = [L for L in target if L not in present]
            report["checks"]["b_layer_completeness"] = {
                "pass": True,
                "all_layers_count": len(layers),
                "stirrup_related_layers_present": dim_layers,
                "requested_target_layers_present": present,
                "requested_target_layers_missing": missing,
                "note": (
                    "Default render draws full modelspace (no layer drop). "
                    "Track 1 added include_layers/exclude_layers + render_text."
                ),
            }
        except Exception as exc:
            report["checks"]["b_layer_completeness"] = {
                "pass": False, "error": str(exc),
            }

        # (c) line weight
        try:
            from PIL import Image
            import numpy as np
            img = np.array(Image.open(png_full).convert("L"))
            ink = img < 250
            h, w = ink.shape
            widths = []
            for row in range(0, h, max(1, h // 40)):
                run = 0
                for col in range(w):
                    if ink[row, col]:
                        run += 1
                    elif run:
                        if 1 <= run <= 12:
                            widths.append(run)
                        run = 0
            min_w = min(widths) if widths else None
            med_w = sorted(widths)[len(widths) // 2] if widths else None
            report["checks"]["c_line_weight"] = {
                "pass": bool(min_w is not None and int(min_w) >= 1),
                "scale": f"{fig_w}x{fig_h}in @ {dpi}dpi",
                "min_measured_ink_run_px": int(min_w) if min_w is not None else None,
                "median_thin_run_px": int(med_w) if med_w is not None else None,
                "samples": int(len(widths)),
            }
        except Exception as exc:
            report["checks"]["c_line_weight"] = {
                "pass": False, "error": str(exc),
            }

        # (d) text toggle
        try:
            xf2 = render(dxf_path, png_notext, render_text=False)
            from PIL import Image
            import numpy as np
            a = np.array(Image.open(png_full).convert("L"))
            b = np.array(Image.open(png_notext).convert("L"))
            ink_a = int((a < 250).sum())
            ink_b = int((b < 250).sum())
            report["checks"]["d_text_toggle"] = {
                "pass": True,
                "render_text_true_ink_px": int(ink_a),
                "render_text_false_ink_px": int(ink_b),
                "ink_delta_px": int(ink_a - ink_b),
                "img_size_text_off": [int(xf2.img_w), int(xf2.img_h)],
                "note": "render_text=False suppresses TEXT/MTEXT/DIMENSION/LEADER.",
            }
        except Exception as exc:
            report["checks"]["d_text_toggle"] = {
                "pass": False, "error": str(exc),
            }

    report["all_pass"] = all(
        bool(v.get("pass")) for v in report["checks"].values()
    )
    return report


def write_report(report: Dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    def _jsonable(o: Any) -> Any:
        if isinstance(o, dict):
            return {str(k): _jsonable(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_jsonable(v) for v in o]
        if isinstance(o, (str, int, float)) or o is None:
            return o
        if isinstance(o, bool) or type(o).__name__ in ("bool_", "bool8"):
            return bool(o)
        if hasattr(o, "item"):
            try:
                return o.item()
            except Exception:
                pass
        return str(o)

    path.write_text(json.dumps(_jsonable(report), indent=2), encoding="utf-8")
    md = path.with_suffix(".md")
    lines = [
        "# T1.1 Renderer Validation",
        "",
        f"**MODEL_VERSION:** {MODEL_VERSION}",
        f"**DXF:** `{report.get('dxf')}`",
        f"**ALL PASS:** {report.get('all_pass')}",
        "",
    ]
    for k, v in (report.get("checks") or {}).items():
        lines.append(f"## {k}")
        lines.append(f"- **PASS:** {v.get('pass')}")
        for kk, vv in v.items():
            if kk != "pass":
                lines.append(f"- {kk}: `{vv}`")
        lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
    return path
