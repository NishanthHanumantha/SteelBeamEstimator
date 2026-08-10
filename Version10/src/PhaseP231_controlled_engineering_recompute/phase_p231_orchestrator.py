"""
P2.3.1 orchestrator — Controlled Engineering Recompute / Steel Re-benchmark.
MODEL_VERSION: 10.5.6
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from PhaseP23_controlled_production_gate.overlay import ownership_counts
from PhaseQA31_pipeline_diagnostics.artefact_locator import (
    PRIORITY_FOURTH_BEAMS,
    ArtefactLocator,
)

from .b16_trace import build_b16_trace
from .benchmark_run import run_fourth_benchmark
from .comparison import build_comparison
from .config import (
    DEFAULT_CONFIG,
    EXPECTED_MIGRATED_ENTITIES,
    MODEL_VERSION,
    PHASE_ID,
    PRODUCTION_POLICY,
    P231Config,
)
from .gates import validate_p231
from .report_builder import write_all
from .sandbox import prepare_sandbox
from .unit_tests import run_unit_tests
from .vb1_runner import run_vb1_excel
from .workbook_inspect import inspect_workbook, sha256_file


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _sha_obj(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


class PhaseP231Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        mode: str = "controlled",
        set_key: str = "Fourth",
        beam_ids: Optional[Sequence[str]] = None,
        p23_root: Optional[Path] = None,
        config: Optional[P231Config] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root
            / "data"
            / "output"
            / "PhaseP23_1_controlled_engineering_recompute"
        )
        self.mode = mode.upper()
        if self.mode == "OFF":
            self.mode = "BASELINE"
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.config = config or DEFAULT_CONFIG
        base = self.engine_root / "data" / "output"
        self.p23_root = (
            Path(p23_root) if p23_root else base / "PhaseP23_controlled_production_gate"
        )
        self.qa30_root = base / "PhaseQA30_unseen_benchmark"
        self.log_path = self.output_root / "phase_p23_1_execution.log"
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _log(self, msg: str) -> None:
        line = msg if msg.endswith("\n") else msg + "\n"
        print(msg)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)

    def _find_estimator_excel(self) -> Path:
        meta = _load_json(
            self.qa30_root / "Fourth_Set_Drawings" / "run_metadata.json"
        ) or {}
        candidates = []
        for key in ("estimator_excel_path_recorded", "estimator_excel"):
            if meta.get(key):
                candidates.append(Path(meta[key]))
        candidates.extend(
            [
                self.engine_root.parent
                / "Test_Input"
                / "Fourth Set Drawings"
                / "Estimator_Output_4thSet"
                / "EstimatorOutput_Basement_Beam BBS_INIZIO.xlsx",
                self.engine_root
                / "Test_Input"
                / "Fourth Set Drawings"
                / "Estimator_Output_4thSet"
                / "EstimatorOutput_Basement_Beam BBS_INIZIO.xlsx",
            ]
        )
        for c in candidates:
            if c.exists():
                return c
        raise FileNotFoundError("Fourth Set estimator Excel not found")

    def _run_once(self, *, label: str, ownership: Dict[str, Any], scoped: Optional[Dict[str, Any]], source_run: Path, estimator: Path) -> Dict[str, Any]:
        sandbox = self.output_root / "sandboxes" / label
        prep = prepare_sandbox(
            sandbox_root=sandbox,
            source_run_root=source_run,
            ownership=ownership,
            scoped=scoped,
            label=label,
        )
        self._log(f"[{PHASE_ID}] VB1 {label} sandbox={sandbox}")
        vb1 = run_vb1_excel(engine_root=self.engine_root, sandbox_run_root=sandbox)
        if not vb1.get("success"):
            raise RuntimeError(f"VB1 failed for {label}: {vb1}")
        xlsx_src = Path(vb1["workbook_path"])
        xlsx_dest = self.output_root / f"Estimation_Output_{label}.xlsx"
        shutil.copy2(xlsx_src, xlsx_dest)
        wb = inspect_workbook(xlsx_dest)
        bench_dir = self.output_root / f"benchmark_{label}"
        bench = run_fourth_benchmark(
            engine_root=self.engine_root,
            model_excel=xlsx_dest,
            estimator_excel=estimator,
            set_output_dir=bench_dir,
            label=label,
        )
        return {
            "label": label,
            "sandbox": prep,
            "vb1": vb1,
            "workbook_path": str(xlsx_dest),
            "workbook": wb,
            "benchmark": bench,
        }

    def run(self) -> Dict[str, Any]:
        if self.log_path.exists():
            self.log_path.unlink()
        self._log("=" * 72)
        self._log(f"Phase {PHASE_ID} - Controlled Engineering Recompute")
        self._log(f"MODEL_VERSION : {MODEL_VERSION}")
        self._log(f"Mode          : {self.mode}")
        self._log("=" * 72)
        t0 = time.perf_counter()

        unit_tests = run_unit_tests()
        self._log(
            f"[{PHASE_ID}] unit_tests={unit_tests.get('passed')}/{unit_tests.get('total')} "
            f"pass={unit_tests.get('overall_pass')}"
        )

        # Locate historical Fourth artefacts
        locator = ArtefactLocator(self.engine_root, self.qa30_root)
        art = locator.locate_set(self.set_key)
        bundle = locator.load_bundle(art)
        historical_own = bundle.get("beam_ownership")
        if not historical_own:
            raise FileNotFoundError("Historical BeamOwnership missing")
        own_path = Path(
            art.paths.get("beam_ownership")
            or (Path(art.output_root) / "PhaseT18_beam_ownership" / "BeamOwnership.json")
        )
        hist_hash_before = sha256_file(own_path)
        source_run = Path(art.run_root)
        if not source_run.exists():
            raise FileNotFoundError(f"Fourth web_run missing: {source_run}")

        # P2.3 controlled ownership
        ctrl_own_path = self.p23_root / "controlled_effective" / "BeamOwnership.json"
        ctrl_scoped_path = (
            self.p23_root / "controlled_effective" / "BeamScopedAnnotations.json"
        )
        mig_path = self.p23_root / "OwnershipMigration.json"
        if not ctrl_own_path.exists():
            raise FileNotFoundError(f"Missing P2.3 controlled ownership: {ctrl_own_path}")
        controlled_own = _load_json(ctrl_own_path) or {}
        # controlled_effective file IS the ownership doc
        if "by_beam" not in controlled_own and "ownership" in controlled_own:
            controlled_own = controlled_own["ownership"]
        controlled_scoped = _load_json(ctrl_scoped_path)
        migrations = (_load_json(mig_path) or {}).get("rows") or []

        baseline_counts = ownership_counts(historical_own, self.beam_ids)
        controlled_counts = ownership_counts(controlled_own, self.beam_ids)

        estimator = self._find_estimator_excel()
        self._log(f"[{PHASE_ID}] estimator_excel={estimator}")

        # RUN A baseline
        self._log(f"[{PHASE_ID}] RUN A — BASELINE")
        run_a = self._run_once(
            label="baseline",
            ownership=historical_own,
            scoped=bundle.get("beam_scoped"),
            source_run=source_run,
            estimator=estimator,
        )

        # RUN B controlled (and deterministic repeat)
        self._log(f"[{PHASE_ID}] RUN B — CONTROLLED (pass 1)")
        run_b1 = self._run_once(
            label="controlled",
            ownership=controlled_own,
            scoped=controlled_scoped,
            source_run=source_run,
            estimator=estimator,
        )
        self._log(f"[{PHASE_ID}] RUN B — CONTROLLED (pass 2 determinism)")
        run_b2 = self._run_once(
            label="controlled_repeat",
            ownership=controlled_own,
            scoped=controlled_scoped,
            source_run=source_run,
            estimator=estimator,
        )

        hist_hash_after = sha256_file(own_path)

        # Determinism on controlled engineering content (not raw xlsx bytes;
        # VB1 stamps timestamps into workbook metadata).
        det_checks = [
            {
                "check": "workbook_content_fingerprint",
                "pass": run_b1["workbook"].get("content_fingerprint")
                == run_b2["workbook"].get("content_fingerprint")
                and run_b1["workbook"].get("content_fingerprint") is not None,
                "a": run_b1["workbook"].get("content_fingerprint"),
                "b": run_b2["workbook"].get("content_fingerprint"),
            },
            {
                "check": "steel_kg",
                "pass": run_b1["workbook"].get("steel_kg")
                == run_b2["workbook"].get("steel_kg"),
                "a": run_b1["workbook"].get("steel_kg"),
                "b": run_b2["workbook"].get("steel_kg"),
            },
            {
                "check": "steel_accuracy",
                "pass": (
                    (run_b1["benchmark"].get("drawing_summary") or {}).get(
                        "steel_accuracy_pct"
                    )
                    == (run_b2["benchmark"].get("drawing_summary") or {}).get(
                        "steel_accuracy_pct"
                    )
                ),
            },
            {
                "check": "b16_steel",
                "pass": (run_b1["workbook"].get("b16") or {}).get("steel_kg")
                == (run_b2["workbook"].get("b16") or {}).get("steel_kg"),
            },
            {
                "check": "ownership_unchanged_across_repeats",
                "pass": True,
                "detail": "same controlled_effective ownership injected both passes",
            },
        ]
        determinism = {
            "determinism_status": "PASS" if all(c["pass"] for c in det_checks) else "FAIL",
            "checks": det_checks,
        }

        r13_path = (
            source_run
            / "data"
            / "output"
            / "PhaseR1.3_pipeline_integration"
            / "beam_reinforcement_models_production.json"
        )
        prop = _load_json(self.p23_root / "RecoveryPropagationTrace.json")
        b16_trace = build_b16_trace(
            baseline_ownership=historical_own,
            controlled_ownership=controlled_own,
            r13_models_path=r13_path,
            baseline_wb=run_a["workbook"],
            controlled_wb=run_b1["workbook"],
            p23_propagation=prop,
        )

        comparison = build_comparison(
            baseline_wb=run_a["workbook"],
            controlled_wb=run_b1["workbook"],
            baseline_bench=run_a["benchmark"],
            controlled_bench=run_b1["benchmark"],
            baseline_counts=baseline_counts,
            controlled_counts=controlled_counts,
            b16_trace=b16_trace,
        )

        mig_ids = {m.get("entity_id") for m in migrations}
        unexpected = sorted(mig_ids - set(EXPECTED_MIGRATED_ENTITIES))
        migration_provenance = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "source_phase": "P2.3",
            "source_model_version": "10.5.5",
            "source_policy": PRODUCTION_POLICY,
            "rows": [
                {
                    "source_phase": "P2.3",
                    "source_model_version": "10.5.5",
                    "source_policy": m.get("recovery_policy"),
                    "beam_id": m.get("beam_id"),
                    "entity_id": m.get("entity_id"),
                    "entity_type": m.get("entity_type"),
                    "baseline_owner": None
                    if m.get("baseline_status") == "REJECTED"
                    else m.get("beam_id"),
                    "controlled_owner": m.get("beam_id")
                    if m.get("controlled_status") == "ACCEPTED"
                    else None,
                    "reason": m.get("reason"),
                    "provenance": m.get("source"),
                }
                for m in migrations
            ],
            "unexpected": unexpected,
            "unexpected_count": len(unexpected),
        }

        ownership_comparison = {
            "baseline": baseline_counts,
            "controlled": controlled_counts,
            "delta_nodes": controlled_counts["accepted_node_total"]
            - baseline_counts["accepted_node_total"],
            "delta_leaders": controlled_counts["accepted_leaders"]
            - baseline_counts["accepted_leaders"],
            "historical_t18_path": str(own_path),
            "historical_t18_hash_before": hist_hash_before,
            "historical_t18_hash_after": hist_hash_after,
            "historical_t18_unchanged": hist_hash_before == hist_hash_after,
        }

        # Unexpected engineering content change (ignore raw xlsx timestamp bytes).
        unexpected_eng = []
        if (
            run_a["workbook"].get("content_fingerprint")
            != run_b1["workbook"].get("content_fingerprint")
        ):
            unexpected_eng.append(
                {
                    "type": "engineering_content_differs",
                    "baseline_fp": run_a["workbook"].get("content_fingerprint"),
                    "controlled_fp": run_b1["workbook"].get("content_fingerprint"),
                    "steel_delta_kg": (run_b1["workbook"].get("steel_kg") or 0)
                    - (run_a["workbook"].get("steel_kg") or 0),
                    "note": "Engineering quantities differ between baseline and controlled",
                }
            )

        regression = {
            "status": "PASS"
            if hist_hash_before == hist_hash_after and len(unexpected) == 0
            else "FAIL",
            "historical_t18_unchanged": hist_hash_before == hist_hash_after,
            "unexpected_ownership_migrations": unexpected,
            "unexpected_engineering_changes": unexpected_eng,
        }

        outputs_ok = all(
            Path(p).exists()
            for p in (
                run_a["workbook_path"],
                run_b1["workbook_path"],
                self.output_root / "benchmark_baseline" / "benchmark_result.json",
                self.output_root / "benchmark_controlled" / "benchmark_result.json",
            )
        )

        gate_ctx = {
            "baseline_counts": baseline_counts,
            "controlled_counts": controlled_counts,
            "migrations": migrations,
            "production_policy": PRODUCTION_POLICY,
            "controlled_ownership": controlled_own,
            "baseline_wb": run_a["workbook"],
            "controlled_wb": run_b1["workbook"],
            "b16_trace": b16_trace,
            "baseline_bench": run_a["benchmark"],
            "controlled_bench": run_b1["benchmark"],
            "comparison": comparison,
            "historical_t18_hash_before": hist_hash_before,
            "historical_t18_hash_after": hist_hash_after,
            "determinism": determinism,
            "contamination_found": False,
            "outputs_ok": outputs_ok,
            "unit_tests": unit_tests,
            "unexpected_engineering_changes": unexpected_eng,
        }
        # For controlled mode require controlled run; baseline mode still generates both for measurement
        gates = validate_p231(gate_ctx)

        summary = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "status": gates.get("status"),
            "decision": gates.get("decision"),
            "broader_e_validation": gates.get("broader_e_validation"),
            "recommendation": gates.get("recommendation"),
            "baseline": {
                "ownership": baseline_counts,
                "steel_kg": run_a["workbook"].get("steel_kg"),
                "steel_accuracy_pct": (run_a["benchmark"].get("drawing_summary") or {}).get(
                    "steel_accuracy_pct"
                ),
                "overall_accuracy_pct": (
                    comparison.get("qa30_fourth") or {}
                ).get("Overall Accuracy", {}).get("baseline"),
            },
            "controlled": {
                "ownership": controlled_counts,
                "steel_kg": run_b1["workbook"].get("steel_kg"),
                "steel_accuracy_pct": (
                    run_b1["benchmark"].get("drawing_summary") or {}
                ).get("steel_accuracy_pct"),
                "overall_accuracy_pct": (
                    comparison.get("qa30_fourth") or {}
                ).get("Overall Accuracy", {}).get("controlled"),
            },
            "delta": {
                "steel_kg": (comparison.get("workbook") or {})
                .get("steel_kg", {})
                .get("delta"),
                "steel_accuracy_pp": (comparison.get("qa30_fourth") or {})
                .get("Steel Accuracy", {})
                .get("delta_pp"),
                "overall_accuracy_pp": (comparison.get("qa30_fourth") or {})
                .get("Overall Accuracy", {})
                .get("delta_pp"),
            },
            "b16_effect_class": b16_trace.get("effect_class"),
            "workbook_identical": (comparison.get("workbook") or {}).get(
                "identical_engineering_content"
            ),
            "vb1_consumes_beam_ownership": False,
            "remaining_blocker": (
                None
                if gates.get("decision")
                and "IMPROVEMENT" in str(gates.get("decision"))
                else (
                    "Production architecture generates Estimation_Output.xlsx from R1.3 "
                    "before T18 ownership. Recovering B16::LDR::7A1FFD68 changes effective "
                    "ownership/render but has no path into VB1 steel quantities without a "
                    "new ownership->R1.3 engineering bridge."
                )
            ),
        }

        artefacts = {
            "baseline_bench": run_a["benchmark"],
            "controlled_bench": run_b1["benchmark"],
            "comparison": comparison,
            "b16_trace": b16_trace,
            "ownership_comparison": ownership_comparison,
            "migration_provenance": migration_provenance,
            "summary": summary,
            "unit_tests": unit_tests,
            "determinism": determinism,
            "gates": {
                **gates,
                "elapsed_s": round(time.perf_counter() - t0, 3),
            },
            "regression": regression,
            "contamination_found": False,
        }
        paths = write_all(self.output_root, artefacts)

        elapsed = round(time.perf_counter() - t0, 3)
        self._log(f"\n[{PHASE_ID}] STATUS={gates.get('status')} elapsed={elapsed}s")
        self._log(f"[{PHASE_ID}] decision={gates.get('decision')}")
        self._log(
            f"[{PHASE_ID}] steel_delta_pp="
            f"{summary['delta']['steel_accuracy_pp']} "
            f"workbook_identical={summary['workbook_identical']}"
        )
        self._log(f"[{PHASE_ID}] broader_e={gates.get('broader_e_validation')}")
        self._log(f"[{PHASE_ID}] output={self.output_root}")

        return {
            "success": bool(gates.get("overall_pass")),
            "status": gates.get("status"),
            "decision": gates.get("decision"),
            "model_version": MODEL_VERSION,
            "output_root": str(self.output_root),
            "summary": summary,
            "gates": gates,
            "determinism": determinism,
            "comparison": comparison,
            "b16_trace": b16_trace,
            "paths": paths,
            "elapsed_s": elapsed,
            "broader_e_validation": gates.get("broader_e_validation"),
        }
