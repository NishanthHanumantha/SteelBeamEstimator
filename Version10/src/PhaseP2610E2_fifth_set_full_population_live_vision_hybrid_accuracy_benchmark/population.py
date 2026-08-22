"""Fifth Set population + estimator truth. Reuses E.1 discovery. No beam-ID tables."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.benchmark_truth_loader import load_benchmark_truth
from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.population_discovery import discover_population


def _sha(path: Optional[Path]) -> Optional[str]:
    if path is None or not Path(path).exists() or not Path(path).is_file():
        return None
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_population(v10: Path) -> Dict[str, Any]:
    pop = discover_population(v10)
    truth = load_benchmark_truth(estimator_path=pop.get("estimator_path"))
    est_ids = []
    if truth.get("ok") and truth.get("workbook") is not None:
        est_ids = [b.beam_id for b in truth["workbook"].beams]
    model_ids = list(pop.get("model_beam_ids") or [])
    model_set = {str(x) for x in model_ids}
    est_set = {str(x) for x in est_ids}
    matched = sorted(model_set & est_set)
    missing_model = sorted(est_set - model_set)
    extra_model = sorted(model_set - est_set)
    fingerprints = {}
    if pop.get("r13_path"):
        fingerprints["r13_models"] = _sha(Path(pop["r13_path"]))
    if pop.get("estimator_path"):
        fingerprints["estimator_workbook"] = _sha(Path(pop["estimator_path"]))
    return {
        "ok": bool(pop.get("ok")) and bool(truth.get("ok")),
        "reason": None if (pop.get("ok") and truth.get("ok")) else (pop.get("reason") or "TRUTH_UNAVAILABLE"),
        "drawing_set": pop.get("drawing_set"),
        "set_key": pop.get("set_key"),
        "discovery_method": pop.get("population_source"),
        "run_root": pop.get("run_root"),
        "run_folder": pop.get("run_folder"),
        "r13_path": pop.get("r13_path"),
        "estimator_path": pop.get("estimator_path"),
        "discovered_model_beam_count": len(model_ids),
        "discovered_estimator_beam_count": len(est_ids),
        "matched_benchmark_population": len(matched),
        "missing_model_beams": missing_model,
        "extra_model_beams": extra_model,
        "model_beam_ids": model_ids,
        "estimator_beam_ids": est_ids,
        "catalog": pop.get("catalog") or {},
        "truth": truth,
        "source_fingerprints": fingerprints,
        "population": pop,
    }


__all__ = ["build_population"]
