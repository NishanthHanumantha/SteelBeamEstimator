"""Phase W.8 unit tests — P2.6.10 evidence adapter (no Lightsail, no secret print)."""
from __future__ import annotations

import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path

from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

ensure_src_on_path()

from PhaseW5_production_hybrid_shadow.config import EXCEL_REL, R13_REL, STEEL_SUMMARY_REL, T1_RENDER_REL
from PhaseW5_production_hybrid_shadow.settings import HybridSettings
from PhaseW5_production_hybrid_shadow.unit_tests import _png, _vision_client
from PhaseW6_hybrid_production_authority.config import OUTPUT_DIRNAME, PRE_HYBRID_FILENAME, PROTECTED_BAR_KEYS, R13_DIR_REL
from PhaseW6_hybrid_production_authority.coverage import CROP_P2610_PRIMARY, CROP_T1_NATIVE, build_coverage
from PhaseW6_hybrid_production_authority.handoff import apply_beam_handoff
from PhaseW6_hybrid_production_authority.orchestrator import run_production_hybrid
from PhaseW6_hybrid_production_authority.unit_tests import _authority_client, _plant, _r13_model, _settings

from .config import (
    CLASS_UNAVAILABLE,
    CLAUDE_CONTEXT_IMAGES,
    CLAUDE_DETAIL_IMAGES,
    COMPONENT_INVENTORY,
    MULTIPLE_DETAIL_IN_CLAUDE_REQUEST,
    SOURCE_P2610_PRIMARY,
    W6_ADAPTER_ROLE,
)
from .generator import selected_png
from .package import prepare_production_evidence

ALLOWED_CLASSES = {
    "PRODUCTION_READY",
    "REUSABLE_WITH_ADAPTER",
    "RESEARCH_ONLY",
    "OUTPUT_ONLY",
    "DEPRECATED",
    "UNKNOWN",
}

FIRST_SET_DXF = (
    Path(__file__).resolve().parents[3]
    / "Test_Input"
    / "1st Set Drawings-Galera_OHT&STP"
    / "reinforcement"
    / "SampleBeam_Reinforcement&StirrupsDetials_DXF.dxf"
)


def _capture_client():
    captured: dict = {}

    def _client(**kwargs):
        captured["images"] = kwargs.get("images") or []
        captured["user_prompt"] = kwargs.get("user_prompt")
        captured["n_images"] = len(kwargs.get("images") or [])
        inner = _authority_client()
        return inner(**kwargs)

    _client.captured = captured  # type: ignore[attr-defined]
    return _client


class InventoryTests(unittest.TestCase):
    def test_w8_02_c1c5_inventory_classified(self):
        self.assertGreaterEqual(len(COMPONENT_INVENTORY), 10)
        missing = []
        for row in COMPONENT_INVENTORY:
            cls = str(row.get("classification") or "")
            if cls not in ALLOWED_CLASSES:
                missing.append((row.get("module"), cls))
        self.assertEqual(missing, [])
        phases = {str(r.get("phase") or "") for r in COMPONENT_INVENTORY}
        self.assertTrue(any("C.1" in p or "C.1+C.2" in p for p in phases))
        self.assertTrue(any("C.3" in p for p in phases))
        self.assertTrue(any("C.4" in p for p in phases))
        self.assertTrue(any("C.5" in p for p in phases))
        self.assertEqual(W6_ADAPTER_ROLE, "FALLBACK")
        self.assertFalse(MULTIPLE_DETAIL_IN_CLAUDE_REQUEST)
        self.assertEqual(CLAUDE_CONTEXT_IMAGES, 1)
        self.assertEqual(CLAUDE_DETAIL_IMAGES, 1)


class W7PathTraceTests(unittest.TestCase):
    def test_w8_03_live_invoke_and_e2_accept_split_paths(self):
        from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.live_caller import (
            call_live_beam,
        )
        from PhaseP2610C5_stratified_vision_semantic_benchmark.claude_call import call_selected_beam
        from PhaseW5_production_hybrid_shadow.live_invoke import call_shadow_beam

        live_params = inspect.signature(call_live_beam).parameters
        self.assertIn("context_path", live_params)
        self.assertIn("detail_path", live_params)
        shadow_params = inspect.signature(call_shadow_beam).parameters
        self.assertIn("context_path", shadow_params)
        self.assertIn("detail_path", shadow_params)
        src = inspect.getsource(call_live_beam)
        self.assertIn("context_path", src)
        self.assertIn("detail_path", src)
        c5 = inspect.getsource(call_selected_beam)
        self.assertIn("n_images", c5)
        self.assertIn("encode_png(context_path)", c5)
        self.assertIn("encode_png(detail_path)", c5)


class OrchestratorSafetyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="w8_hybrid_")
        self.root = Path(self._tmp.name)
        self.excel = b"PK\x03\x04isolation-w8"
        _plant(self.root, excel=self.excel)

    def tearDown(self):
        self._tmp.cleanup()

    def test_w8_01_hybrid_off_no_claude(self):
        before = (self.root / R13_REL).read_text(encoding="utf-8")
        result = run_production_hybrid(
            run_id="w8-off",
            staging=self.root,
            settings=_settings(mode="off", key="ABSENT"),
            persist=True,
        )
        self.assertEqual(result["classification"], "HYBRID_SKIPPED_OFF")
        self.assertEqual(result["request_count"], 0)
        self.assertFalse(result["production_authority_applied"])
        self.assertEqual((self.root / R13_REL).read_text(encoding="utf-8"), before)
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)

    def test_w8_05_context_detail_sent_from_package(self):
        bid = "B1"
        ctx = selected_png(self.root, bid, "context")
        det = selected_png(self.root, bid, "detail")
        ctx.parent.mkdir(parents=True, exist_ok=True)
        det.parent.mkdir(parents=True, exist_ok=True)
        ctx.write_bytes(_png(320))
        det.write_bytes(_png(480))
        man = {
            "beam_id": bid,
            "available": True,
            "evidence_class": "PRIMARY",
            "visual_source": SOURCE_P2610_PRIMARY,
            "fallback_status": "NONE",
            "selected_context_evidence": {"path": str(ctx), "source_phase": "B.1"},
            "selected_detail_evidence": {"path": str(det), "source_phase": "B.1"},
            "context_and_detail_distinct": True,
        }
        (ctx.parent.parent / "evidence_manifest.json").write_text(
            json.dumps(man), encoding="utf-8"
        )
        client = _capture_client()
        result = run_production_hybrid(
            run_id="w8-ctx-det",
            staging=self.root,
            settings=_settings(mode="production", key="PRESENT"),
            client_override=client,
            persist=True,
        )
        self.assertGreaterEqual(result["request_count"], 1)
        images = client.captured.get("images") or []
        self.assertEqual(len(images), 2)
        self.assertNotEqual(images[0].get("data_base64"), images[1].get("data_base64"))
        self.assertIn("context", str(images[0].get("path") or "").replace("\\", "/"))
        self.assertIn("detail", str(images[1].get("path") or "").replace("\\", "/"))

    def test_w8_06_coverage_identity_includes_p2610(self):
        shadow = {
            "request_count": 1,
            "beams": [
                {
                    "beam_id": "B1",
                    "visual_source": SOURCE_P2610_PRIMARY,
                    "visual_available": True,
                    "evidence_class": "PRIMARY",
                    "hybrid_status": "OBSERVED",
                    "called": True,
                },
                {
                    "beam_id": "B2",
                    "visual_source": "W6_ENVELOPE_RENDER",
                    "visual_available": True,
                    "evidence_class": "FALLBACK",
                    "hybrid_status": "OBSERVED",
                    "called": True,
                },
                {
                    "beam_id": "B3",
                    "visual_source": None,
                    "visual_available": False,
                    "evidence_class": "UNAVAILABLE",
                    "hybrid_status": "HYBRID_UNAVAILABLE",
                    "skip_reason": "EVIDENCE_UNAVAILABLE",
                    "called": False,
                },
                {
                    "beam_id": "B4",
                    "visual_source": "W8_SELECTED_MIXED",
                    "visual_available": True,
                    "evidence_class": "COMPATIBILITY",
                    "hybrid_status": "OBSERVED",
                    "called": True,
                },
            ],
        }
        cov = build_coverage(
            mode="production",
            beam_ids=["B1", "B2", "B3", "B4"],
            shadow_result=shadow,
            visual_prep={"evidence_packages_generated": 3, "unavailable": 1},
        )
        self.assertEqual(cov["hybrid_eligible"], 4)
        self.assertEqual(cov["p2610_primary_evidence"], 1)
        self.assertEqual(cov["generated_fallback_crop"], 2)
        self.assertEqual(cov["visual_context_unavailable"], 1)
        self.assertEqual(cov["unexplained"], 0)
        self.assertTrue(cov["identity_ok"])
        self.assertEqual(
            cov["hybrid_eligible"],
            cov["p2610_primary_evidence"]
            + cov["native_t1_crop"]
            + cov["generated_fallback_crop"]
            + cov["visual_context_unavailable"],
        )
        by_id = {b["beam_id"]: b for b in cov["beams"]}
        self.assertEqual(by_id["B1"]["crop_path"], CROP_P2610_PRIMARY)

    def test_w8_10_existing_bar_engineering_preserved(self):
        model = _r13_model()
        cut = model["top_main_bars"][0]["cut_length_mm"]
        qty = model["stirrups"][0]["quantity"]
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
            "stirrups": {
                "items": [
                    {
                        "origin": "MATCHED",
                        "spec": {"value": "2L-Y10@150C/C", "source": "VISION"},
                        "quantity": {"value": 99, "source": "VISION"},
                    }
                ]
            },
        }
        apply_beam_handoff(model=model, hybrid_semantic=hybrid)
        self.assertEqual(model["top_main_bars"][0]["cut_length_mm"], cut)
        self.assertEqual(model["stirrups"][0]["quantity"], qty)
        for key in PROTECTED_BAR_KEYS:
            self.assertNotIn(key, ("quantity", "diameter_mm", "bar_label"))

    def test_w8_11_evidence_unavailable_excel_safe(self):
        (self.root / T1_RENDER_REL / "B1_crop.png").unlink()
        before_r13 = (self.root / R13_REL).read_text(encoding="utf-8")
        result = run_production_hybrid(
            run_id="w8-no-ev",
            staging=self.root,
            settings=_settings(mode="production", key="PRESENT"),
            client_override=_authority_client(),
            persist=True,
        )
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)
        self.assertEqual((self.root / R13_REL).read_text(encoding="utf-8"), before_r13)
        self.assertFalse(result["production_authority_applied"])
        self.assertEqual(result["request_count"], 0)
        man = json.loads(
            (
                self.root
                / "data"
                / "output"
                / OUTPUT_DIRNAME
                / "hybrid_evidence"
                / "B1"
                / "evidence_manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(man.get("available"))
        self.assertIn(man.get("evidence_class"), (CLASS_UNAVAILABLE, "UNAVAILABLE"))
        self.assertNotIn("sk-ant", json.dumps(man).lower())

    def test_w8_12_claude_failure_excel_safe(self):
        before_r13 = (self.root / R13_REL).read_text(encoding="utf-8")
        result = run_production_hybrid(
            run_id="w8-api-fail",
            staging=self.root,
            settings=_settings(mode="production", key="PRESENT"),
            client_override=_vision_client(fail=True),
            persist=True,
        )
        self.assertEqual((self.root / EXCEL_REL).read_bytes(), self.excel)
        self.assertEqual((self.root / R13_REL).read_text(encoding="utf-8"), before_r13)
        self.assertFalse(result["production_authority_applied"])
        self.assertIn(
            result["classification"],
            ("HYBRID_FALLBACK_USED", "HYBRID_API_ERROR", "HYBRID_UNAVAILABLE"),
        )


class EvidenceGenerationTests(unittest.TestCase):
    def test_w8_04_07_first_set_context_detail_distinct(self):
        if not FIRST_SET_DXF.is_file():
            self.skipTest("First Set reinforcement DXF not present")
        tmp = tempfile.TemporaryDirectory(prefix="w8_ev_")
        try:
            root = Path(tmp.name)
            reinf = root / "reinforcement"
            reinf.mkdir(parents=True)
            dest = reinf / FIRST_SET_DXF.name
            dest.write_bytes(FIRST_SET_DXF.read_bytes())
            report = prepare_production_evidence(root, beam_ids=["B1"])
            self.assertTrue(report.get("ok"))
            rec = (report.get("by_id") or {}).get("B1") or {}
            ctx = selected_png(root, "B1", "context")
            det = selected_png(root, "B1", "detail")
            man_path = (
                root
                / "data"
                / "output"
                / OUTPUT_DIRNAME
                / "hybrid_evidence"
                / "B1"
                / "evidence_manifest.json"
            )
            self.assertTrue(man_path.is_file())
            man = json.loads(man_path.read_text(encoding="utf-8"))
            blob = json.dumps(man).lower()
            self.assertNotIn("sk-ant", blob)
            self.assertNotIn("api_key", blob)
            if rec.get("available"):
                self.assertTrue(ctx.is_file())
                self.assertTrue(det.is_file())
                self.assertGreaterEqual(ctx.stat().st_size, 200)
                self.assertGreaterEqual(det.stat().st_size, 200)
                if rec.get("evidence_class") == "PRIMARY" or rec.get("visual_source") == SOURCE_P2610_PRIMARY:
                    self.assertNotEqual(ctx.read_bytes(), det.read_bytes())
                    self.assertTrue(man.get("selected_context_evidence"))
                    self.assertTrue(man.get("selected_detail_evidence"))
            else:
                self.assertEqual(rec.get("evidence_class"), CLASS_UNAVAILABLE)
                self.assertTrue(man.get("fallback_reason") or man.get("attempted_evidence_sources"))
        finally:
            tmp.cleanup()

    def test_w8_t1_compatibility_when_no_dxf(self):
        tmp = tempfile.TemporaryDirectory(prefix="w8_t1_")
        try:
            root = Path(tmp.name)
            t1 = root / T1_RENDER_REL
            t1.mkdir(parents=True)
            (t1 / "B1_crop.png").write_bytes(_png(256))
            report = prepare_production_evidence(root, beam_ids=["B1"])
            rec = (report.get("by_id") or {}).get("B1") or {}
            self.assertTrue(rec.get("available"))
            self.assertIn(rec.get("evidence_class"), ("COMPATIBILITY", "FALLBACK"))
            self.assertTrue(rec.get("fallback_status") not in (None, "NONE"))
            self.assertTrue(selected_png(root, "B1", "context").is_file())
            self.assertTrue(selected_png(root, "B1", "detail").is_file())
        finally:
            tmp.cleanup()


class SecretSafetyTests(unittest.TestCase):
    def test_manifest_sanitizer_redacts_key_like_strings(self):
        from .package import _sanitize

        payload = {"ok": True, "note": "sk-ant-fakevalue", "api_key": "SECRET"}
        cleaned = _sanitize(payload)
        self.assertNotIn("api_key", cleaned)
        self.assertEqual(cleaned.get("note"), "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
