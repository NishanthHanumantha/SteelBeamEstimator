"""
QA.2B.1 — ProductionRegenerator
MODEL_VERSION: 9.6.1

Snapshots prior Estimation_Output.xlsx workbooks, then runs the full integrated
production pipeline (no reuse) for every complete Test_Input drawing set.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .workbook_utils import (
    resolve_latest_workbook,
    set_key_from_drawing_name,
    snapshot_workbook,
)

MODEL_VERSION = "9.6.1"
PHASE_ID = "QA.2B.1"
SET_KEYS = ("First", "Second", "Third")


class ProductionRegenerator:
    def __init__(self, engine_root: Path, output_root: Path):
        self.engine_root = Path(engine_root)
        self.output_root = Path(output_root)
        self.web_runs = self.engine_root / "data" / "web_runs"
        self.output_root.mkdir(parents=True, exist_ok=True)

    def snapshot_prior_workbooks(self) -> Dict[str, Any]:
        """Capture hashes/timestamps of workbooks that QA.2B.0 reused."""
        by_set: Dict[str, Any] = {}
        for key in SET_KEYS:
            path = resolve_latest_workbook(self.web_runs, key)
            by_set[key] = snapshot_workbook(path, label=f"prior_{key}")
        doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": "Baseline workbooks before QA.2B.1 regeneration",
            "by_set": by_set,
        }
        path = self.output_root / "PriorWorkbookSnapshot.json"
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        print(f"[QA.2B.1] Prior workbook snapshot -> {path}")
        for key, snap in by_set.items():
            print(
                f"  {key}: hash={(snap.get('sha256') or '')[:16]} "
                f"mtime={snap.get('mtime_utc')}"
            )
        return doc

    def regenerate_all(self, *, test_input: Optional[Path] = None) -> Dict[str, Any]:
        """
        Run ProductionPipelineRunner for each complete drawing set.
        Creates NEW web_run folders and NEW Estimation_Output.xlsx files.
        """
        import importlib.util
        import sys

        qa2_dir = self.engine_root / "src" / "PhaseQA.2_multi_drawing_benchmark"
        for name in ("drawing_set_discoverer", "pipeline_runner"):
            full = f"_qa2b1_{name}"
            if full in sys.modules:
                continue
            spec = importlib.util.spec_from_file_location(full, qa2_dir / f"{name}.py")
            mod = importlib.util.module_from_spec(spec)
            sys.modules[full] = mod
            sys.modules[name] = mod
            spec.loader.exec_module(mod)  # type: ignore[union-attr]

        disc_mod = sys.modules["_qa2b1_drawing_set_discoverer"]
        pipe_mod = sys.modules["_qa2b1_pipeline_runner"]
        test_input = Path(test_input) if test_input else self.engine_root.parent / "Test_Input"

        print(f"[QA.2B.1] Discovering drawing sets under {test_input}")
        sets = disc_mod.DrawingSetDiscoverer(test_input).discover()
        complete = [ds for ds in sets if ds.is_complete]
        if not complete:
            return {
                "success": False,
                "error": f"No complete drawing sets under {test_input}",
                "sets": [],
            }

        runner = pipe_mod.ProductionPipelineRunner(self.engine_root)
        results: List[Dict[str, Any]] = []
        t0 = time.perf_counter()

        for i, ds in enumerate(complete, 1):
            key = set_key_from_drawing_name(ds.name)
            print(f"\n[QA.2B.1] === [{i}/{len(complete)}] REGENERATE {ds.name} ({key}) ===")
            print("  Fresh pipeline - no workbook reuse")
            t_set = time.perf_counter()
            pipe = runner.run(
                ds.name, ds.general_notes, ds.framing, ds.reinforcement
            )
            elapsed = round(time.perf_counter() - t_set, 2)
            excel = pipe.model_excel
            snap = snapshot_workbook(excel, label=f"new_{key}")
            results.append(
                {
                    "drawing_set": ds.name,
                    "set_key": key,
                    "success": bool(pipe.success) and bool(excel and Path(excel).exists()),
                    "pipeline_elapsed_s": elapsed,
                    "pipeline": pipe.to_dict(),
                    "workbook": snap,
                    "estimator_excel": str(ds.estimator_excel),
                    "reused": False,
                }
            )
            print(
                f"  pipeline_success={pipe.success} elapsed={elapsed}s "
                f"excel={excel}"
            )
            if not pipe.success:
                print(f"  ERROR: {pipe.error}")

        return {
            "success": all(r.get("success") for r in results),
            "model_version": MODEL_VERSION,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "sets": results,
            "reuse_existing_model": False,
        }
