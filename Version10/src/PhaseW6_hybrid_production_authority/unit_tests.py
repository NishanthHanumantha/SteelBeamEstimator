"""Phase W.6 unit tests — Hybrid production authority (no live Claude)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

ensure_src_on_path()

from PhaseW5_production_hybrid_shadow.config import (
    EXCEL_REL,
    R13_REL,
    STATUS_AUTHORITATIVE_FORBIDDEN,
    STATUS_KEY_ABSENT,
    STATUS_SKIPPED_OFF,
    STEEL_SUMMARY_REL,
    T1_RENDER_REL,
)
from PhaseW5_production_hybrid_shadow.settings import HybridSettings, load_settings
from PhaseW5_production_hybrid_shadow.unit_tests import _png, _vision_client

from .config import COVERAGE_FILENAME, OBSERVABILITY_FILENAME, OUTPUT_DIRNAME, PRE_HYBRID_FILENAME, R13_DIR_REL
from .coverage import (
    CROP_T1_NATIVE,
    CROP_UNAVAILABLE,
    CROP_W6_FALLBACK,
    OUT_CLAUDE_FAILURE,
    OUT_CLAUDE_SUCCESS,
    OUT_FALLBACK,
    build_coverage,
)
from .handoff import apply_beam_handoff, apply_production_handoff
from .orchestrator import run_production_hybrid


def _settings(*, mode: str, key: str = "PRESENT", calls: int = 0, wall: float = 0.0) -> HybridSettings:
    return HybridSettings(
        mode=mode,
        api_key_status=key,
        model_override="mock-claude",
        max_live_calls=calls,
        max_wall_s=wall,
        per_call_timeout_s=120.0,
        dotenv_override=None,
    )


def _r13_model(*, count: int = 3, diameter: int = 16, cut: float = 4200.0) -> dict:
    return {
        "beam_id": "B1",
        "geometry": {"span_mm": 4000, "depth_mm": 450, "width_mm": 230},
        "top_main_bars": [
            {
                "bar_id": "R13-B1-TOP_MAIN-aaaaaa",
                "quantity": count,
                "diameter_mm": diameter,
                "semantic_role": "TOP_MAIN",
                "piece_type": "TOP_MAIN",
                "bar_label": f"{count}-Y{diameter}",
                "cut_length_mm": cut,
                "spacing_mm": None,
            }
        ],
        "stirrups": [
            {
                "bar_id": "R13-B1-STIRRUP-bbbbbb",
                "quantity": 22,
                "diameter_mm": 8,
                "bar_label": "2L-Y8@150C/C",
                "semantic_role": "STIRRUP",
                "cut_length_mm": 1100,
                "spacing_mm": 150,
            }
        ],
        "spacer_bars": [],
        "top_extra_bars": [],
        "bottom_main_bars": [],
        "bottom_extra_bars": [],
        "side_face_reinforcement": [],
    }


def _plant(root: Path, *, excel: bytes = b"PK\x03\x04w6-excel") -> Path:
    (root / R13_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / T1_RENDER_REL).mkdir(parents=True, exist_ok=True)
    (root / EXCEL_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / STEEL_SUMMARY_REL).parent.mkdir(parents=True, exist_ok=True)
    catalog = {"models": [_r13_model()]}
    (root / R13_REL).write_text(json.dumps(catalog), encoding="utf-8")
    (root / T1_RENDER_REL / "B1_crop.png").write_bytes(_png())
    (root / EXCEL_REL).write_bytes(excel)
    (root / STEEL_SUMMARY_REL).write_text(
        json.dumps({"total_beams": 1, "total_bars": 3, "total_weight_kg": 12.5}),
        encoding="utf-8",
    )
    return root


def _authority_client():
    """Vision disagrees on count/diameter so the handoff is observable."""

    def _client(**kwargs):
        payload = {
            "target_beam_id": "B1",
            "target_identified": True,
            "association_confidence": 0.94,
            "groups": [
                {
                    "physical_group_id": "G1",
                    "layer": "TOP",
                    "spec": "4-Y20",
                    "bar_count": 4,
                    "role_hypothesis": "MAIN",
                    "role_confidence": 0.93,
                    "support_scope": "FULL_SPAN",
                    "relative_length_evidence": "UNKNOWN",
                    "span_relationship": "FULL_SPAN",
                    "confidence": 0.93,
                    "evidence": "w6-authority-mock",
                }
            ],
            "stirrups": [
                {"spec": "2L-Y10@150C/C", "confidence": 0.85, "evidence": "w6-authority-mock"}
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
            "usage": {"input_tokens": 80, "output_tokens": 30},
            "error": None,
            "error_type": None,
            "temperature": 0,
        }

    return _client


class SettingsModeTests(unittest.TestCase):
    def setUp(self):
        self._old = {k: os.environ.get(k) for k in ("HYBRID_MODE", "ANTHROPIC_API_KEY", "HYBRID_MAX_LIVE_CALLS", "HYBRID_MAX_WALL_S")}

    def tearDown(self):
        for key, value in self._old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_production_defaults_unlimited(self):
        os.environ["HYBRID_MODE"] = "production"
        os.environ.pop("HYBRID_MAX_LIVE_CALLS", None)
        os.environ.pop("HYBRID_MAX_WALL_S", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        cfg = load_settings()
        self.assertEqual(cfg.mode, "production")
        self.assertEqual(cfg.max_live_calls, 0)
        self.assertEqual(cfg.max_wall_s, 0.0)
        self.assertEqual(cfg.public_dict()["production_authority"], "semantic_only")

    def test_off_default(self):
        os.environ.pop("HYBRID_MODE", None)
        cfg = load_settings()
        self.assertEqual(cfg.mode, "off")


class HandoffUnitTests(unittest.TestCase):
    def test_vision_patches_count_diameter_not_cut_length(self):
        model = _r13_model()
        hybrid = {
            "beam_id": "B1",
            "reinforcement_groups": [
                {
                    "group_id": "G01",
                    "origin": "MATCHED",
                    "bar_count": {"value": 4, "source": "VISION"},
                    "diameter": {"value": 20, "source": "VISION"},
                    "specification": {"value": "4-Y20", "source": "VISION"},
                    "role": {"value": "MAIN", "source": "VISION"},
                    "layer": {"value": "TOP", "source": "VISION"},
                    "support_scope": {"value": "FULL_SPAN", "source": "VISION"},
                    "provenance": {"deterministic_id": "G01"},
                }
            ],
            "stirrups": {"items": []},
        }
        ledger = apply_beam_handoff(model=model, hybrid_semantic=hybrid)
        bar = model["top_main_bars"][0]
        self.assertEqual(bar["quantity"], 4)
        self.assertEqual(bar["diameter_mm"], 20)
        self.assertEqual(bar["cut_length_mm"], 4200.0)
        self.assertTrue(any(row.get("action") == "PATCHED" for row in ledger))
        self.assertTrue(bar.get("hybrid_semantic_handoff", {}).get("applied"))

    def test_vision_only_not_materialized(self):
        model = _r13_model()
        hybrid = {
            "reinforcement_groups": [
                {
                    "group_id": "VG99",
                    "origin": "VISION_ONLY_GROUP",
                    "bar_count": {"value": 2, "source": "VISION"},
                    "provenance": {},
                }
            ],
            "stirrups": {"items": []},
        }
        apply_beam_handoff(model=model, hybrid_semantic=hybrid)
        self.assertEqual(len(model["top_main_bars"]), 1)
        self.assertEqual(model["top_main_bars"][0]["quantity"], 3)

    def test_stirrup_quantity_and_cut_preserved(self):
        model = _r13_model()
        hybrid = {
            "reinforcement_groups": [],
            "stirrups": {
                "items": [
                    {
                        "origin": "MATCHED",
                        "semantic_identification": {
                            "value": "2L-Y10@150C/C",
                            "source": "VISION",
                        },
                        "engineering_calculation_reference": {
                            "specification": "2L-Y8@150C/C",
                            "cut_length_mm": 1100,
                        },
                    }
                ]
            },
        }
        apply_beam_handoff(model=model, hybrid_semantic=hybrid)
        st = model["stirrups"][0]
        self.assertEqual(st["quantity"], 22)
        self.assertEqual(st["cut_length_mm"], 1100)
        self.assertEqual(st["spacing_mm"], 150)
        self.assertEqual(st["diameter_mm"], 10)
        self.assertEqual(st["bar_label"], "2L-Y10@150C/C")


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="w6_hybrid_")
        self.root = Path(self._tmp.name)
        self.excel = b"PK\x03\x04isolation-w6"
        _plant(self.root, excel=self.excel)
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

    def test_w6_01_off_no_claude_r13_unchanged(self):
        os.environ["HYBRID_MODE"] = "off"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        before = (self.root / R13_REL).read_text(encoding="utf-8")
        result = run_production_hybrid(
            run_id="t-off",
            staging=self.root,
            settings=_settings(mode="off", key="ABSENT"),
            persist=True,
        )
        self.assertEqual(result["classification"], "HYBRID_SKIPPED_OFF")
        self.assertEqual(result["request_count"], 0)
        self.assertFalse(result["production_authority_applied"])
        self.assertEqual((self.root / R13_REL).read_text(encoding="utf-8"), before)
        self.assertFalse((self.root / "data" / "output" / OUTPUT_DIRNAME).exists())

    def test_w6_04_production_handoff_consumed(self):
        result = run_production_hybrid(
            run_id="t-auth",
            staging=self.root,
            settings=_settings(mode="production", key="PRESENT"),
            client_override=_authority_client(),
            persist=True,
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["production_authority_applied"])
        self.assertEqual(result["classification"], "HYBRID_SUCCESS")
        data = json.loads((self.root / R13_REL).read_text(encoding="utf-8"))
        bar = data["models"][0]["top_main_bars"][0]
        self.assertEqual(bar["quantity"], 4)
        self.assertEqual(bar["diameter_mm"], 20)
        self.assertEqual(bar["cut_length_mm"], 4200.0)
        pre = self.root / R13_DIR_REL / PRE_HYBRID_FILENAME
        self.assertTrue(pre.exists())
        pre_bar = json.loads(pre.read_text(encoding="utf-8"))["models"][0]["top_main_bars"][0]
        self.assertEqual(pre_bar["quantity"], 3)
        self.assertEqual(pre_bar["diameter_mm"], 16)
        obs = json.loads(
            (self.root / "data" / "output" / OUTPUT_DIRNAME / OBSERVABILITY_FILENAME).read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(obs["production_authority_applied"])
        self.assertIn("api_key_configured", obs)
        blob = json.dumps(obs)
        self.assertNotIn("sk-ant-", blob.lower())

    def test_w6_05_engineering_fields_untouched(self):
        run_production_hybrid(
            run_id="t-eng",
            staging=self.root,
            settings=_settings(mode="production", key="PRESENT"),
            client_override=_authority_client(),
            persist=True,
        )
        data = json.loads((self.root / R13_REL).read_text(encoding="utf-8"))
        model = data["models"][0]
        self.assertEqual(model["geometry"]["span_mm"], 4000)
        self.assertEqual(model["top_main_bars"][0]["cut_length_mm"], 4200.0)
        self.assertEqual(model["stirrups"][0]["quantity"], 22)
        self.assertEqual(model["stirrups"][0]["cut_length_mm"], 1100)
        self.assertEqual(model["stirrups"][0]["spacing_mm"], 150)

    def test_w6_06_missing_key_fallback(self):
        before = (self.root / R13_REL).read_text(encoding="utf-8")
        result = run_production_hybrid(
            run_id="t-nokey",
            staging=self.root,
            settings=_settings(mode="production", key="ABSENT"),
            persist=True,
        )
        self.assertEqual(result["classification"], "HYBRID_UNAVAILABLE")
        self.assertFalse(result["production_authority_applied"])
        self.assertEqual(result["request_count"], 0)
        self.assertEqual((self.root / R13_REL).read_text(encoding="utf-8"), before)

    def test_w6_06_api_failure_no_fabricated_result(self):
        before = (self.root / R13_REL).read_text(encoding="utf-8")
        result = run_production_hybrid(
            run_id="t-fail",
            staging=self.root,
            settings=_settings(mode="production", key="PRESENT"),
            client_override=_vision_client(fail=True),
            persist=True,
        )
        self.assertFalse(result["production_authority_applied"])
        self.assertEqual((self.root / R13_REL).read_text(encoding="utf-8"), before)
        self.assertIn(
            result["classification"],
            ("HYBRID_FALLBACK_USED", "HYBRID_API_ERROR", "HYBRID_UNAVAILABLE"),
        )

    def test_w6_07_isolation_under_run_tree(self):
        run_production_hybrid(
            run_id="t-iso",
            staging=self.root,
            settings=_settings(mode="production", key="PRESENT"),
            client_override=_authority_client(),
            persist=True,
        )
        out = self.root / "data" / "output" / OUTPUT_DIRNAME
        self.assertTrue((out / "hybrid_resolution.json").is_file())
        self.assertTrue((out / "hybrid_observability.json").is_file())
        self.assertTrue((out / "hybrid_handoff_ledger.json").is_file())
        self.assertTrue((out / COVERAGE_FILENAME).is_file())
        cov = json.loads((out / COVERAGE_FILENAME).read_text(encoding="utf-8"))
        self.assertTrue(cov.get("identity_ok"))
        self.assertEqual(cov.get("unexplained"), 0)
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)

    def test_coverage_identity_no_unexplained_gap(self):
        shadow = {
            "request_count": 2,
            "beams": [
                {
                    "beam_id": "B1",
                    "visual_source": "T1_OPENCV_CROP",
                    "visual_available": True,
                    "hybrid_status": "OBSERVED",
                    "called": True,
                },
                {
                    "beam_id": "B2",
                    "visual_source": "W6_ENVELOPE_RENDER",
                    "visual_available": True,
                    "hybrid_status": "OBSERVED",
                    "called": True,
                },
                {
                    "beam_id": "B3",
                    "visual_source": "T1_OPENCV_CROP",
                    "visual_available": False,
                    "hybrid_status": "SKIPPED",
                    "skip_reason": "RENDER_MISSING",
                    "called": False,
                },
                {
                    "beam_id": "B4",
                    "visual_source": "W6_ENVELOPE_RENDER",
                    "visual_available": True,
                    "hybrid_status": "HYBRID_ERROR",
                    "skip_reason": "LIVE_CALL_EXCEPTION",
                    "called": True,
                },
            ],
        }
        cov = build_coverage(
            mode="production",
            beam_ids=["B1", "B2", "B3", "B4"],
            shadow_result=shadow,
            visual_prep={"rendered": 1},
        )
        self.assertEqual(cov["hybrid_eligible"], 4)
        self.assertEqual(cov["native_t1_crop"], 1)
        self.assertEqual(cov["generated_fallback_crop"], 2)
        self.assertEqual(cov["visual_context_unavailable"], 1)
        self.assertEqual(
            cov["hybrid_eligible"],
            cov["native_t1_crop"]
            + cov["generated_fallback_crop"]
            + cov["visual_context_unavailable"],
        )
        self.assertEqual(cov["claude_success"], 2)
        self.assertEqual(cov["claude_failure"], 1)
        self.assertEqual(cov["deterministic_fallback"], 1)
        self.assertEqual(
            cov["hybrid_eligible"],
            cov["claude_success"] + cov["claude_failure"] + cov["deterministic_fallback"],
        )
        self.assertEqual(cov["unexplained"], 0)
        self.assertTrue(cov["identity_ok"])
        by_id = {b["beam_id"]: b for b in cov["beams"]}
        self.assertEqual(by_id["B1"]["crop_path"], CROP_T1_NATIVE)
        self.assertEqual(by_id["B2"]["crop_path"], CROP_W6_FALLBACK)
        self.assertEqual(by_id["B3"]["crop_path"], CROP_UNAVAILABLE)
        self.assertEqual(by_id["B1"]["hybrid_outcome"], OUT_CLAUDE_SUCCESS)
        self.assertEqual(by_id["B4"]["hybrid_outcome"], OUT_CLAUDE_FAILURE)
        self.assertEqual(by_id["B3"]["hybrid_outcome"], OUT_FALLBACK)

    def test_shadow_does_not_patch(self):
        before = (self.root / R13_REL).read_text(encoding="utf-8")
        result = run_production_hybrid(
            run_id="t-shadow",
            staging=self.root,
            settings=_settings(mode="shadow", key="PRESENT", calls=6, wall=90),
            client_override=_authority_client(),
            persist=True,
        )
        self.assertFalse(result["production_authority_applied"])
        self.assertEqual((self.root / R13_REL).read_text(encoding="utf-8"), before)
        self.assertGreaterEqual(result["request_count"], 1)

    def test_authoritative_still_forbidden(self):
        from PhaseW5_production_hybrid_shadow.adapter import run_hybrid_shadow

        result = run_hybrid_shadow(
            run_id="t-auth-forbid",
            staging=self.root,
            settings=_settings(mode="authoritative", key="PRESENT"),
            persist=True,
        )
        self.assertEqual(result["hybrid_status"], STATUS_AUTHORITATIVE_FORBIDDEN)
        self.assertEqual(result["request_count"], 0)


class SecretSafetyTests(unittest.TestCase):
    def test_health_payload_has_no_secret_fields(self):
        from PhaseW5_production_hybrid_shadow.settings import health_payload

        payload = health_payload(_settings(mode="off", key="ABSENT"))
        blob = json.dumps(payload).lower()
        self.assertNotIn("sk-ant", blob)
        self.assertNotIn("api_key_value", blob)
        self.assertIn("api_key_configured", payload)
        self.assertIsInstance(payload["api_key_configured"], bool)


if __name__ == "__main__":
    unittest.main()
