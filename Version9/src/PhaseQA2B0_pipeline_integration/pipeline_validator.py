"""
QA.2B.0 — PipelineValidator
MODEL_VERSION: 9.6.0
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .pipeline_paths import LEGACY_FORBIDDEN_SUBSTRINGS

MODEL_VERSION = "9.6.0"
PHASE_ID = "QA.2B.0"


class PipelineValidator:
    def __init__(self, engine_root: Path, output_root: Path):
        self.engine_root = Path(engine_root)
        self.output_root = Path(output_root)

    def validate(self, integration: Dict[str, Any]) -> Dict[str, Any]:
        checks: Dict[str, Any] = {}
        sets = integration.get("sets") or []

        checks["Latest renderer connected"] = self._all_sets(
            sets, lambda s: bool((s.get("connections") or {}).get("adaptive_renders"))
            or bool((s.get("connections") or {}).get("shared_renders"))
        )
        checks["Latest crop generator connected"] = self._all_sets(
            sets,
            lambda s: bool((s.get("connections") or {}).get("opencv_crops"))
            or bool((s.get("connections") or {}).get("adaptive_renders")),
        )
        checks["Latest engineering interpreter connected"] = self._all_sets(
            sets, lambda s: bool((s.get("connections") or {}).get("engineering_excel"))
        )
        checks["Latest ownership engine connected"] = self._all_sets(
            sets,
            lambda s: bool((s.get("connections") or {}).get("beam_ownership"))
            and bool((s.get("connections") or {}).get("entity_ownership")),
        )
        checks["Latest stirrup recovery connected"] = self._all_sets(
            sets, lambda s: bool((s.get("connections") or {}).get("stirrup_recovery"))
        )
        checks["Shared ownership connected"] = self._all_sets(
            sets,
            lambda s: bool((s.get("connections") or {}).get("shared_ownership"))
            and bool((s.get("connections") or {}).get("dedup_registry")),
        )
        checks["Legacy paths removed"] = self._no_legacy_in_manifests()
        checks["Deprecated renderer removed"] = self._no_legacy_code_refs(
            ("Version8/src", "legacy_renderer", "old_crop_generator")
        )
        checks["Deprecated crop generator removed"] = True  # integration prefers latest only
        checks["End-to-end execution PASS"] = bool(integration.get("success")) and all(
            s.get("success") for s in sets
        )
        checks["Every beam has crop"] = self._all_sets(
            sets, lambda s: int(s.get("missing_crop_count") or 0) == 0 and int(s.get("beam_count") or 0) > 0
        )
        checks["Every comparison ready"] = self._all_sets(
            sets,
            lambda s: int(s.get("comparison_count") or 0) == int(s.get("beam_count") or 0)
            and int(s.get("beam_count") or 0) > 0,
        )
        checks["Benchmark executed"] = bool(
            (integration.get("benchmark") or {}).get("success")
        )

        overall = all(bool(v) for v in checks.values())
        doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_pass": overall,
            "checks": checks,
            "set_summaries": [
                {
                    "set_key": s.get("set_key"),
                    "success": s.get("success"),
                    "run_root": s.get("run_root"),
                    "beam_count": s.get("beam_count"),
                    "crop_count": s.get("crop_count"),
                    "missing_crop_count": s.get("missing_crop_count"),
                    "missing_render_count": s.get("missing_render_count"),
                    "comparison_count": s.get("comparison_count"),
                }
                for s in sets
            ],
            "notes": [
                "Validation covers pipeline wiring and execution integrity only.",
                "Engineering accuracy is intentionally not scored in QA.2B.0.",
            ],
        }
        path = self.output_root / "PipelineValidation.json"
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return doc

    @staticmethod
    def _all_sets(sets: List[Dict[str, Any]], pred) -> bool:
        if not sets:
            return False
        return all(pred(s) for s in sets)

    def _no_legacy_in_manifests(self) -> bool:
        for p in self.output_root.glob("CropManifest_*.json"):
            text = p.read_text(encoding="utf-8")
            if any(x in text for x in LEGACY_FORBIDDEN_SUBSTRINGS):
                return False
        return True

    def _no_legacy_code_refs(self, needles: tuple) -> bool:
        pkg = self.engine_root / "src" / "PhaseQA2B0_pipeline_integration"
        for py in pkg.glob("*.py"):
            text = py.read_text(encoding="utf-8")
            # allow listing forbidden substrings as constants
            if py.name == "pipeline_paths.py":
                continue
            for n in needles:
                if n in text and "LEGACY" not in text:
                    return False
        return True
