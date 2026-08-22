"""Dynamic Second–Sixth population + estimator truth. First Set excluded. No count tables."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.benchmark_truth_loader import load_benchmark_truth
from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.population_discovery import load_r13_catalog

from .config import INCLUDED_SET_KEYS, QA30_DIRNAME, TRUTH_ESTIMATOR, TRUTH_NONE, TRUTH_VALIDATED
from .sets import classify_folder_name, drawing_set_label, is_excluded_set, name_matches_set, tokens_for


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _sha(path: Optional[Path]) -> Optional[str]:
    if path is None or not Path(path).exists() or not Path(path).is_file():
        return None
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _repo_root(v10: Path) -> Path:
    return Path(v10).resolve().parent


def iter_web_run_roots(v10: Path) -> List[Path]:
    roots: List[Path] = []
    seen = set()
    primary = Path(v10) / "data" / "web_runs"
    if primary.exists() and primary.is_dir():
        roots.append(primary)
        seen.add(primary.resolve())
    repo = _repo_root(v10)
    if repo.exists():
        for child in sorted(repo.iterdir()):
            if not child.is_dir():
                continue
            web = child / "data" / "web_runs"
            if web.exists() and web.is_dir() and web.resolve() not in seen:
                roots.append(web)
                seen.add(web.resolve())
    return roots


def discover_web_run_for_set(v10: Path, set_key: str) -> Dict[str, Any]:
    named: List[Path] = []
    for web in iter_web_run_roots(v10):
        try:
            children = list(web.iterdir())
        except OSError:
            continue
        for p in children:
            if not p.is_dir():
                continue
            low = p.name.lower()
            if not low.startswith("qa2_"):
                continue
            if name_matches_set(p.name, set_key):
                named.append(p)
    if not named:
        return {"ok": False, "reason": "WEB_RUN_UNAVAILABLE", "run_root": None, "set_key": set_key}
    run = sorted(named, key=lambda p: p.name)[-1]
    return {
        "ok": True,
        "reason": None,
        "run_root": str(run),
        "set_key": set_key,
        "discovery": "WEB_RUN_NAME_TOKEN",
        "folder_name": run.name,
        "web_root": str(run.parent),
    }


def discover_estimator_workbook(v10: Path, set_key: str) -> Optional[Path]:
    test_input = _repo_root(v10) / "Test_Input"
    if not test_input.exists():
        return None
    toks = tokens_for(set_key)
    folders: List[Path] = []
    for child in sorted(test_input.iterdir()):
        if not child.is_dir():
            continue
        if not name_matches_set(child.name, set_key):
            continue
        folders.append(child)
        try:
            level1 = list(child.iterdir())
        except OSError:
            continue
        for nested in level1:
            if nested.is_dir() and "estimator" in nested.name.lower():
                folders.append(nested)
            if nested.is_dir():
                try:
                    for nested2 in nested.iterdir():
                        if nested2.is_dir() and "estimator" in nested2.name.lower():
                            folders.append(nested2)
                except OSError:
                    continue
    candidates: List[Path] = []
    seen = set()
    for folder in folders:
        try:
            files = list(folder.glob("*.xlsx"))
        except OSError:
            continue
        for path in files:
            if path.name.startswith("~$"):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda p: (p.stat().st_size, p.name), reverse=True)
    return candidates[0]


def _validated_context(v10: Path, set_key: str) -> Optional[str]:
    qa30 = Path(v10) / "data" / "output" / QA30_DIRNAME / "Generalization_Benchmark_Report.xlsx"
    if set_key in ("Fourth", "Fifth", "Sixth") and qa30.exists():
        return str(qa30)
    if set_key in ("Second", "Third"):
        repo = _repo_root(v10)
        for child in sorted(repo.iterdir()):
            cand = (
                child
                / "data"
                / "output"
                / "PhaseQA2B1_production_regeneration"
                / "GroundTruth_Benchmark_Report.xlsx"
            )
            if cand.exists() and cand.is_file():
                return str(cand)
    return None


def build_set_population(v10: Path, set_key: str) -> Dict[str, Any]:
    if is_excluded_set(set_key):
        return {"ok": False, "reason": "SET_EXCLUDED", "set_key": set_key, "model_beam_ids": []}
    run = discover_web_run_for_set(v10, set_key)
    catalog = load_r13_catalog(run.get("run_root"))
    est = discover_estimator_workbook(v10, set_key)
    truth = load_benchmark_truth(estimator_path=str(est) if est else None)
    est_ids = []
    if truth.get("ok") and truth.get("workbook") is not None:
        est_ids = [b.beam_id for b in truth["workbook"].beams]
    model_ids = list(catalog.get("beam_ids") or [])
    model_set = {str(x) for x in model_ids}
    est_set = {str(x) for x in est_ids}
    matched = sorted(model_set & est_set)
    unmatched_model = sorted(model_set - est_set)
    unmatched_gt = sorted(est_set - model_set)
    validated = _validated_context(v10, set_key)
    truth_source = TRUTH_ESTIMATOR if truth.get("ok") else TRUTH_NONE
    fingerprints = {}
    if catalog.get("path"):
        fingerprints["r13_models"] = _sha(Path(catalog["path"]))
    if est:
        fingerprints["estimator_workbook"] = _sha(est)
    return {
        "ok": bool(run.get("ok")) and bool(catalog.get("ok")) and bool(truth.get("ok")),
        "reason": None
        if (run.get("ok") and catalog.get("ok") and truth.get("ok"))
        else (run.get("reason") or catalog.get("reason") or "TRUTH_UNAVAILABLE"),
        "drawing_set": drawing_set_label(set_key),
        "set_key": set_key,
        "discovery_method": run.get("discovery"),
        "run_root": run.get("run_root"),
        "run_folder": run.get("folder_name"),
        "web_root": run.get("web_root"),
        "r13_path": catalog.get("path"),
        "estimator_path": str(est) if est else None,
        "truth_source": truth_source,
        "truth_context": TRUTH_VALIDATED if validated else None,
        "truth_context_path": validated,
        "discovered_model_beam_count": len(model_ids),
        "discovered_estimator_beam_count": len(est_ids),
        "matched_benchmark_population": len(matched),
        "unmatched_model_beams": unmatched_model,
        "unmatched_estimator_beams": unmatched_gt,
        "model_beam_ids": model_ids,
        "estimator_beam_ids": est_ids,
        "catalog": catalog,
        "truth": truth,
        "source_fingerprints": fingerprints,
        "web_run": run,
    }


def discover_all_sets(v10: Path) -> Dict[str, Any]:
    by_set: Dict[str, Dict[str, Any]] = {}
    excluded = []
    test_input = _repo_root(v10) / "Test_Input"
    if test_input.exists():
        for child in sorted(test_input.iterdir()):
            if not child.is_dir():
                continue
            key = classify_folder_name(child.name)
            if key and is_excluded_set(key):
                excluded.append({"set_key": key, "folder": child.name, "reason": "SET_EXCLUDED"})
    for set_key in INCLUDED_SET_KEYS:
        by_set[set_key] = build_set_population(v10, set_key)
    ok = all(row.get("ok") for row in by_set.values())
    return {
        "ok": ok,
        "included_set_keys": list(INCLUDED_SET_KEYS),
        "excluded": excluded,
        "by_set": by_set,
        "model_beam_total": sum(int(r.get("discovered_model_beam_count") or 0) for r in by_set.values()),
        "estimator_beam_total": sum(int(r.get("discovered_estimator_beam_count") or 0) for r in by_set.values()),
        "matched_total": sum(int(r.get("matched_benchmark_population") or 0) for r in by_set.values()),
    }


def slim_set_population(pop: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in pop.items() if k not in ("catalog", "truth")}


__all__ = [
    "build_set_population",
    "discover_all_sets",
    "discover_estimator_workbook",
    "discover_web_run_for_set",
    "iter_web_run_roots",
    "slim_set_population",
]
