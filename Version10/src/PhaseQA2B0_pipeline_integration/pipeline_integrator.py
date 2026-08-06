"""
QA.2B.0 — PipelineIntegrator
MODEL_VERSION: 9.6.0

Wires latest production / Track1 visual outputs into the benchmark spine.
Does not change engineering, render, crop, or accuracy algorithms.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pipeline_paths import (
    CROP_PREFERENCE,
    LATEST_ARTEFACTS,
    artefact_path,
    list_beam_ids_from_envelopes,
    resolve_beam_crop,
    resolve_latest_web_run,
)
from .track1_chain_runner import run_track1_visual_chain

MODEL_VERSION = "9.6.0"
PHASE_ID = "QA.2B.0"

BENCHMARK_SETS = (
    ("First", "First Set Drawings"),
    ("Second", "Second Set Drawings"),
    ("Third", "Third Set Drawings"),
)


class PipelineIntegrator:
    def __init__(self, engine_root: Path, output_root: Optional[Path] = None):
        self.engine_root = Path(engine_root)
        self.web_runs = self.engine_root / "data" / "web_runs"
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root / "data" / "output" / "PhaseQA2B0_pipeline_integration"
        )
        self.output_root.mkdir(parents=True, exist_ok=True)

    def integrate_all(
        self,
        *,
        force_track1: bool = False,
        run_benchmark: bool = True,
    ) -> Dict[str, Any]:
        set_results: List[Dict[str, Any]] = []
        for set_key, display in BENCHMARK_SETS:
            set_results.append(
                self.integrate_set(
                    set_key,
                    display_name=display,
                    force_track1=force_track1,
                )
            )

        benchmark: Dict[str, Any] = {"skipped": True}
        if run_benchmark:
            benchmark = self._run_qa2a_reuse()

        doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_root": str(self.engine_root),
            "sets": set_results,
            "benchmark": benchmark,
            "success": all(s.get("success") for s in set_results)
            and bool(benchmark.get("success", not run_benchmark)),
        }
        (self.output_root / "IntegrationResult.json").write_text(
            json.dumps(doc, indent=2), encoding="utf-8"
        )
        return doc

    def integrate_set(
        self,
        set_key: str,
        *,
        display_name: str = "",
        force_track1: bool = False,
    ) -> Dict[str, Any]:
        run_root = resolve_latest_web_run(self.web_runs, set_key)
        if run_root is None:
            return {
                "set_key": set_key,
                "display_name": display_name,
                "success": False,
                "error": "no_qa2_web_run",
            }

        print(f"\n[QA.2B.0] === {set_key}: {run_root.name} ===")
        chain = run_track1_visual_chain(
            self.engine_root, run_root, force=force_track1, ensure_envelopes=True
        )
        beams = list(chain.get("processable_beam_ids") or [])
        if not beams:
            beams = list_beam_ids_from_envelopes(run_root)
        skipped_null = list(chain.get("skipped_null_extent") or [])

        crop_manifest: List[Dict[str, Any]] = []
        missing_crop: List[str] = []
        missing_render: List[str] = []
        for bid in beams:
            hit = resolve_beam_crop(run_root, bid)
            if hit is None:
                missing_crop.append(bid)
                missing_render.append(bid)
                crop_manifest.append(
                    {
                        "beam_id": bid,
                        "path": None,
                        "source": None,
                        "comparison_ready": False,
                    }
                )
            else:
                is_render = "render" in (hit.get("source") or "")
                if not is_render and hit.get("source") == "opencv_crop":
                    # opencv crop counts as crop; check dedicated render separately
                    t182 = (
                        run_root
                        / "data"
                        / "output"
                        / "PhaseT182_adaptive_render_extent"
                        / "RenderedBeams"
                        / f"{bid}_render.png"
                    )
                    t183 = (
                        run_root
                        / "data"
                        / "output"
                        / "PhaseT183_shared_engineering_ownership"
                        / "RenderedBeams"
                        / f"{bid}_render.png"
                    )
                    if not t182.exists() and not t183.exists():
                        missing_render.append(bid)
                crop_manifest.append({**hit, "comparison_ready": True})

        manifest_path = self.output_root / f"CropManifest_{set_key}.json"
        manifest_doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "set_key": set_key,
            "run_root": str(run_root),
            "beam_count": len(beams),
            "crops_resolved": sum(1 for c in crop_manifest if c.get("path")),
            "missing_crop": missing_crop,
            "missing_render": missing_render,
            "skipped_null_extent": skipped_null,
            "preference_order": [s for s, _ in CROP_PREFERENCE],
            "by_beam": crop_manifest,
            "legacy_paths_forbidden": True,
        }
        manifest_path.write_text(json.dumps(manifest_doc, indent=2), encoding="utf-8")

        connections = self._connection_map(run_root)
        success = (
            bool(chain.get("success"))
            and len(beams) > 0
            and len(missing_crop) == 0
            and bool(connections.get("engineering_excel"))
            and bool(connections.get("stirrup_recovery"))
            and bool(connections.get("adaptive_renders") or connections.get("opencv_crops"))
        )
        return {
            "set_key": set_key,
            "display_name": display_name,
            "run_root": str(run_root),
            "success": success,
            "track1_chain": chain,
            "beam_count": len(beams),
            "crop_count": sum(1 for c in crop_manifest if c.get("path")),
            "missing_crop_count": len(missing_crop),
            "missing_render_count": len(missing_render),
            "missing_crop": missing_crop,
            "missing_render": missing_render,
            "skipped_null_extent": skipped_null,
            "crop_manifest": str(manifest_path),
            "connections": connections,
            "comparison_count": sum(1 for c in crop_manifest if c.get("comparison_ready")),
        }

    def _connection_map(self, run_root: Path) -> Dict[str, bool]:
        out: Dict[str, bool] = {}
        for logical, rel in LATEST_ARTEFACTS.items():
            p = Path(run_root) / "data" / "output" / rel
            if p.is_dir():
                out[logical] = p.exists() and any(p.iterdir())
            else:
                out[logical] = p.exists()
        return out

    def _run_qa2a_reuse(self) -> Dict[str, Any]:
        """Execute QA.2A via official runner (no metric changes; reuse model Excels)."""
        import subprocess
        import sys

        print("\n[QA.2B.0] Running QA.2A ground-truth benchmark (--reuse-existing-model)...")
        script = self.engine_root / "Run_PY" / "run_phase_qa2a_ground_truth_benchmark.py"
        try:
            proc = subprocess.run(
                [sys.executable, str(script), "--reuse-existing-model"],
                cwd=str(self.engine_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3600,
            )
            tail = ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-3000:]
            ok = proc.returncode == 0
            if not ok:
                print(tail)
            return {
                "skipped": False,
                "success": ok,
                "exit_code": proc.returncode,
                "output_tail": tail,
                "note": "QA.2A metrics unchanged; reused existing model Excels",
            }
        except Exception as exc:  # noqa: BLE001
            return {"skipped": False, "success": False, "error": str(exc)}
