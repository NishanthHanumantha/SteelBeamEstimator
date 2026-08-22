"""QA.2A KPI splits: HYBRID_ONLY / FALLBACK_ONLY / FULL. No cross-contamination."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Set

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.kpis import compute_kpis, diameter_wise

_QA2A_DIR = Path(__file__).resolve().parents[1] / "PhaseQA.2A_ground_truth_benchmark"
_QA2A_MODULES = (
    "gt_models",
    "bar_matcher",
    "beam_matcher",
    "metrics_engine",
    "error_classifier",
    "workbook_normalizer",
)


def _ensure_qa2a() -> None:
    p = str(_QA2A_DIR)
    if sys.path[:1] != [p]:
        if p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)
    for name in _QA2A_MODULES:
        dest = _QA2A_DIR / f"{name}.py"
        if not dest.exists():
            continue
        current = sys.modules.get(name)
        current_file = Path(getattr(current, "__file__", "") or "")
        if current is not None and current_file.exists() and current_file.resolve() == dest.resolve():
            continue
        spec = importlib.util.spec_from_file_location(name, dest)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)


def filter_workbook(wb, beam_ids: Iterable[str]):
    _ensure_qa2a()
    from gt_models import NormalizedWorkbook  # type: ignore

    allow: Set[str] = {str(x) for x in beam_ids}
    beams = [b for b in (wb.beams or []) if str(b.beam_id) in allow]
    total = round(sum(float(b.steel_kg or 0) for b in beams), 4)
    dia: Dict[int, float] = {}
    for b in beams:
        for d, kg in (b.diameter_kg or {}).items():
            dia[int(d)] = round(dia.get(int(d), 0.0) + float(kg), 4)
    return NormalizedWorkbook(
        source_path=wb.source_path,
        source_label=wb.source_label,
        project_name=getattr(wb, "project_name", "") or "",
        sheet_names=list(getattr(wb, "sheet_names", []) or []),
        beams=beams,
        total_steel_kg=total,
        total_steel_mt=round(total / 1000.0, 4),
        diameter_kg=dia,
    )


def score_cohort(*, drawing_set: str, estimator, model, label: str) -> Dict[str, Any]:
    _ensure_qa2a()
    if estimator is None or model is None or not getattr(model, "beams", None):
        return {
            "label": label,
            "applicable": False,
            "reason": "INSUFFICIENT_COMPARISON_EVIDENCE",
            "kpis": None,
        }
    kpis = compute_kpis(drawing_set=drawing_set, estimator=estimator, model=model)
    return {"label": label, "applicable": True, "reason": None, "kpis": kpis, "diameter_wise": diameter_wise(kpis)}


def split_scores(*, drawing_set: str, estimator, model_full, hybrid_ids: Iterable[str], fallback_ids: Iterable[str]) -> Dict[str, Any]:
    hy = {str(x) for x in hybrid_ids}
    fb = {str(x) for x in fallback_ids}
    full = score_cohort(drawing_set=drawing_set, estimator=estimator, model=model_full, label="FULL_POPULATION")
    hy_model = filter_workbook(model_full, hy)
    hy_est = filter_workbook(estimator, hy)
    fb_model = filter_workbook(model_full, fb)
    fb_est = filter_workbook(estimator, fb)
    return {
        "FULL_POPULATION": full,
        "HYBRID_ONLY": score_cohort(drawing_set=drawing_set, estimator=hy_est, model=hy_model, label="HYBRID_ONLY"),
        "FALLBACK_ONLY": score_cohort(drawing_set=drawing_set, estimator=fb_est, model=fb_model, label="FALLBACK_ONLY"),
        "note": "Subset scores use matching estimator+model beam IDs only. Full-population totals are not replaced by subset sums.",
    }


def semantic_field_breakdown(kpis: Dict[str, Any]) -> Dict[str, Any]:
    tax = (kpis.get("correct_of_detected") or {}).get("taxonomy") or {}
    dia = kpis.get("diameter_identification") or {}
    beam = kpis.get("beam_identification") or {}
    return {
        "target_identification": {
            "status": "MEASURED",
            "percent": beam.get("beam_identification_percent"),
            "source": "QA.2A BeamMatcher",
        },
        "diameter": {
            "status": "MEASURED",
            "percent": dia.get("diameter_identification_percent"),
            "source": "QA.2A detected bars with both diameters",
        },
        "MAIN_EXTRA_role": {
            "status": "MEASURED_VIA_TAXONOMY",
            "wrong_role": tax.get("WRONG_ROLE", 0),
            "match": tax.get("MATCH", 0),
            "source": "QA.2A BarMatcher WRONG_ROLE vs MATCH",
        },
        "bar_count": {
            "status": "MEASURED_VIA_TAXONOMY",
            "wrong_quantity": tax.get("WRONG_QUANTITY", 0),
            "source": "QA.2A BarMatcher WRONG_QUANTITY",
        },
        "layer": {"status": "NOT_MEASURED", "reason": "INSUFFICIENT_COMPARISON_EVIDENCE"},
        "physical_group_detection": {"status": "NOT_MEASURED", "reason": "INSUFFICIENT_COMPARISON_EVIDENCE"},
        "specification": {"status": "NOT_MEASURED", "reason": "INSUFFICIENT_COMPARISON_EVIDENCE"},
        "support_scope": {"status": "NOT_MEASURED", "reason": "INSUFFICIENT_COMPARISON_EVIDENCE"},
        "stirrup_identification": {"status": "NOT_MEASURED", "reason": "INSUFFICIENT_COMPARISON_EVIDENCE"},
        "note": "Do not treat unmeasured fields as zero percent.",
    }


__all__ = ["filter_workbook", "score_cohort", "semantic_field_breakdown", "split_scores"]
