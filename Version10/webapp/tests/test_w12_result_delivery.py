"""Phase W.12 result delivery and download reliability tests (stub pipeline)."""
from __future__ import annotations

import io
import os
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parents[1]
if str(WEBAPP_ROOT) not in sys.path:
    sys.path.insert(0, str(WEBAPP_ROOT))

os.environ.setdefault("STEEL_WEB_PIPELINE_MODE", "stub")

import config  # noqa: E402
from app import create_app  # noqa: E402
from services.estimation_service import _JOBS, _LOCK, get_job  # noqa: E402
from services.flight_guard import GUARD  # noqa: E402
from services.result_registry import (  # noqa: E402
    MANIFEST_NAME,
    workbook_filename,
    workbook_path_for_run,
)


def _dxf_bytes(tag: str = "W12") -> bytes:
    body = (
        "  0\nSECTION\n  2\nHEADER\n  0\nENDSEC\n"
        f"  0\nSECTION\n  2\nENTITIES\n  1\n{tag}\n  0\nENDSEC\n"
        "  0\nEOF\n"
    )
    return body.encode("ascii")


class W12ResultDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="w12_web_")
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

    def test_health_w12_and_no_secrets(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("phase"), "W.19.1")
        self.assertEqual(data.get("app_release"), "W.19.1")
        delivery = data.get("result_delivery") or {}
        self.assertTrue(delivery.get("durable_registry"))
        self.assertTrue(delivery.get("download_reconstructs_from_disk"))
        blob = str(data).lower()
        self.assertNotIn("sk-ant-", blob)
        self.assertNotIn("anthropic_api_key=", blob)
        home = self.client.get("/")
        html = home.get_data(as_text=True)
        self.assertIn('id="btn-download"', html)
        self.assertIn("download-error", html)
        self.assertIn("app.js?v=", html)
        self.assertIn("app.css?v=", html)

    def test_w12_01_server_result_registration(self):
        run_id, status = self._complete()
        self.assertTrue(status.get("result_registered"))
        self.assertTrue(status.get("download_ready"))
        self.assertTrue(status.get("excel_generated"))
        self.assertTrue(status.get("excel_exists"))
        self.assertEqual(status.get("result_lifecycle"), "DOWNLOAD_READY")
        self.assertNotIn("workbook_path", status)
        manifest = config.WEB_RUNS_ROOT / run_id / MANIFEST_NAME
        self.assertTrue(manifest.is_file())
        path = workbook_path_for_run(run_id)
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())
        self.assertGreater(path.stat().st_size, 0)

    def test_w12_02_download_endpoint_success(self):
        run_id, status = self._complete()
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 200)
        cd = dl.headers.get("Content-Disposition") or ""
        self.assertIn("attachment", cd.lower())
        self.assertIn(status["workbook_name"], cd)
        self.assertIn("spreadsheetml", (dl.headers.get("Content-Type") or "").lower())

    def test_w12_03_xlsx_integrity(self):
        run_id, _status = self._complete()
        dl = self.client.get(f"/api/download/{run_id}")
        payload = dl.data
        self.assertGreater(len(payload), 32)
        self.assertEqual(payload[:2], b"PK")
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            names = zf.namelist()
        self.assertTrue(any(n.startswith("xl/") for n in names))

    def test_w12_04_repeated_download(self):
        run_id, _status = self._complete()
        first = self.client.get(f"/api/download/{run_id}")
        second = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data, second.data)
        self.assertTrue(workbook_path_for_run(run_id).is_file())

    def test_w12_05_and_10_memory_loss_refresh_resilience(self):
        run_id, _status = self._complete()
        path = workbook_path_for_run(run_id)
        self.assertTrue(path.is_file())
        with _LOCK:
            _JOBS.clear()
        self.assertIsNone(_JOBS.get(run_id))
        status = self.client.get(f"/api/status/{run_id}").get_json()
        self.assertTrue(status.get("ok"))
        self.assertEqual(status.get("status"), "success")
        self.assertTrue(status.get("download_ready"))
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 200)
        self.assertEqual(dl.data[:2], b"PK")
        job = get_job(run_id)
        self.assertIsNotNone(job)
        self.assertEqual(job.status, "success")

    def test_w12_06_missing_file_explicit_failure(self):
        run_id, _status = self._complete()
        path = workbook_path_for_run(run_id)
        path.unlink()
        with _LOCK:
            _JOBS.clear()
        status = self.client.get(f"/api/status/{run_id}").get_json()
        self.assertTrue(status.get("ok"))
        self.assertEqual(status.get("status"), "success")
        self.assertFalse(status.get("download_ready"))
        self.assertEqual(status.get("result_lifecycle"), "RESULT_UNAVAILABLE")
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 404)
        body = dl.get_json()
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("classification"), "RESULT_UNAVAILABLE")
        self.assertIn("no longer available", (body.get("error") or "").lower())

    def test_w12_07_invalid_run_safety(self):
        missing = self.client.get("/api/download/does-not-exist")
        self.assertEqual(missing.status_code, 404)
        body = missing.get_json()
        self.assertEqual(body.get("classification"), "INVALID_RUN")
        status = self.client.get("/api/status/not-a-run")
        self.assertEqual(status.status_code, 404)

    def test_w12_08_hybrid_failure_still_downloadable(self):
        os.environ["HYBRID_MODE"] = "production"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        run_id, status = self._complete()
        self.assertEqual(status["status"], "success")
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 200)
        self.assertEqual(dl.data[:2], b"PK")

    def test_w12_09_retention_cleanup_does_not_delete_on_download(self):
        run_id, _status = self._complete()
        path = workbook_path_for_run(run_id)
        before = path.stat().st_mtime
        size = path.stat().st_size
        self.client.get(f"/api/download/{run_id}")
        self.assertTrue(path.is_file())
        self.assertEqual(path.stat().st_size, size)
        self.assertGreaterEqual(path.stat().st_mtime, before)
        staging = config.WEB_RUNS_ROOT / run_id
        self.assertTrue(staging.exists())

    def test_w12_path_traversal_rejected(self):
        for bad in (
            "../outputs/secret.xlsx",
            "..%2F..%2Fetc%2Fpasswd",
            "20260101_000000_deadbeef/../../config.py",
        ):
            res = self.client.get(f"/api/download/{bad}")
            self.assertIn(res.status_code, {400, 404})
            payload = res.get_data()
            self.assertNotEqual(payload[:2], b"PK")

    def test_w12_legacy_excel_without_memory_is_downloadable(self):
        run_id = "20260826_120000_abcd1234"
        config.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        path = config.OUTPUT_ROOT / workbook_filename(run_id)
        path.write_bytes(b"PK\x03\x04" + b"0" * 64)
        with _LOCK:
            _JOBS.clear()
        status = self.client.get(f"/api/status/{run_id}").get_json()
        self.assertEqual(status.get("status"), "success")
        self.assertTrue(status.get("download_ready"))
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 200)
        self.assertEqual(dl.data[:2], b"PK")

    def test_w12_failed_pipeline_has_no_fake_download(self):
        os.environ["STEEL_WEB_FAIL_STAGE"] = "VROOT1"
        res = self._post()
        run_id = res.get_json()["run_id"]
        status = self._wait(run_id)
        self.assertEqual(status["status"], "error")
        self.assertFalse(status.get("download_ready"))
        dl = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(dl.status_code, 400)
        self.assertNotEqual(dl.data[:2], b"PK")

    def test_w12_15_authority_keys_untouched(self):
        engine = config.ENGINE_ROOT / "src" / "PhaseW6_hybrid_production_authority"
        cfg = (engine / "config.py").read_text(encoding="utf-8")
        self.assertIn("cut_length_mm", cfg)
        self.assertIn("cut_length_m", cfg)
        handoff = (engine / "handoff.py").read_text(encoding="utf-8")
        self.assertIn("cut_length_unchanged", handoff)


if __name__ == "__main__":
    unittest.main()
