"""Charts generated only from actual benchmark JSON. No fabricated series."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .config import INCLUDED_SET_KEYS
from .pooling import round_display


def _pct(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def write_charts(*, out_root: Path, report_data: Dict[str, Any]) -> Dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    charts_dir = Path(out_root) / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    per_set = report_data.get("per_set") or {}
    keys = [k for k in INCLUDED_SET_KEYS if k in per_set] or list(per_set.keys())
    labels = [f"{k} Set" for k in keys]
    overall = [_pct((per_set.get(k) or {}).get("overall_accuracy_percent")) for k in keys]
    beam = [_pct((per_set.get(k) or {}).get("beam_identification_percent")) for k in keys]
    bar = [_pct((per_set.get(k) or {}).get("bar_identification_percent")) for k in keys]
    correct = [_pct((per_set.get(k) or {}).get("correct_of_detected_percent")) for k in keys]
    steel = [_pct((per_set.get(k) or {}).get("weight_accuracy_percent")) for k in keys]
    hybrid = [_pct((per_set.get(k) or {}).get("hybrid_count")) for k in keys]
    fallback = [_pct((per_set.get(k) or {}).get("fallback_count")) for k in keys]
    model_kg = [_pct((per_set.get(k) or {}).get("hybrid_total_kg")) for k in keys]
    bench_kg = [_pct((per_set.get(k) or {}).get("benchmark_total_kg")) for k in keys]
    tax = report_data.get("semantic_taxonomy_pooled") or {}
    paths: Dict[str, str] = {}

    def _save(fig, name: str) -> None:
        dest = charts_dir / name
        fig.tight_layout()
        fig.savefig(dest, dpi=140, bbox_inches="tight")
        plt.close(fig)
        paths[name] = str(dest)

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.bar(labels, overall, color="#1B365D")
    ax.set_ylabel("Overall accuracy %")
    ax.set_title("Per-set overall accuracy — current hybrid architecture")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    _save(fig, "per_set_overall_accuracy.png")

    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    x = list(range(len(labels)))
    w = 0.2
    ax.bar([i - 1.5 * w for i in x], beam, width=w, label="Beam ID", color="#1B365D")
    ax.bar([i - 0.5 * w for i in x], bar, width=w, label="Bar ID", color="#2F5D7C")
    ax.bar([i + 0.5 * w for i in x], correct, width=w, label="Correct of detected", color="#1F6B3A")
    ax.bar([i + 1.5 * w for i in x], steel, width=w, label="Steel / weight", color="#B88A2E")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.set_ylabel("%")
    ax.set_title("Per-set KPI comparison")
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    _save(fig, "per_set_kpi_comparison.png")

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.bar(labels, hybrid, label="HYBRID", color="#1F6B3A")
    ax.bar(labels, fallback, bottom=hybrid, label="FALLBACK", color="#9B2C2C")
    ax.set_ylabel("Model beams")
    ax.set_title("HYBRID versus FALLBACK coverage")
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    _save(fig, "hybrid_fallback_coverage.png")

    names = [
        "MATCH",
        "WRONG_QUANTITY",
        "WRONG_DIAMETER",
        "MISSING",
        "PARTIAL_MATCH",
        "WRONG_ROLE",
        "EXTRA",
        "ACCEPTABLE_EXTRA",
    ]
    vals = [int(tax.get(n) or 0) for n in names]
    extra_keys = [k for k in tax.keys() if k not in names]
    names = names + extra_keys
    vals = vals + [int(tax.get(k) or 0) for k in extra_keys]
    fig, ax = plt.subplots(figsize=(9.0, 4.4))
    ax.barh(names, vals, color="#2F5D7C")
    ax.set_xlabel("Count")
    ax.set_title("Semantic error distribution (pooled matcher taxonomy)")
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    _save(fig, "semantic_error_distribution.png")

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    x = list(range(len(labels)))
    w = 0.35
    ax.bar([i - w / 2 for i in x], model_kg, width=w, label="Model kg", color="#1B365D")
    ax.bar([i + w / 2 for i in x], bench_kg, width=w, label="Benchmark kg", color="#B88A2E")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Steel kg")
    ax.set_title("Model steel kg versus benchmark steel kg")
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    _save(fig, "model_vs_benchmark_steel_kg.png")

    return paths


__all__ = ["write_charts"]
