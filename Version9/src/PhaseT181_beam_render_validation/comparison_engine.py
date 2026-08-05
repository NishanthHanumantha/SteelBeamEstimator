"""
T1.8.1 — Side-by-side comparison + pixel difference images.
MODEL_VERSION: 9.5.1
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

MODEL_VERSION = "9.5.1"


def make_side_by_side(
    manual: Path,
    rendered: Path,
    dest: Path,
    *,
    beam_id: str = "",
) -> Dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    import numpy as np

    manual = Path(manual)
    rendered = Path(rendered)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    img_l = Image.open(manual).convert("RGB")
    img_r = Image.open(rendered).convert("RGB")

    def _resize_h(im: Image.Image, th: int) -> Image.Image:
        if im.height == th:
            return im
        w = max(1, int(im.width * th / im.height))
        return im.resize((w, th), Image.Resampling.BILINEAR)

    h = max(img_l.height, img_r.height)
    img_l = _resize_h(img_l, h)
    img_r = _resize_h(img_r, h)
    gap = 12
    canvas = Image.new(
        "RGB", (img_l.width + gap + img_r.width, h + 40), (255, 255, 255)
    )
    canvas.paste(img_l, (0, 40))
    canvas.paste(img_r, (img_l.width + gap, 40))

    arr = np.array(canvas)
    fig = plt.figure(figsize=(canvas.width / 100, canvas.height / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(arr)
    ax.set_axis_off()
    ax.text(
        img_l.width / 2,
        16,
        f"{beam_id} — Manual AutoCAD crop" if beam_id else "Manual",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="#222222",
    )
    ax.text(
        img_l.width + gap + img_r.width / 2,
        16,
        f"{beam_id} — Owned render (T1.8 scoped)" if beam_id else "Rendered",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="#222222",
    )
    fig.savefig(str(dest), dpi=100, facecolor="white")
    plt.close(fig)
    return {"path": str(dest), "width": canvas.width, "height": canvas.height}


def make_diff_image(
    manual: Path,
    rendered: Path,
    dest: Path,
    *,
    beam_id: str = "",
) -> Dict[str, Any]:
    """Deterministic absolute pixel difference (resized to common size)."""
    from PIL import Image
    import numpy as np

    manual = Path(manual)
    rendered = Path(rendered)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    img_a = Image.open(manual).convert("RGB")
    img_b = Image.open(rendered).convert("RGB")
    tw = max(img_a.width, img_b.width)
    th = max(img_a.height, img_b.height)
    img_a = img_a.resize((tw, th), Image.Resampling.BILINEAR)
    img_b = img_b.resize((tw, th), Image.Resampling.BILINEAR)

    a = np.asarray(img_a, dtype=np.int16)
    b = np.asarray(img_b, dtype=np.int16)
    diff = np.abs(a - b).astype(np.uint8)
    # Amplify for visibility; red channel = magnitude
    mag = diff.max(axis=2)
    heat = np.zeros((th, tw, 3), dtype=np.uint8)
    heat[..., 0] = np.clip(mag * 3, 0, 255)
    heat[..., 1] = np.clip(mag // 2, 0, 255)
    heat[..., 2] = np.clip(255 - mag * 2, 0, 80)
    Image.fromarray(heat).save(dest)

    changed = int((mag > 12).sum())
    total = tw * th
    return {
        "path": str(dest),
        "beam_id": beam_id,
        "width": tw,
        "height": th,
        "changed_pixels": changed,
        "changed_ratio": round(changed / max(total, 1), 4),
        "mean_abs_diff": float(np.mean(mag)),
    }
