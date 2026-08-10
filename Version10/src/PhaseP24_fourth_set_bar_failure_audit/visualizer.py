"""
Limited diagnostic visualisations for P2.4 (no render algorithm changes).
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .config import P24Config


def _safe_import_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except Exception:
        return None


def select_representatives(
    matrix: List[Dict[str, Any]], max_per: int
) -> Dict[str, List[Dict[str, Any]]]:
    classes = {
        "PHYSICAL_BAR_DETECTION": [],
        "OWNERSHIP": [],
        "ANNOTATION_ASSOCIATION": [],
        "SEMANTIC_DIAMETER": [],
    }
    for r in matrix:
        ff = r["first_failure_stage"]
        if ff == "PHYSICAL_BAR_DETECTION" and len(classes["PHYSICAL_BAR_DETECTION"]) < max_per:
            classes["PHYSICAL_BAR_DETECTION"].append(r)
        elif ff == "OWNERSHIP" and len(classes["OWNERSHIP"]) < max_per:
            classes["OWNERSHIP"].append(r)
        elif ff == "ANNOTATION_ASSOCIATION" and len(classes["ANNOTATION_ASSOCIATION"]) < max_per:
            classes["ANNOTATION_ASSOCIATION"].append(r)
        elif ff in (
            "ROLE_RESOLUTION",
            "DIAMETER_RESOLUTION",
            "QUANTITY_RESOLUTION",
        ) and len(classes["SEMANTIC_DIAMETER"]) < max_per:
            classes["SEMANTIC_DIAMETER"].append(r)
    return classes


def write_visuals(
    matrix: List[Dict[str, Any]],
    first_fail_pct: Dict[str, float],
    out_dir: Path,
    config: P24Config,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    plt = _safe_import_matplotlib()
    written: List[str] = []
    reps = select_representatives(matrix, config.max_visuals_per_class)

    # distribution chart
    if plt and first_fail_pct:
        fig, ax = plt.subplots(figsize=(10, 5))
        items = sorted(first_fail_pct.items(), key=lambda x: -x[1])
        labels = [k for k, _ in items]
        vals = [v for _, v in items]
        ax.barh(labels[::-1], vals[::-1], color="#2F5D8C")
        ax.set_xlabel("% of failing GT bars")
        ax.set_title("P2.4 Fourth Set — First-Failure Distribution")
        fig.tight_layout()
        p = out_dir / "first_failure_distribution.png"
        fig.savefig(p, dpi=120)
        plt.close(fig)
        written.append(str(p))

    # representative case cards (text panels)
    if plt:
        for cls, rows in reps.items():
            if not rows:
                continue
            fig, ax = plt.subplots(figsize=(11, 2 + 0.55 * len(rows)))
            ax.axis("off")
            lines = [f"P2.4 representative failures — {cls}", ""]
            for r in rows:
                lines.append(
                    f"{r['beam_id']} | {r['gt_role']} Y{r['gt_diameter']} qty={r['gt_quantity']} "
                    f"| phys={r['physical_status']} own={r['ownership_status']} "
                    f"ann={r['annotation_status']} | {r['failure_reason']}"
                )
                lines.append(
                    f"  DXF={r['dxf_entity_handle']} PHYS={r['physical_bar_id']} "
                    f"ANN={r['annotation_id']} LDR={r['leader_id']}"
                )
            ax.text(
                0.02,
                0.98,
                "\n".join(lines),
                va="top",
                ha="left",
                family="monospace",
                fontsize=8,
                transform=ax.transAxes,
            )
            p = out_dir / f"rep_{cls.lower()}.png"
            fig.savefig(p, dpi=120)
            plt.close(fig)
            written.append(str(p))

    manifest = {
        "images": written,
        "representatives": {
            k: [
                {
                    "beam_id": r["beam_id"],
                    "gt_bar_id": r["gt_bar_id"],
                    "first_failure_stage": r["first_failure_stage"],
                    "failure_reason": r["failure_reason"],
                }
                for r in v
            ]
            for k, v in reps.items()
        },
    }
    (out_dir / "visual_manifest.json").write_text(
        __import__("json").dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest
