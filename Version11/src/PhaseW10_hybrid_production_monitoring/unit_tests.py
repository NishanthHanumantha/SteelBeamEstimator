"""Phase W.10 unit tests — monitoring only, no live Claude, no Lightsail."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

ensure_src_on_path()

from PhaseW5_production_hybrid_shadow.config import EXCEL_REL, R13_REL, STEEL_SUMMARY_REL
from PhaseW6_hybrid_production_authority.config import PRE_HYBRID_FILENAME, R13_DIR_REL
from PhaseW6_hybrid_production_authority.orchestrator import run_production_hybrid
from PhaseW6_hybrid_production_authority.unit_tests import _authority_client, _plant, _settings

from .config import (
    BEAM_REVIEW_FILENAME,
    CROP_DECISION_NO_CHANGE,
    DETERMINISTIC_AGREEMENT,
    DUP_COMPATIBILITY_FALLBACK,
    DUP_NOT_DUPLICATE,
    MONITOR_FILENAME,
    OUTPUT_DIRNAME,
    SEMANTIC_CORRECTION,
)
from .monitor import build_monitor, engineering_overwrites
from .sanitize import sanitize
from .writer import write_run_monitor


def _png(tag: bytes) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + tag + (b"\x00" * 200)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _plant_w10_run(root: Path) -> Path:
    w6 = root / "data/output/PhaseW6_hybrid_semantic_resolution"
    w5 = root / "data/output/PhaseW5_production_hybrid_shadow"
    ev = w6 / "hybrid_evidence"
    (root / EXCEL_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / EXCEL_REL).write_bytes(b"PK\x03\x04w10")
    _write_json(
        root / STEEL_SUMMARY_REL,
        {"total_weight_kg": 10.0, "total_beams": 2, "total_bars": 4, "calculation_method": "IS_456_DETERMINISTIC"},
    )
    models = [
        {
            "beam_id": "B1",
            "geometry": {"span_mm": 4000},
            "top_main_bars": [{"bar_id": "a", "cut_length_mm": 1000, "quantity": 3}],
            "stirrups": [{"bar_id": "s", "quantity": 10, "cut_length_mm": 800, "spacing_mm": 150}],
        },
        {
            "beam_id": "B2",
            "geometry": {"span_mm": 3000},
            "top_main_bars": [{"bar_id": "b", "cut_length_mm": 900, "quantity": 2}],
            "stirrups": [{"bar_id": "t", "quantity": 8, "cut_length_mm": 700, "spacing_mm": 150}],
        },
    ]
    _write_json(root / R13_REL, {"models": models})
    _write_json(root / R13_DIR_REL / PRE_HYBRID_FILENAME, {"models": json.loads(json.dumps(models))})
    coverage = {
        "total_production_beams": 2,
        "hybrid_eligible": 2,
        "p2610_primary_evidence": 1,
        "native_t1_crop": 0,
        "generated_fallback_crop": 1,
        "visual_context_unavailable": 0,
        "deterministic_fallback": 0,
        "claude_attempted": 2,
        "claude_success": 2,
        "claude_failure": 0,
        "unexplained": 0,
        "identity_ok": True,
        "beams": [
            {
                "beam_id": "B1",
                "crop_path": "P2610_PRIMARY_EVIDENCE",
                "hybrid_outcome": "CLAUDE_SUCCESS",
                "evidence_class": "PRIMARY",
                "visual_source": "P2610B1_ADAPTIVE_CONTEXT_DETAIL",
                "hybrid_status": "OBSERVED",
                "unexplained": False,
            },
            {
                "beam_id": "B2",
                "crop_path": "W6_GENERATED_FALLBACK_CROP",
                "hybrid_outcome": "CLAUDE_SUCCESS",
                "evidence_class": "FALLBACK",
                "visual_source": "W6_ENVELOPE_RENDER",
                "hybrid_status": "OBSERVED",
                "unexplained": False,
            },
        ],
    }
    _write_json(w6 / "hybrid_coverage.json", coverage)
    _write_json(
        w6 / "hybrid_observability.json",
        {
            "hybrid_mode": "production",
            "model": "mock-claude",
            "classification": "HYBRID_SUCCESS",
            "claude_invocation_count": 2,
            "successful_invocation_count": 2,
            "failed_invocation_count": 0,
            "timeout_count": 0,
            "fallback_count": 0,
            "hybrid_latency_s": 12.5,
            "coverage": coverage,
        },
    )
    (ev / "B1" / "context").mkdir(parents=True)
    (ev / "B1" / "detail").mkdir(parents=True)
    (ev / "B2" / "context").mkdir(parents=True)
    (ev / "B2" / "detail").mkdir(parents=True)
    (ev / "B1" / "context" / "selected.png").write_bytes(_png(b"ctx-b1"))
    (ev / "B1" / "detail" / "selected.png").write_bytes(_png(b"det-b1"))
    dup = _png(b"same-w6")
    (ev / "B2" / "context" / "selected.png").write_bytes(dup)
    (ev / "B2" / "detail" / "selected.png").write_bytes(dup)
    _write_json(
        ev / "B1" / "evidence_manifest.json",
        {
            "beam_id": "B1",
            "evidence_class": "PRIMARY",
            "visual_source": "P2610B1_ADAPTIVE_CONTEXT_DETAIL",
            "fallback_status": "NONE",
            "completeness_status": "VISION_READY",
            "selected_context_evidence": {"source_phase": "B.1"},
            "selected_detail_evidence": {"source_phase": "B.1"},
        },
    )
    _write_json(
        ev / "B2" / "evidence_manifest.json",
        {
            "beam_id": "B2",
            "evidence_class": "FALLBACK",
            "visual_source": "W6_ENVELOPE_RENDER",
            "fallback_status": "FALLBACK",
            "fallback_reason": "P2610_PRIMARY_NOT_USABLE",
            "completeness_status": "W6_COMPATIBILITY",
            "selected_context_evidence": {"source_phase": "W.6"},
            "selected_detail_evidence": {"source_phase": "W.6"},
        },
    )
    _write_json(
        w5 / "hybrid_shadow_report.json",
        {
            "beam_count": 2,
            "request_count": 2,
            "input_tokens": 100,
            "output_tokens": 20,
            "estimated_cost_usd": 0.001,
            "cost_basis": "ESTIMATED",
            "hybrid_latency_s": 12.5,
            "model": "mock-claude",
            "agreement_counts": {"AGREE": 1, "SEMANTIC_DISAGREEMENT": 1, "comparisons": 2},
            "beams": [
                {
                    "beam_id": "B1",
                    "called": True,
                    "hybrid_status": "OBSERVED",
                    "context_path": str(ev / "B1" / "context" / "selected.png"),
                    "detail_path": str(ev / "B1" / "detail" / "selected.png"),
                    "usage": {"latency_s": 5.0, "input_tokens": 50, "output_tokens": 10, "cost_basis": "ESTIMATED"},
                    "comparison": {"agreement_classification": "AGREE"},
                },
                {
                    "beam_id": "B2",
                    "called": True,
                    "hybrid_status": "OBSERVED",
                    "context_path": str(ev / "B2" / "context" / "selected.png"),
                    "detail_path": str(ev / "B2" / "detail" / "selected.png"),
                    "usage": {"latency_s": 7.0, "input_tokens": 50, "output_tokens": 10, "cost_basis": "ESTIMATED"},
                    "comparison": {"agreement_classification": "SEMANTIC_DISAGREEMENT"},
                },
            ],
        },
    )
    return root


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="w10_mon_")
        self.root = _plant_w10_run(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_w10_02_monitor_artefact(self):
        mon = write_run_monitor(staging=self.root, run_id="t-w10")
        self.assertIsNotNone(mon)
        path = self.root / "data/output" / OUTPUT_DIRNAME / MONITOR_FILENAME
        self.assertTrue(path.is_file())
        reviews = self.root / "data/output" / OUTPUT_DIRNAME / BEAM_REVIEW_FILENAME
        self.assertTrue(reviews.is_file())

    def test_w10_03_05_coverage_identity(self):
        mon = build_monitor(self.root, run_id="t-w10")
        self.assertEqual(mon["hybrid_eligible"], 2)
        self.assertEqual(mon["primary_evidence_count"], 1)
        self.assertEqual(mon["native_t1_evidence_count"], 0)
        self.assertEqual(mon["compatibility_fallback_count"], 1)
        self.assertEqual(mon["unavailable_count"], 0)
        self.assertEqual(mon["unexplained_count"], 0)
        self.assertTrue(mon["identity_ok"])
        self.assertEqual(
            mon["hybrid_eligible"],
            mon["primary_evidence_count"]
            + mon["native_t1_evidence_count"]
            + mon["compatibility_fallback_count"]
            + mon["unavailable_count"],
        )

    def test_w10_04_06_explicit_classification_and_provenance(self):
        write_run_monitor(staging=self.root, run_id="t-w10")
        payload = json.loads(
            (self.root / "data/output" / OUTPUT_DIRNAME / BEAM_REVIEW_FILENAME).read_text(encoding="utf-8")
        )
        by_id = {b["beam_id"]: b for b in payload["beams"]}
        self.assertEqual(by_id["B1"]["selection_classification"], "PRIMARY")
        self.assertEqual(by_id["B2"]["selection_classification"], "FALLBACK")
        self.assertTrue(by_id["B1"]["context_sha"])
        self.assertTrue(by_id["B1"]["detail_sha"])
        self.assertTrue(by_id["B1"]["images_distinct"])
        self.assertEqual(by_id["B1"]["context_source_phase"], "B.1")
        self.assertEqual(by_id["B1"]["detail_source_phase"], "B.1")

    def test_w10_07_duplicate_analysis(self):
        write_run_monitor(staging=self.root, run_id="t-w10")
        payload = json.loads(
            (self.root / "data/output" / OUTPUT_DIRNAME / BEAM_REVIEW_FILENAME).read_text(encoding="utf-8")
        )
        by_id = {b["beam_id"]: b for b in payload["beams"]}
        self.assertEqual(by_id["B1"]["duplicate_reason"], DUP_NOT_DUPLICATE)
        self.assertFalse(by_id["B2"]["images_distinct"])
        self.assertEqual(by_id["B2"]["duplicate_reason"], DUP_COMPATIBILITY_FALLBACK)
        self.assertEqual(by_id["B2"]["duplicate_outcome"], "RELIABLE_RESOLUTION")

    def test_w10_08_semantic_classifications(self):
        mon = build_monitor(self.root, run_id="t-w10")
        self.assertEqual(mon["semantic_agreement_count"], 1)
        self.assertEqual(mon["semantic_correction_count"], 1)
        self.assertEqual(mon["material_disagreement_count"], 0)
        self.assertIn(DETERMINISTIC_AGREEMENT, mon["semantic_counts"])
        self.assertIn(SEMANTIC_CORRECTION, mon["semantic_counts"])

    def test_w10_11_engineering_protection(self):
        prot = engineering_overwrites(self.root)
        self.assertEqual(prot["cut_length_overwrites"], 0)
        self.assertEqual(prot["geometry_overwrites"], 0)
        self.assertEqual(prot["stirrup_quantity_overwrites"], 0)
        self.assertEqual(prot["deterministic_engineering_overwrite_count"], 0)

    def test_w10_12_secret_sanitizer(self):
        dirty = {"token": "sk-ant-secretvalue", "api_key": "SHOULD_DROP", "ok": "plain"}
        clean = sanitize(dirty)
        self.assertNotIn("api_key", clean)
        self.assertNotIn("sk-ant-secretvalue", json.dumps(clean))
        self.assertEqual(clean["ok"], "plain")
        mon = write_run_monitor(staging=self.root, run_id="t-w10")
        blob = json.dumps(mon)
        self.assertNotIn("sk-ant-", blob.lower())

    def test_w10_crop_no_change(self):
        mon = build_monitor(self.root, run_id="t-w10")
        self.assertEqual(mon["crop_improvement"]["decision"], CROP_DECISION_NO_CHANGE)

    def test_w10_09_writer_failure_returns_none(self):
        with patch(
            "PhaseW10_hybrid_production_monitoring.writer.build_monitor",
            side_effect=RuntimeError("boom"),
        ):
            self.assertIsNone(write_run_monitor(staging=self.root, run_id="t-fail"))
        self.assertTrue((self.root / EXCEL_REL).is_file())


class OrchestratorSafetyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="w10_orch_")
        self.root = Path(self._tmp.name)
        _plant(self.root, excel=b"PK\x03\x04w10-excel")
        self._old = {
            "HYBRID_MODE": os.environ.get("HYBRID_MODE"),
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
        }

    def tearDown(self):
        for key, value in self._old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def test_w10_01_w9_hybrid_still_runs(self):
        result = run_production_hybrid(
            run_id="t-w10-arch",
            staging=self.root,
            settings=_settings(mode="production", key="PRESENT"),
            client_override=_authority_client(),
            persist=True,
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["production_authority_applied"])
        self.assertTrue((self.root / EXCEL_REL).is_file())
        self.assertTrue(
            (self.root / "data/output" / OUTPUT_DIRNAME / MONITOR_FILENAME).is_file()
        )

    def test_w10_09_monitor_cannot_fail_excel(self):
        with patch(
            "PhaseW10_hybrid_production_monitoring.writer.write_run_monitor",
            side_effect=RuntimeError("monitor-down"),
        ):
            result = run_production_hybrid(
                run_id="t-w10-iso",
                staging=self.root,
                settings=_settings(mode="production", key="PRESENT"),
                client_override=_authority_client(),
                persist=True,
            )
        self.assertTrue(result["ok"])
        self.assertTrue((self.root / EXCEL_REL).is_file())
        data = json.loads((self.root / R13_REL).read_text(encoding="utf-8"))
        self.assertEqual(data["models"][0]["top_main_bars"][0]["cut_length_mm"], 4200.0)

    def test_w10_10_api_failure_still_excel(self):
        def _fail(**kwargs):
            raise TimeoutError("api")

        before = (self.root / EXCEL_REL).read_bytes()
        result = run_production_hybrid(
            run_id="t-w10-fail",
            staging=self.root,
            settings=_settings(mode="production", key="PRESENT"),
            client_override=_fail,
            persist=True,
        )
        self.assertFalse(result["production_authority_applied"])
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
