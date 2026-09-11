"""Phase W.11 unit tests — bounded Hybrid reliability (no live Claude)."""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from PhaseW5_production_hybrid_shadow.config import (
    EXCEL_REL,
    HYBRID_UNAVAILABLE,
    R13_REL,
    STEEL_SUMMARY_REL,
)
from PhaseW5_production_hybrid_shadow.settings import load_settings
from PhaseW5_production_hybrid_shadow.unit_tests import _plant_staging, _vision_client
from PhaseW5_production_hybrid_shadow.adapter import run_hybrid_shadow
from PhaseW6_hybrid_production_authority.orchestrator import run_production_hybrid
from PhaseW6_hybrid_production_authority.unit_tests import _plant as _plant_w6
from PhaseW6_hybrid_production_authority.unit_tests import _settings as _w6_settings

from .bounded import TimeoutExpired, run_with_timeout
from .config import STATUS_VISION_TIMEOUT
from .progress import load_progress, progress_path, write_progress


class W11ReliabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(prefix="w11_", ignore_cleanup_errors=True)
        self.root = Path(self._tmpdir.name)
        os.environ["HYBRID_MODE"] = "production"
        os.environ["ANTHROPIC_API_KEY"] = "not-a-real-key"
        os.environ["HYBRID_PER_CALL_TIMEOUT_S"] = "0.4"
        os.environ["HYBRID_MAX_RETRIES"] = "1"
        os.environ["HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS"] = "0.5"
        os.environ.pop("HYBRID_EVIDENCE_TIMEOUT_SECONDS", None)

    def tearDown(self) -> None:
        os.environ["HYBRID_MODE"] = "off"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self._tmpdir.cleanup()

    def test_w11_02_simulated_timeout(self) -> None:
        staging = _plant_staging(self.root)
        result = run_hybrid_shadow(
            run_id="t-timeout",
            staging=staging,
            client_override=_vision_client(timeout=True),
            persist=True,
        )
        self.assertTrue(result.get("beams"))
        row = result["beams"][0]
        self.assertEqual(row.get("skip_reason"), STATUS_VISION_TIMEOUT)
        self.assertEqual(row.get("hybrid_status"), HYBRID_UNAVAILABLE)
        self.assertEqual((staging / EXCEL_REL).read_bytes()[:4], b"PK\x03\x04")

    def test_w11_03_hanging_client_is_bounded(self) -> None:
        def hang() -> None:
            time.sleep(8)

        t0 = time.perf_counter()
        with self.assertRaises(TimeoutExpired):
            run_with_timeout(hang, 0.25)
        self.assertLess(time.perf_counter() - t0, 3.0)

        def hanging_client(**_kwargs):
            time.sleep(8)
            return {"success": False}

        staging = _plant_staging(self.root)
        t1 = time.perf_counter()
        result = run_hybrid_shadow(
            run_id="t-hang",
            staging=staging,
            client_override=hanging_client,
            persist=True,
        )
        self.assertLess(time.perf_counter() - t1, 4.0)
        self.assertEqual(result["beams"][0].get("skip_reason"), STATUS_VISION_TIMEOUT)
        self.assertGreaterEqual(int(result.get("timeout_count") or 0), 1)

    def test_w11_04_05_one_beam_timeout_others_continue(self) -> None:
        staging = _plant_staging(self.root)
        catalog = json.loads((staging / R13_REL).read_text(encoding="utf-8"))
        from PhaseW5_production_hybrid_shadow.unit_tests import _png, _r13_model

        catalog["models"]["B2"] = _r13_model()
        catalog["models"]["B2"]["beam_id"] = "B2"
        (staging / R13_REL).write_text(json.dumps(catalog), encoding="utf-8")
        (staging / "data/output/PhaseT1_geometric_stirrup_evidence/opencv_renders/B2_crop.png").write_bytes(_png())

        def mixed(**kwargs):
            prompt = str(kwargs.get("user_prompt") or "")
            if "B1" in prompt:
                time.sleep(8)
            return _vision_client()(**kwargs)

        os.environ["HYBRID_TOTAL_BEAM_TIMEOUT_SECONDS"] = "0.4"
        result = run_hybrid_shadow(
            run_id="t-partial",
            staging=staging,
            client_override=mixed,
            persist=True,
        )
        statuses = {row["beam_id"]: row.get("skip_reason") or row.get("hybrid_status") for row in result["beams"]}
        self.assertEqual(statuses.get("B1"), STATUS_VISION_TIMEOUT)
        self.assertIn("B2", statuses)
        self.assertNotEqual(statuses.get("B2"), STATUS_VISION_TIMEOUT)

    def test_w11_06_all_unavailable(self) -> None:
        staging = _plant_staging(self.root)
        result = run_hybrid_shadow(
            run_id="t-all-fail",
            staging=staging,
            client_override=_vision_client(fail=True),
            persist=True,
        )
        self.assertEqual(result["request_count"], 1)
        self.assertEqual(
            (result.get("beams") or [{}])[0].get("comparison", {}).get("agreement_classification"),
            HYBRID_UNAVAILABLE,
        )

    def test_w11_07_network_exception(self) -> None:
        def boom(**_kwargs):
            raise ConnectionError("simulated network")

        staging = _plant_staging(self.root)
        result = run_hybrid_shadow(
            run_id="t-net",
            staging=staging,
            client_override=boom,
            persist=True,
        )
        self.assertEqual(result["beams"][0].get("error_type"), "ConnectionError")

    def test_w11_08_evidence_timeout_helper(self) -> None:
        def hang() -> str:
            time.sleep(5)
            return "done"

        with self.assertRaises(TimeoutExpired):
            run_with_timeout(hang, 0.2)

    def test_w11_09_progress_and_no_secrets(self) -> None:
        write_progress(
            self.root,
            run_id="r1",
            phase="CLAUDE_VISION",
            beam_id="B12",
            index=3,
            total=18,
            extra_fields={"note": "sk-ant-should-not-remain"},
        )
        data = load_progress(self.root)
        self.assertIsNotNone(data)
        text = progress_path(self.root).read_text(encoding="utf-8")
        self.assertNotIn("sk-ant-", text)
        self.assertEqual(data["beam_id"], "B12")
        self.assertIn("Processing beam", data["label"])

    def test_w11_10_pipeline_fallback_keeps_excel(self) -> None:
        staging = _plant_w6(self.root)
        result = run_production_hybrid(
            run_id="t-w6-timeout",
            staging=staging,
            settings=_w6_settings(mode="production", key="PRESENT"),
            client_override=_vision_client(timeout=True),
            persist=True,
        )
        self.assertTrue((staging / EXCEL_REL).is_file())
        self.assertTrue((staging / STEEL_SUMMARY_REL).is_file())
        self.assertIn(result.get("classification"), ("HYBRID_FALLBACK_USED", "HYBRID_UNAVAILABLE", "HYBRID_SUCCESS", "HYBRID_API_ERROR"))

    def test_w11_11_normal_hybrid_regression(self) -> None:
        staging = _plant_w6(self.root)
        result = run_production_hybrid(
            run_id="t-ok",
            staging=staging,
            settings=_w6_settings(mode="production", key="PRESENT"),
            client_override=_vision_client(),
            persist=True,
        )
        self.assertTrue(result.get("ok"))
        self.assertGreaterEqual(int(result.get("claude_invocation_count") or 0), 1)
        self.assertTrue((staging / EXCEL_REL).is_file())

    def test_w11_12_settings_and_mode_off(self) -> None:
        os.environ["HYBRID_MODE"] = "off"
        cfg = load_settings()
        self.assertEqual(cfg.mode, "off")
        self.assertGreater(cfg.per_call_timeout_s, 0)
        self.assertGreaterEqual(cfg.max_retries, 0)
        staging = _plant_w6(self.root)
        result = run_production_hybrid(
            run_id="t-off",
            staging=staging,
            settings=_w6_settings(mode="off"),
            persist=True,
        )
        self.assertEqual(result.get("hybrid_status"), "SKIPPED_MODE_OFF")
        self.assertEqual(int(result.get("claude_invocation_count") or 0), 0)


if __name__ == "__main__":
    unittest.main()
