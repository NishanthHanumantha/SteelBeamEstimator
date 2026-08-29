"""Phase W.6 Flask-level Hybrid production-authority tests (stub pipeline)."""
from __future__ import annotations

import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parents[1]
if str(WEBAPP_ROOT) not in sys.path:
    sys.path.insert(0, str(WEBAPP_ROOT))

os.environ.setdefault("STEEL_WEB_PIPELINE_MODE", "stub")
os.environ["HYBRID_MODE"] = "off"

import config  # noqa: E402
from app import create_app  # noqa: E402
from services.estimation_service import _JOBS, _LOCK  # noqa: E402
from services.flight_guard import GUARD  # noqa: E402


def _dxf_bytes(tag: str = "W6") -> bytes:
    body = (
        "  0\nSECTION\n  2\nHEADER\n  0\nENDSEC\n"
        f"  0\nSECTION\n  2\nENTITIES\n  1\n{tag}\n  0\nENDSEC\n"
        "  0\nEOF\n"
    )
    return body.encode("ascii")


class W6FlaskHybridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="w6_web_")
        root = Path(cls._tmpdir.name)
        config.UPLOAD_ROOT = root / "uploads"
        config.OUTPUT_ROOT = root / "outputs"
        config.LOG_ROOT = root / "logs"
        config.WEB_RUNS_ROOT = root / "web_runs"
        config.R2A_GN_POINTER = root / "beam_registry.json"
        for p in (
            config.UPLOAD_ROOT,
            config.OUTPUT_ROOT,
            config.LOG_ROOT,
            config.WEB_RUNS_ROOT,
        ):
            p.mkdir(parents=True, exist_ok=True)
        cls.app = create_app()
        cls.app.testing = True
        cls.dxf = _dxf_bytes()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmpdir.cleanup()

    def setUp(self) -> None:
        os.environ["STEEL_WEB_PIPELINE_MODE"] = "stub"
        os.environ["HYBRID_MODE"] = "off"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("STEEL_WEB_FAIL_STAGE", None)
        with _LOCK:
            _JOBS.clear()
        active = GUARD.active_run_id()
        if active:
            GUARD.release(active)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        os.environ["HYBRID_MODE"] = "off"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        active = GUARD.active_run_id()
        if active:
            GUARD.release(active)

    def _post(self):
        files = {
            "general_notes": (io.BytesIO(self.dxf), "general_notes.dxf"),
            "framing": (io.BytesIO(self.dxf), "framing_plan.dxf"),
            "reinforcement": (io.BytesIO(self.dxf), "beam_reinforcement.dxf"),
        }
        return self.client.post(
            "/api/estimate",
            data=files,
            content_type="multipart/form-data",
        )

    def _wait(self, run_id: str, timeout_s: float = 20.0) -> dict:
        deadline = time.time() + timeout_s
        last = {}
        while time.time() < deadline:
            res = self.client.get(f"/api/status/{run_id}")
            last = res.get_json() or {}
            if last.get("status") in {"success", "error"}:
                hybrid = last.get("hybrid") or {}
                if last.get("status") == "error":
                    return last
                if os.environ.get("HYBRID_MODE", "off").lower() in {"off", ""}:
                    return last
                if hybrid.get("hybrid_status") and hybrid.get("hybrid_status") != "PENDING":
                    return last
                if last.get("status") == "success":
                    return last
            time.sleep(0.05)
        self.fail(f"Timed out waiting for run {run_id}: {last}")

    def test_health_w6_hybrid_off(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("phase"), "W.19.1")
        self.assertEqual(data.get("app_release"), "W.19.1")
        ids = data.get("production_stages") or []
        self.assertIn("HYBRID", ids)
        self.assertLess(ids.index("R13"), ids.index("HYBRID"))
        self.assertLess(ids.index("HYBRID"), ids.index("VB1"))
        hybrid = data.get("hybrid") or {}
        self.assertEqual(hybrid.get("mode"), "off")
        self.assertEqual(hybrid.get("production_authority"), "none")
        self.assertEqual(hybrid.get("production_excel_invokes_claude"), False)
        self.assertIn("api_key_configured", hybrid)
        self.assertIsInstance(hybrid.get("api_key_configured"), bool)
        blob = str(data).lower()
        self.assertNotIn("sk-ant-", blob)
        self.assertNotIn("anthropic_api_key=", blob)

    def test_w6_01_hybrid_off_excel_succeeds(self):
        os.environ["HYBRID_MODE"] = "off"
        res = self._post()
        self.assertEqual(res.status_code, 200)
        run_id = res.get_json()["run_id"]
        status = self._wait(run_id)
        self.assertEqual(status["status"], "success")
        self.assertIn("HYBRID", status.get("stages_run") or [])
        self.assertIn("VB1", status.get("stages_run") or [])
        excel = config.WEB_RUNS_ROOT / run_id / config.VB1_EXCEL_REL
        self.assertTrue(excel.exists())
        self.assertGreater(excel.stat().st_size, 0)
        self.assertFalse(status.get("hybrid"))
        w6 = config.WEB_RUNS_ROOT / run_id / "data" / "output" / "PhaseW6_hybrid_semantic_resolution"
        self.assertFalse(w6.exists())

    def test_w6_06_production_missing_key_excel_still_succeeds(self):
        os.environ["HYBRID_MODE"] = "production"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        res = self._post()
        self.assertEqual(res.status_code, 200)
        run_id = res.get_json()["run_id"]
        status = self._wait(run_id)
        self.assertEqual(status["status"], "success")
        excel = config.WEB_RUNS_ROOT / run_id / config.VB1_EXCEL_REL
        self.assertTrue(excel.exists())
        hybrid = status.get("hybrid") or {}
        self.assertEqual(hybrid.get("hybrid_mode"), "production")
        self.assertIn(
            hybrid.get("hybrid_status"),
            ("HYBRID_UNAVAILABLE", "KEY_ABSENT", "NO_ENGINEERING_CONTEXT", "MISSING_W6_ARTEFACT"),
        )
        self.assertEqual(hybrid.get("request_count"), 0)
        self.assertFalse(hybrid.get("production_authority_applied"))

    def test_w6_07_single_flight_unchanged(self):
        os.environ["HYBRID_MODE"] = "off"
        first = self._post()
        self.assertEqual(first.status_code, 200)
        busy = self._post()
        self.assertEqual(busy.status_code, 409)
        run_id = first.get_json()["run_id"]
        status = self._wait(run_id)
        self.assertEqual(status["status"], "success")


if __name__ == "__main__":
    unittest.main()
