"""Phase W.14 provider classification, lifecycle identity, and download path."""
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

import config  # noqa: E402
from app import create_app  # noqa: E402
from services.estimation_service import _JOBS, _LOCK  # noqa: E402
from services.flight_guard import GUARD  # noqa: E402


def _dxf_bytes(tag: str = "W14") -> bytes:
    body = (
        "  0\nSECTION\n  2\nHEADER\n  0\nENDSEC\n"
        f"  0\nSECTION\n  2\nENTITIES\n  1\n{tag}\n  0\nENDSEC\n"
        "  0\nEOF\n"
    )
    return body.encode("ascii")


class W14RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="w14_web_")
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
        os.environ.pop("STEEL_WEB_FAIL_STAGE", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with _LOCK:
            _JOBS.clear()
        active = GUARD.active_run_id()
        if active:
            GUARD.release(active)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        os.environ.pop("STEEL_WEB_FAIL_STAGE", None)
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
                return last
            time.sleep(0.05)
        self.fail(f"Timed out waiting for run {run_id}: {last}")

    def test_w14_health_phase(self):
        res = self.client.get("/health")
        data = res.get_json()
        self.assertEqual(data.get("phase"), "W.19")
        self.assertEqual(data.get("app_release"), "W.19")
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("app.js?v=W.19", html)
        self.assertIn('id="btn-download"', html)
        blob = str(data).lower()
        self.assertNotIn("sk-ant-", blob)

    def test_w14_download_path_intact(self):
        res = self._post()
        self.assertEqual(res.status_code, 200)
        run_id = res.get_json()["run_id"]
        status = self._wait(run_id)
        self.assertEqual(status["status"], "success")
        first = self.client.get(f"/api/download/{run_id}")
        second = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data[:2], b"PK")
        self.assertEqual(first.data, second.data)

    def test_w14_provider_classification_spend_limit(self):
        from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

        ensure_src_on_path()
        from PhaseW6_hybrid_production_authority.resolution_trace import (
            PROVIDER_WORKSPACE_SPEND_LIMIT,
            classify_provider_error,
            classify_stop_stage,
        )

        row = {
            "called": True,
            "visual_available": True,
            "hybrid_status": "HYBRID_UNAVAILABLE",
            "failure_category": "API_FAILED",
            "skip_reason": "API_FAILED",
            "api_error": "Error code: 400 - invalid_request_error You have reached your specified workspace API usage limits.",
        }
        self.assertEqual(classify_provider_error(row), PROVIDER_WORKSPACE_SPEND_LIMIT)
        status, reason, existing = classify_stop_stage(row)
        self.assertEqual(reason, "VISION_API_ERROR")
        self.assertEqual(existing, PROVIDER_WORKSPACE_SPEND_LIMIT)
        self.assertNotEqual(status, "HYBRID_RESOLVED")
