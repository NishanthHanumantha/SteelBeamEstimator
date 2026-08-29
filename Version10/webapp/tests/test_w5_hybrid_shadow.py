"""Phase W.5 Flask-level Hybrid shadow tests (stub pipeline)."""
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


def _dxf_bytes(tag: str = "W5") -> bytes:
    body = (
        "  0\nSECTION\n  2\nHEADER\n  0\nENDSEC\n"
        f"  0\nSECTION\n  2\nENTITIES\n  1\n{tag}\n  0\nENDSEC\n"
        "  0\nEOF\n"
    )
    return body.encode("ascii")


class W5FlaskHybridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="w5_web_")
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
            time.sleep(0.05)
        self.fail(f"Timed out waiting for run {run_id}: {last}")

    def test_health_reports_hybrid_off_without_key(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("phase"), "W.19.1")
        hybrid = data.get("hybrid") or {}
        hybrid = data.get("hybrid") or {}
        self.assertEqual(hybrid.get("mode"), "off")
        self.assertEqual(hybrid.get("production_excel_invokes_claude"), False)
        self.assertEqual(hybrid.get("authoritative_enabled"), False)
        self.assertFalse(hybrid.get("shadow_may_invoke_claude"))
        self.assertIn(hybrid.get("api_key_status"), ("ABSENT", "EMPTY", "PRESENT"))

    def test_1_hybrid_off_excel_succeeds(self):
        os.environ["HYBRID_MODE"] = "off"
        res = self._post()
        self.assertEqual(res.status_code, 200)
        run_id = res.get_json()["run_id"]
        status = self._wait(run_id)
        self.assertEqual(status["status"], "success")
        excel = config.WEB_RUNS_ROOT / run_id / config.VB1_EXCEL_REL
        self.assertTrue(excel.exists())
        self.assertGreater(excel.stat().st_size, 0)
        hybrid_dir = config.WEB_RUNS_ROOT / run_id / "data" / "output" / "PhaseW5_production_hybrid_shadow"
        self.assertFalse(hybrid_dir.exists())
        self.assertFalse(status.get("hybrid"))

    def test_3_shadow_missing_key_excel_still_succeeds(self):
        os.environ["HYBRID_MODE"] = "shadow"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        res = self._post()
        self.assertEqual(res.status_code, 200)
        run_id = res.get_json()["run_id"]
        status = self._wait(run_id)
        self.assertEqual(status["status"], "success")
        excel = config.WEB_RUNS_ROOT / run_id / config.VB1_EXCEL_REL
        self.assertTrue(excel.exists())
        hybrid = status.get("hybrid") or {}
        self.assertEqual(hybrid.get("hybrid_mode"), "shadow")
        self.assertIn(
            hybrid.get("hybrid_status"),
            ("KEY_ABSENT", "NO_ENGINEERING_CONTEXT", "HYBRID_UNAVAILABLE"),
        )
        self.assertEqual(hybrid.get("request_count"), 0)


if __name__ == "__main__":
    unittest.main()
