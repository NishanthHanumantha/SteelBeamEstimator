"""Phase W.5 unit tests — Hybrid shadow adapter (no production Excel mutation)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from .paths import ensure_src_on_path

ensure_src_on_path()

from .comparison import classify_field, classify_beam, summarize_classifications
from .config import (
    AGREE,
    BENIGN_DIFFERENCE,
    EXCEL_REL,
    HYBRID_ERROR,
    HYBRID_UNAVAILABLE,
    MATERIAL_DISAGREEMENT,
    R13_REL,
    SEMANTIC_DISAGREEMENT,
    STATUS_AUTHORITATIVE_FORBIDDEN,
    STATUS_KEY_ABSENT,
    STATUS_SKIPPED_OFF,
    STEEL_SUMMARY_REL,
    T1_RENDER_REL,
)
from .cost import estimate_cost_usd
from .settings import load_settings
from .adapter import run_hybrid_shadow


def _png(size: int = 256) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + (b"\x00" * max(0, size - 8))


def _r13_model(*, count: int = 3, diameter: int = 16) -> dict:
    return {
        "beam_id": "B1",
        "top_main_bars": [
            {
                "quantity": count,
                "diameter_mm": diameter,
                "semantic_role": "MAIN",
                "piece_type": "TOP_MAIN",
            }
        ],
        "stirrups": [
            {
                "quantity": 2,
                "diameter_mm": 8,
                "bar_label": "2L-Y8@150C/C",
                "semantic_role": "STIRRUP",
            }
        ],
    }


def _plant_staging(root: Path, *, excel_bytes: bytes = b"PK\x03\x04excel-fixture") -> Path:
    (root / R13_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / T1_RENDER_REL).mkdir(parents=True, exist_ok=True)
    (root / EXCEL_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / STEEL_SUMMARY_REL).parent.mkdir(parents=True, exist_ok=True)
    catalog = {"models": {"B1": _r13_model()}}
    (root / R13_REL).write_text(json.dumps(catalog), encoding="utf-8")
    (root / T1_RENDER_REL / "B1_crop.png").write_bytes(_png())
    (root / EXCEL_REL).write_bytes(excel_bytes)
    (root / STEEL_SUMMARY_REL).write_text(
        json.dumps({"total_beams": 1, "total_bars": 3, "total_weight_kg": 12.5}),
        encoding="utf-8",
    )
    return root


def _vision_client(fail: bool = False, timeout: bool = False):
    def _client(**kwargs):
        if timeout:
            raise TimeoutError("simulated hybrid timeout")
        if fail:
            return {
                "success": False,
                "model": "mock-claude",
                "raw_text": None,
                "latency_s": 0.01,
                "retry_count": 0,
                "usage": None,
                "error": "simulated_api_failure",
                "error_type": "APIError",
                "temperature": 0,
            }
        prompt = str(kwargs.get("user_prompt") or "")
        beam_id = "B1"
        for line in prompt.splitlines():
            if line.startswith("TARGET BEAM ID:"):
                beam_id = line.split(":", 1)[1].strip()
        payload = {
            "target_beam_id": beam_id,
            "target_identified": True,
            "association_confidence": 0.91,
            "groups": [
                {
                    "physical_group_id": "G1",
                    "layer": "TOP",
                    "spec": "3-Y16",
                    "bar_count": 3,
                    "role_hypothesis": "MAIN",
                    "role_confidence": 0.9,
                    "support_scope": "FULL_SPAN",
                    "relative_length_evidence": "UNKNOWN",
                    "span_relationship": "FULL_SPAN",
                    "confidence": 0.9,
                    "evidence": "unit-test mock",
                }
            ],
            "stirrups": [
                {"spec": "2L-Y8@150C/C", "confidence": 0.8, "evidence": "unit-test mock"}
            ],
            "ambiguities": [],
            "neighbour_evidence_detected": False,
            "response_status": "OK",
        }
        return {
            "success": True,
            "model": "mock-claude",
            "raw_text": json.dumps(payload),
            "latency_s": 0.02,
            "retry_count": 0,
            "usage": {"input_tokens": 120, "output_tokens": 40},
            "error": None,
            "error_type": None,
            "temperature": 0,
        }

    return _client


class SettingsTests(unittest.TestCase):
    def test_mode_off_default(self):
        os.environ.pop("HYBRID_MODE", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        cfg = load_settings()
        self.assertEqual(cfg.mode, "off")
        self.assertEqual(cfg.api_key_status, "ABSENT")
        self.assertFalse(cfg.live_calls_allowed)

    def test_authoritative_not_enabled(self):
        self.assertFalse(load_settings().authoritative_enabled)


class ComparisonTests(unittest.TestCase):
    def test_agree_and_material(self):
        agree = classify_field(name="bar_count", vision_value=3, deterministic_value=3)
        self.assertEqual(agree["classification"], AGREE)
        material = classify_field(name="bar_count", vision_value=4, deterministic_value=3)
        self.assertEqual(material["classification"], MATERIAL_DISAGREEMENT)
        benign = classify_field(name="layer", vision_value=None, deterministic_value="TOP")
        self.assertEqual(benign["classification"], BENIGN_DIFFERENCE)
        semantic = classify_field(name="role", vision_value="MAIN", deterministic_value="EXTRA")
        self.assertEqual(semantic["classification"], SEMANTIC_DISAGREEMENT)

    def test_spec_text_benign_vs_material(self):
        same = classify_field(name="specification", vision_value="3Y16", deterministic_value="3-Y16")
        self.assertEqual(same["classification"], AGREE)
        benign = classify_field(name="specification", vision_value="3LY16", deterministic_value="3-Y16")
        self.assertEqual(benign["classification"], BENIGN_DIFFERENCE)
        material = classify_field(name="specification", vision_value="4-Y16", deterministic_value="3-Y16")
        self.assertEqual(material["classification"], MATERIAL_DISAGREEMENT)

    def test_unavailable_beam(self):
        row = classify_beam(beam_id="B1", hybrid=None, status=HYBRID_UNAVAILABLE)
        self.assertEqual(row["agreement_classification"], HYBRID_UNAVAILABLE)
        counts = summarize_classifications([row])
        self.assertEqual(counts[HYBRID_UNAVAILABLE], 1)


class CostTests(unittest.TestCase):
    def test_estimated_label(self):
        payload = estimate_cost_usd(input_tokens=1_000_000, output_tokens=0)
        self.assertEqual(payload["cost_basis"], "ESTIMATED")
        self.assertEqual(payload["estimated_cost_usd"], 3.0)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="w5_hybrid_")
        self.root = Path(self._tmp.name)
        self.excel = b"PK\x03\x04isolation-bytes-w5"
        _plant_staging(self.root, excel_bytes=self.excel)
        self._old = {
            "HYBRID_MODE": os.environ.get("HYBRID_MODE"),
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
            "HYBRID_MAX_LIVE_CALLS": os.environ.get("HYBRID_MAX_LIVE_CALLS"),
        }

    def tearDown(self):
        for key, value in self._old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def test_1_mode_off_zero_requests(self):
        os.environ["HYBRID_MODE"] = "off"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        result = run_hybrid_shadow(run_id="t-off", staging=self.root, persist=True)
        self.assertEqual(result["hybrid_status"], STATUS_SKIPPED_OFF)
        self.assertEqual(result["request_count"], 0)
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)
        self.assertFalse((self.root / "data" / "output" / "PhaseW5_production_hybrid_shadow").exists())

    def test_2_shadow_available_mock(self):
        os.environ["HYBRID_MODE"] = "shadow"
        os.environ["ANTHROPIC_API_KEY"] = "not-a-real-key"
        result = run_hybrid_shadow(
            run_id="t-shadow",
            staging=self.root,
            client_override=_vision_client(),
            persist=True,
        )
        self.assertIn(result["hybrid_status"], ("COMPLETE", "PARTIAL_BUDGET"))
        self.assertGreaterEqual(result["request_count"], 1)
        self.assertEqual(result["cost_basis"], "ESTIMATED")
        self.assertTrue(result.get("excel_unchanged"))
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)
        report = self.root / "data" / "output" / "PhaseW5_production_hybrid_shadow" / "hybrid_shadow_report.json"
        self.assertTrue(report.exists())
        beam = (result.get("beams") or [None])[0]
        self.assertIsNotNone(beam)
        self.assertIn(
            beam.get("comparison", {}).get("agreement_classification"),
            (AGREE, BENIGN_DIFFERENCE, SEMANTIC_DISAGREEMENT, MATERIAL_DISAGREEMENT, HYBRID_UNAVAILABLE, HYBRID_ERROR),
        )

    def test_3_shadow_missing_key(self):
        os.environ["HYBRID_MODE"] = "shadow"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        result = run_hybrid_shadow(run_id="t-nokey", staging=self.root, persist=True)
        self.assertEqual(result["hybrid_status"], STATUS_KEY_ABSENT)
        self.assertEqual(result["request_count"], 0)
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)

    def test_4_timeout_and_api_failure(self):
        os.environ["HYBRID_MODE"] = "shadow"
        os.environ["ANTHROPIC_API_KEY"] = "not-a-real-key"
        timeout = run_hybrid_shadow(
            run_id="t-timeout",
            staging=self.root,
            client_override=_vision_client(timeout=True),
            persist=True,
        )
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)
        self.assertTrue(timeout.get("beams"))
        failed = run_hybrid_shadow(
            run_id="t-fail",
            staging=self.root,
            client_override=_vision_client(fail=True),
            persist=True,
        )
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)
        self.assertEqual(failed["request_count"], 1)
        cls = (failed.get("beams") or [{}])[0].get("comparison", {}).get("agreement_classification")
        self.assertEqual(cls, HYBRID_UNAVAILABLE)

    def test_5_excel_isolation(self):
        os.environ["HYBRID_MODE"] = "shadow"
        os.environ["ANTHROPIC_API_KEY"] = "not-a-real-key"
        before = (self.root / EXCEL_REL).read_bytes()
        steel_before = (self.root / STEEL_SUMMARY_REL).read_text(encoding="utf-8")
        run_hybrid_shadow(
            run_id="t-iso",
            staging=self.root,
            client_override=_vision_client(),
            persist=True,
        )
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), before)
        self.assertEqual((self.root / STEEL_SUMMARY_REL).read_text(encoding="utf-8"), steel_before)

    def test_authoritative_forbidden(self):
        os.environ["HYBRID_MODE"] = "authoritative"
        result = run_hybrid_shadow(run_id="t-auth", staging=self.root, persist=True)
        self.assertEqual(result["hybrid_status"], STATUS_AUTHORITATIVE_FORBIDDEN)
        self.assertEqual(result["request_count"], 0)
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)


if __name__ == "__main__":
    unittest.main()
