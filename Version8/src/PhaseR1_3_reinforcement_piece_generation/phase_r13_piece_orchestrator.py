"""
Phase R.1.3 Piece Generation Orchestrator
MODEL_VERSION: 8.5.0
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import time
import types
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.5.0"


def _load_pkg(pkg_name: str, pkg_dir: pathlib.Path, subs: List[str]):
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(pkg_dir)]
        pkg.__package__ = pkg_name
        sys.modules[pkg_name] = pkg
    for sub in subs:
        key = f"{pkg_name}.{sub}"
        if key in sys.modules:
            del sys.modules[key]
        spec = importlib.util.spec_from_file_location(key, pkg_dir / f"{sub}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[key] = mod
        spec.loader.exec_module(mod)


def _run(cmd: List[str], cwd: pathlib.Path) -> int:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, cwd=str(cwd)).returncode


class PhaseR13PieceOrchestrator:

    def __init__(self, v7_root: Optional[pathlib.Path] = None):
        self.v7 = v7_root or pathlib.Path(__file__).resolve().parents[2]
        self._src = pathlib.Path(__file__).parent

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.3 - Reinforcement Piece Generation Engine")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("=" * 72)
        t0 = time.perf_counter()

        _load_pkg("PhaseR13Piece", self._src, [
            "piece_model",
            "piece_geometry",
            "piece_quantity",
            "piece_generator",
            "piece_validator",
            "piece_confidence",
            "piece_traceability",
            "piece_builder",
            "piece_exporter",
            "piece_phase_validators",
        ])

        print("\n[1/7] Loading Intents + Details ...")
        intents = self._load_intents()
        details = self._load_details(intents)
        print(f"      Intents={len(intents)} Details={len(details)}")

        print("\n[2/7] Generating ReinforcementPieces ...")
        Builder = sys.modules["PhaseR13Piece.piece_builder"].PieceBuilder
        ctx = self._load_ctx()
        pieces, payload = Builder(self.v7, ctx).build(details)
        stir_zones = sum(
            1 for p in pieces
            if str(p.piece_type).startswith("STIRRUP_ZONE")
        )
        print(
            f"      Pieces={len(pieces)} types={payload.get('piece_types')} "
            f"stirrup_zones={stir_zones}"
        )

        print("\n[3/7] Rebuilding R.1.3 pipeline integration + V.B.1 ...")
        _run([sys.executable, "Run_PY/run_phase_r13_pipeline_integration.py"], self.v7)
        vb1 = self.v7 / "Run_PY/run_phase_vb1_production_output_completion.py"
        if vb1.exists():
            _run([sys.executable, str(vb1.relative_to(self.v7))], self.v7)

        print("\n[4/7] Mapping + validation ...")
        mapping = self._build_mapping(pieces)
        builder_uses = self._check_builder_uses_pieces()
        validators = sys.modules["PhaseR13Piece.piece_phase_validators"]
        regression = validators.RegressionPieceValidator().validate(
            self.v7, len(pieces), len(mapping)
        )
        validation = validators.PiecePhaseValidator().validate(
            details,
            pieces,
            mapping,
            payload.get("validation") or {},
            payload.get("geometry_summary") or {},
            regression,
            builder_uses,
            stir_zones,
        )
        print(f"      Rules {validation['passed']}/{validation['total']} passed")

        recommendation = "A" if validation.get("overall_passed") else "B"

        result: Dict[str, Any] = {
            "model_version": MODEL_VERSION,
            "phase": "R.1.3_PIECE",
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "recommendation": recommendation,
            "pieces": [p.to_dict() for p in pieces],
            "payload": payload,
            "mapping": mapping,
            "regression": regression,
            "validation": validation,
            "builder_uses_pieces": builder_uses,
        }

        print("\n[5/7] Exporting artefacts ...")
        Exporter = sys.modules["PhaseR13Piece.piece_exporter"].PieceExporter
        exporter = Exporter(self.v7)
        report_md = exporter.generate_report(result)
        exports = exporter.export_all(result, report_md)

        print("\n[6/7] Summary")
        print(f"      Pieces: {len(pieces)}")
        print(f"      Recommendation: {recommendation}")

        print("\n[7/7] Done")
        print("=" * 72)

        result["status"] = "PASS" if validation.get("overall_passed") else "WARN"
        result["export_paths"] = exports
        return result

    def _load_intents(self) -> list:
        r12c = self.v7 / "src/PhaseR1_2C_engineering_intent_resolution"
        _load_pkg("PhaseR12C", r12c, [
            "engineering_intent_model",
            "engineering_role_resolver",
            "engineering_diameter_resolver",
            "engineering_extent_resolver",
            "engineering_consistency_engine",
            "engineering_intent_resolution_engine",
        ])
        Engine = sys.modules[
            "PhaseR12C.engineering_intent_resolution_engine"
        ].EngineeringIntentResolutionEngine
        intents, _ = Engine(self.v7).resolve_all()
        return intents

    def _load_details(self, intents: list) -> list:
        r12d = self.v7 / "src/PhaseR1_2D_reinforcement_detailing"
        _load_pkg("PhaseR12D", r12d, [
            "reinforcement_detail_model",
            "stirrup_zone_interpreter",
            "support_zone_interpreter",
            "continuity_interpreter",
            "development_length_engine",
            "curtailment_engine",
            "side_face_reinforcement_detector",
            "detail_consistency_validator",
            "detail_confidence_engine",
            "reinforcement_detail_builder",
            "reinforcement_detail_engine",
        ])
        Engine = sys.modules[
            "PhaseR12D.reinforcement_detail_engine"
        ].ReinforcementDetailEngine
        details, _ = Engine(self.v7, self._load_ctx()).build_from_intents(intents)
        return details

    def _load_ctx(self) -> Dict[str, Any]:
        try:
            r2a = self.v7 / "src/PhaseR.2A_engineering_context"
            if "PhaseR2A" not in sys.modules:
                pkg = types.ModuleType("PhaseR2A")
                pkg.__path__ = [str(r2a)]
                sys.modules["PhaseR2A"] = pkg
            key = "PhaseR2A.engineering_context_parser"
            if key not in sys.modules:
                spec = importlib.util.spec_from_file_location(
                    key, r2a / "engineering_context_parser.py"
                )
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = "PhaseR2A"
                sys.modules[key] = mod
                spec.loader.exec_module(mod)
            loader, _, _ = sys.modules[key].parse_engineering_context(self.v7)
            return (loader.summary() or {}) if loader else {}
        except Exception:
            return {}

    def _build_mapping(self, pieces) -> List[Dict[str, Any]]:
        mapping = [
            {
                "piece_id": p.piece_id,
                "detail_id": p.detail_id,
                "intent_id": p.intent_id,
                "beam_id": p.beam_id,
                "piece_type": p.piece_type,
                "cut_length_mm": p.cut_length_mm,
                "confidence": p.confidence,
            }
            for p in pieces
        ]
        eng = (
            self.v7
            / "data/output/PhaseR1.3_pipeline_integration"
            / "engineering_bar_models.json"
        )
        if eng.exists():
            data = json.loads(eng.read_text(encoding="utf-8"))
            for bm in data.get("beams") or []:
                for bar in bm.get("bars") or []:
                    meta = bar.get("engineering_metadata") or {}
                    pid = meta.get("piece_id")
                    if pid:
                        mapping.append({
                            "piece_id": pid,
                            "detail_id": meta.get("detail_id"),
                            "intent_id": meta.get("intent_id"),
                            "beam_id": bm.get("beam_id"),
                            "source": "production_engineering_bar",
                            "physical_member_id": meta.get("physical_member_id"),
                        })
        return mapping

    def _check_builder_uses_pieces(self) -> bool:
        path = (
            self.v7
            / "src/PhaseR1.3_pipeline_integration"
            / "engineering_bar_builder.py"
        )
        text = path.read_text(encoding="utf-8", errors="ignore")
        return "_bars_from_pieces" in text and "_resolve_pieces" in text
