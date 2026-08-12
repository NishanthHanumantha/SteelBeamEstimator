"""Contact-sheet generation for visual inspection of refined crops."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

MODEL_VERSION = "10.6.6"


def _safe_open(path: Path):
    from PIL import Image

    return Image.open(path).convert("RGB")


def build_contact_sheet(
    *,
    tiles: Sequence[Dict[str, Any]],
    out_path: Path,
    tile_size: Tuple[int, int] = (320, 240),
    cols: int = 4,
    title: str = "P2.5.2.1 Contact Sheet",
) -> Dict[str, Any]:
    """
    Build a labeled contact sheet.
    Each tile dict: {path, label_lines: [str,...]}
    """
    from PIL import Image, ImageDraw, ImageFont

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not tiles:
        # empty placeholder
        img = Image.new("RGB", (640, 120), (245, 245, 245))
        draw = ImageDraw.Draw(img)
        draw.text((12, 40), f"{title} — no tiles", fill=(30, 30, 30))
        img.save(out_path)
        return {"success": True, "path": str(out_path), "tile_count": 0}

    tw, th = tile_size
    label_h = 54
    cell_w, cell_h = tw, th + label_h
    n = len(tiles)
    cols = max(1, min(cols, n))
    rows = (n + cols - 1) // cols
    header_h = 36
    sheet_w = cols * cell_w + 16
    sheet_h = header_h + rows * cell_h + 16
    sheet = Image.new("RGB", (sheet_w, sheet_h), (250, 250, 250))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    draw.text((10, 8), title, fill=(20, 20, 20), font=font)

    for i, tile in enumerate(tiles):
        r, c = divmod(i, cols)
        x0 = 8 + c * cell_w
        y0 = header_h + 4 + r * cell_h
        path = Path(tile["path"]) if tile.get("path") else None
        if path and path.exists():
            try:
                im = _safe_open(path)
                im.thumbnail((tw - 8, th - 8))
                ox = x0 + (tw - im.size[0]) // 2
                oy = y0 + (th - im.size[1]) // 2
                sheet.paste(im, (ox, oy))
                im.close()
            except Exception:
                draw.rectangle([x0, y0, x0 + tw - 2, y0 + th - 2], outline=(180, 0, 0))
                draw.text((x0 + 8, y0 + 8), "IMAGE_ERROR", fill=(180, 0, 0), font=font)
        else:
            draw.rectangle([x0, y0, x0 + tw - 2, y0 + th - 2], outline=(160, 160, 160))
            draw.text((x0 + 8, y0 + 8), "MISSING", fill=(120, 120, 120), font=font)

        # status color bar
        status = str(tile.get("status") or "")
        color = (40, 140, 40)
        if "PARTIAL" in status:
            color = (200, 140, 20)
        elif "FAIL" in status:
            color = (180, 40, 40)
        elif "REVIEW" in status:
            color = (140, 40, 140)
        draw.rectangle([x0, y0 + th - 4, x0 + tw - 2, y0 + th], fill=color)

        ly = y0 + th + 2
        for line in (tile.get("label_lines") or [])[:3]:
            draw.text((x0 + 4, ly), str(line)[:48], fill=(25, 25, 25), font=font)
            ly += 14

    sheet.save(out_path)
    return {"success": True, "path": str(out_path), "tile_count": n, "cols": cols, "rows": rows}


def build_inspection_package(
    *,
    refined_manifests: List[Dict[str, Any]],
    candidates_root: Path,
    contact_root: Path,
) -> Dict[str, Any]:
    contact_root = Path(contact_root)
    contact_root.mkdir(parents=True, exist_ok=True)

    local_tiles = []
    context_tiles = []
    for m in refined_manifests:
        cid = m.get("candidate_id") or ""
        beam = m.get("beam_id")
        folder = candidates_root / cid.replace("::", "__")
        local = m.get("local_refined") or {}
        ctx = m.get("beam_context_refined") or {}
        local_tiles.append(
            {
                "path": folder / "local_refined.png",
                "status": local.get("readability_status"),
                "label_lines": [
                    f"{beam} | local | iter {local.get('refinement_iteration')}",
                    f"{local.get('readability_status')}",
                    f"{(m.get('raw_text') or '')[:40]}",
                ],
            }
        )
        context_tiles.append(
            {
                "path": folder / "beam_context_refined.png",
                "status": ctx.get("readability_status"),
                "label_lines": [
                    f"{beam} | context | iter {ctx.get('refinement_iteration')}",
                    f"{ctx.get('readability_status')}",
                    f"{(m.get('raw_text') or '')[:40]}",
                ],
            }
        )

    local_sheet = build_contact_sheet(
        tiles=local_tiles,
        out_path=contact_root / "contact_sheet_local_refined.png",
        title="P2.5.2.1 — Local Refined Crops (ACTIVE)",
    )
    ctx_sheet = build_contact_sheet(
        tiles=context_tiles,
        out_path=contact_root / "contact_sheet_beam_context_refined.png",
        title="P2.5.2.1 — Beam-Context Refined Crops (ACTIVE)",
    )
    return {
        "local_contact_sheet": local_sheet,
        "beam_context_contact_sheet": ctx_sheet,
        "individual_crops_root": str(candidates_root),
    }


__all__ = ["build_contact_sheet", "build_inspection_package"]
