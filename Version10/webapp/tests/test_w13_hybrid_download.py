"""Phase W.13 Hybrid trace and download reliability tests (stub pipeline)."""
from __future__ import annotations

import io
import json
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
from services.estimation_service import _JOBS, _LOCK, get_job  # noqa: E402
from services.flight_guard import GUARD  # noqa: E402
from services.result_registry import workbook_path_for_run  # noqa: E402


def _dxf_bytes(tag: str = "W13") -> bytes:
    body = (
        "  0\nSECTION\n  2\nHEADER\n  0\nENDSEC\n"
        f"  0\nSECTION\n  2\nENTITIES\n  1\n{tag}\n  0\nENDSEC\n"
        "  0\nEOF\n"
    )
    return body.encode("ascii")


class W13DownloadAndHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="w13_web_")
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

    def _complete(self) -> tuple[str, dict]:
        res = self._post()
        self.assertEqual(res.status_code, 200)
        run_id = res.get_json()["run_id"]
        status = self._wait(run_id)
        self.assertEqual(status["status"], "success")
        return run_id, status

    def test_w13_08_health_and_cache_bust(self):
        res = self.client.get("/health")
        data = res.get_json()
        self.assertEqual(data.get("phase"), "W.19")
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="btn-download"', html)
        self.assertIn("app.js?v=W.19", html)
        self.assertIn("app.css?v=W.19", html)
        self.assertIn('href="#"', html)
        self.assertNotIn("sk-ant-", html.lower())

    def test_w13_09_repeated_download(self):
        run_id, _status = self._complete()
        first = self.client.get(f"/api/download/{run_id}")
        second = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data[:2], b"PK")
        self.assertEqual(first.data, second.data)

    def test_w13_10_refresh_then_download(self):
        run_id, _status = self._complete()
        with _LOCK:
            _JOBS.clear()
        status = self.client.get(f"/api/status/{run_id}").get_json()
        self.assertEqual(status.get("status"), "success")
        self.assertTrue(status.get("download_ready"))
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 200)

    def test_w13_11_run_query_restore_download(self):
        run_id, _status = self._complete()
        home = self.client.get(f"/?run={run_id}")
        self.assertEqual(home.status_code, 200)
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 200)
        self.assertEqual(dl.data[:2], b"PK")

    def test_w13_12_worker_restart_reconstruction(self):
        run_id, _status = self._complete()
        path = workbook_path_for_run(run_id)
        self.assertTrue(path.is_file())
        with _LOCK:
            _JOBS.clear()
        self.assertIsNone(_JOBS.get(run_id))
        job = get_job(run_id)
        self.assertIsNotNone(job)
        self.assertEqual(job.status, "success")
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 200)

    def test_w13_13_download_failure_keeps_success_state(self):
        run_id, status = self._complete()
        self.assertEqual(status["status"], "success")
        path = workbook_path_for_run(run_id)
        path.unlink()
        with _LOCK:
            _JOBS.clear()
        status2 = self.client.get(f"/api/status/{run_id}").get_json()
        self.assertEqual(status2.get("status"), "success")
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 404)
        body = dl.get_json()
        self.assertFalse(body.get("ok"))
        self.assertIn("no longer available", (body.get("error") or "").lower())

    def test_w13_07_hybrid_failure_still_excel(self):
        os.environ["HYBRID_MODE"] = "production"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        run_id, status = self._complete()
        self.assertEqual(status["status"], "success")
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 200)
        self.assertEqual(dl.data[:2], b"PK")


class W13HybridTraceUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        engine_src = str(Path(__file__).resolve().parents[2] / "src")
        if engine_src not in sys.path:
            sys.path.insert(0, engine_src)

    def test_w13_01_03_historical_classification_separation(self):
        from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

        ensure_src_on_path()
        from PhaseW6_hybrid_production_authority.resolution_trace import (
            REASON_OK,
            REASON_VISION_API_ERROR,
            STATUS_HYBRID_RESOLVED,
            STATUS_VISION_FAILED,
            build_resolution_trace,
        )

        w11 = {
            "request_count": 2,
            "beams": [
                {
                    "beam_id": "B1",
                    "visual_available": True,
                    "called": True,
                    "hybrid_status": "OBSERVED",
                    "failure_category": "OK",
                    "usage": {"input_tokens": 100, "output_tokens": 20},
                    "hybrid_semantic": {"beam_id": "B1"},
                },
                {
                    "beam_id": "B2",
                    "visual_available": True,
                    "called": True,
                    "hybrid_status": "OBSERVED",
                    "failure_category": "OK",
                    "usage": {"input_tokens": 90, "output_tokens": 18},
                    "hybrid_semantic": {"beam_id": "B2"},
                },
            ],
        }
        w12 = {
            "request_count": 2,
            "beams": [
                {
                    "beam_id": "B1",
                    "visual_available": True,
                    "called": True,
                    "hybrid_status": "OBSERVED",
                    "failure_category": "OK",
                    "usage": {"input_tokens": 100, "output_tokens": 20},
                    "hybrid_semantic": {"beam_id": "B1"},
                },
                {
                    "beam_id": "B2",
                    "visual_available": True,
                    "called": True,
                    "hybrid_status": "HYBRID_UNAVAILABLE",
                    "skip_reason": "API_FAILED",
                    "failure_category": "API_FAILED",
                    "retry_count": 0,
                    "attempts": 1,
                    "usage": {"input_tokens": 0, "output_tokens": 0, "latency_s": None},
                },
            ],
        }
        t11 = build_resolution_trace(run_id="w11", beam_ids=["B1", "B2"], shadow_result=w11)
        t12 = build_resolution_trace(run_id="w12", beam_ids=["B1", "B2"], shadow_result=w12)
        self.assertEqual(t11["lifecycle_counts"]["claude_api_success"], 2)
        self.assertEqual(t11["lifecycle_counts"]["d2_resolved"], 2)
        self.assertEqual(t12["lifecycle_counts"]["claude_attempted"], 2)
        self.assertEqual(t12["lifecycle_counts"]["claude_api_success"], 1)
        self.assertEqual(t12["lifecycle_counts"]["claude_api_failure"], 1)
        self.assertNotEqual(
            t12["lifecycle_counts"]["claude_attempted"],
            t12["lifecycle_counts"]["d2_resolved"],
        )
        by12 = {b["beam_id"]: b for b in t12["beams"]}
        self.assertEqual(by12["B1"]["final_status"], STATUS_HYBRID_RESOLVED)
        self.assertEqual(by12["B1"]["reason_code"], REASON_OK)
        self.assertEqual(by12["B2"]["final_status"], STATUS_VISION_FAILED)
        self.assertEqual(by12["B2"]["reason_code"], REASON_VISION_API_ERROR)

    def test_w13_05_known_unresolved_reason(self):
        from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

        ensure_src_on_path()
        from PhaseW6_hybrid_production_authority.resolution_trace import (
            REASON_E2_REJECTED,
            REASON_EVIDENCE_UNAVAILABLE,
            REASON_VISION_TIMEOUT,
            classify_stop_stage,
        )

        e2 = classify_stop_stage(
            {
                "called": True,
                "visual_available": True,
                "hybrid_status": "HYBRID_UNAVAILABLE",
                "failure_category": "SEMANTIC_UNUSABLE",
            }
        )
        self.assertEqual(e2[1], REASON_E2_REJECTED)
        timeout = classify_stop_stage(
            {
                "called": True,
                "visual_available": True,
                "timeout_status": "VISION_TIMEOUT",
                "skip_reason": "VISION_TIMEOUT",
            }
        )
        self.assertEqual(timeout[1], REASON_VISION_TIMEOUT)
        missing = classify_stop_stage(
            {
                "called": False,
                "visual_available": False,
                "skip_reason": "NO_USABLE_EVIDENCE",
            }
        )
        self.assertEqual(missing[1], REASON_EVIDENCE_UNAVAILABLE)
        usage = classify_stop_stage(
            {
                "called": True,
                "visual_available": True,
                "hybrid_status": "HYBRID_UNAVAILABLE",
                "failure_category": "API_FAILED",
                "skip_reason": "API_FAILED",
                "api_error": "Error code: 400 - workspace API usage limits",
            }
        )
        self.assertEqual(usage[1], "VISION_API_ERROR")
        self.assertEqual(usage[2], "WORKSPACE_SPEND_LIMIT")

    def test_w13_06_no_fabricated_vision(self):
        from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

        ensure_src_on_path()
        from PhaseW6_hybrid_production_authority.resolution_trace import (
            STATUS_HYBRID_RESOLVED,
            classify_stop_stage,
        )

        status, reason, _existing = classify_stop_stage(
            {
                "called": True,
                "visual_available": True,
                "hybrid_status": "HYBRID_UNAVAILABLE",
                "failure_category": "API_FAILED",
                "hybrid_semantic": None,
            }
        )
        self.assertNotEqual(status, STATUS_HYBRID_RESOLVED)
        self.assertEqual(reason, "VISION_API_ERROR")


if __name__ == "__main__":
    unittest.main()
