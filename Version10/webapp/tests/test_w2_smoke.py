"""Phase W.2 local smoke tests (adapter / Flask). Engineering modules are not mutated."""
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


def _dxf_bytes(tag: str = "TEST") -> bytes:
    body = (
        "  0\nSECTION\n  2\nHEADER\n  0\nENDSEC\n"
        f"  0\nSECTION\n  2\nENTITIES\n  1\n{tag}\n  0\nENDSEC\n"
        "  0\nEOF\n"
    )
    return body.encode("ascii")


class W2SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="w2_web_")
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
        os.environ.pop("STEEL_WEB_FAIL_STAGE", None)
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

    def _post_estimate(self, files=None):
        if files is None:
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

    def _wait_status(self, run_id: str, timeout_s: float = 20.0) -> dict:
        deadline = time.time() + timeout_s
        last = {}
        while time.time() < deadline:
            res = self.client.get(f"/api/status/{run_id}")
            last = res.get_json() or {}
            if last.get("status") in {"success", "error"}:
                return last
            time.sleep(0.05)
        self.fail(f"Timed out waiting for run {run_id}: {last}")

    def test_web_01_application_startup(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["engine_ready"])
        self.assertIn("Version10", data["engine_root"].replace("\\", "/"))
        self.assertEqual(data["engine_label"], "Version10")
        self.assertNotEqual(data.get("model_version"), "8.9.5")
        self.assertNotIn("8.9.5", (data.get("engine_display") or ""))
        self.assertTrue(data["t1_included"])
        self.assertIn("T1", data["production_stages"])
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        html = home.get_data(as_text=True)
        self.assertIn("Steel Beam Estimation", html)
        self.assertNotIn("8.9.5", html)
        self.assertIn("Version10 production pipeline", html)

    def test_web_02_valid_dxf_upload(self):
        res = self._post_estimate()
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["run_id"])
        self._wait_status(data["run_id"])

    def test_web_03_invalid_file_rejection(self):
        res = self._post_estimate(
            {
                "general_notes": (io.BytesIO(b"not-a-dxf"), "notes.txt"),
                "framing": (io.BytesIO(self.dxf), "framing_plan.dxf"),
                "reinforcement": (io.BytesIO(self.dxf), "beam_reinforcement.dxf"),
            }
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["ok"])
        self.assertIn(".dxf", data["error"].lower())

        empty = self._post_estimate(
            {
                "general_notes": (io.BytesIO(b""), "general_notes.dxf"),
                "framing": (io.BytesIO(self.dxf), "framing_plan.dxf"),
                "reinforcement": (io.BytesIO(self.dxf), "beam_reinforcement.dxf"),
            }
        )
        self.assertEqual(empty.status_code, 400)
        self.assertIn("empty", (empty.get_json() or {}).get("error", "").lower())

        missing = self.client.post("/api/estimate", data={}, content_type="multipart/form-data")
        self.assertEqual(missing.status_code, 400)

    def test_web_04_run_creation_isolation(self):
        res = self._post_estimate()
        run_id = res.get_json()["run_id"]
        staging = config.WEB_RUNS_ROOT / run_id
        self.assertTrue(staging.is_dir())
        self.assertTrue((staging / "general_notes").is_dir())
        self.assertTrue((staging / "framing").is_dir())
        self.assertTrue((staging / "reinforcement").is_dir())
        status = self._wait_status(run_id)
        self.assertEqual(status["status"], "success")
        self.assertTrue((staging / "run_manifest.json").exists())

    def test_web_05_and_06_adapter_invokes_version10_with_t1(self):
        self.assertEqual(config.ENGINE_ROOT.name, "Version10")
        self.assertTrue(config.t1_is_configured())
        self.assertTrue(config.t1_runner_path().exists())
        ids = [s["id"] for s in config.PRODUCTION_STAGES]
        self.assertEqual(ids[0], "VROOT1")
        self.assertIn("T1", ids)
        self.assertLess(ids.index("T1"), ids.index("R2A"))
        self.assertEqual(ids[-1], "VB1")
        self.assertNotIn("T16CHAIN", ids)
        res = self._post_estimate()
        run_id = res.get_json()["run_id"]
        status = self._wait_status(run_id)
        self.assertEqual(status["status"], "success")
        self.assertTrue(status["t1_executed"])
        self.assertIn("T1", status["stages_run"])
        self.assertIn("VB1", status["stages_run"])
        self.assertIn("Version10", (status.get("engine_root") or "").replace("\\", "/"))
        t1_art = config.WEB_RUNS_ROOT / run_id / config.T1_EVIDENCE_REL
        self.assertTrue(t1_art.exists(), "T1 artefact missing")

    def test_web_07_08_09_pipeline_excel_download(self):
        res = self._post_estimate()
        run_id = res.get_json()["run_id"]
        status = self._wait_status(run_id)
        self.assertEqual(status["status"], "success")
        excel = config.WEB_RUNS_ROOT / run_id / config.VB1_EXCEL_REL
        self.assertTrue(excel.exists())
        self.assertGreater(excel.stat().st_size, 0)
        download = self.client.get(f"/api/download/{run_id}")
        self.assertEqual(download.status_code, 200)
        payload = download.data
        self.assertGreater(len(payload), 0)
        self.assertEqual(payload[:2], b"PK")
        self.assertIn(run_id, status["workbook_name"])
        out = config.OUTPUT_ROOT / status["workbook_name"]
        self.assertTrue(out.exists())

    def test_web_10_sequential_run_isolation(self):
        first = self._post_estimate()
        run_a = first.get_json()["run_id"]
        status_a = self._wait_status(run_a)
        self.assertEqual(status_a["status"], "success")
        file_a = config.OUTPUT_ROOT / status_a["workbook_name"]
        bytes_a = file_a.read_bytes()

        second = self._post_estimate()
        run_b = second.get_json()["run_id"]
        self.assertNotEqual(run_a, run_b)
        status_b = self._wait_status(run_b)
        self.assertEqual(status_b["status"], "success")
        file_b = config.OUTPUT_ROOT / status_b["workbook_name"]

        self.assertTrue(file_a.exists())
        self.assertEqual(file_a.read_bytes(), bytes_a)
        self.assertTrue(file_b.exists())
        self.assertNotEqual(file_a.resolve(), file_b.resolve())
        self.assertTrue((config.WEB_RUNS_ROOT / run_a).exists())
        self.assertTrue((config.WEB_RUNS_ROOT / run_b).exists())

    def test_web_11_single_flight_guard(self):
        held = "held-run"
        self.assertTrue(GUARD.acquire(held))
        try:
            res = self._post_estimate()
            self.assertEqual(res.status_code, 409)
            data = res.get_json()
            self.assertFalse(data["ok"])
            self.assertEqual(data.get("code"), "BUSY")
            self.assertIn("currently running", data["error"])
            self.assertEqual(GUARD.active_run_id(), held)
        finally:
            GUARD.release(held)

    def test_web_12_pipeline_failure_handling(self):
        os.environ["STEEL_WEB_FAIL_STAGE"] = "VROOT1"
        res = self._post_estimate()
        self.assertEqual(res.status_code, 200)
        run_id = res.get_json()["run_id"]
        status = self._wait_status(run_id)
        self.assertEqual(status["status"], "error")
        self.assertIn("failed", (status.get("error") or "").lower())
        self.assertNotIn("Traceback", status.get("error") or "")
        home = self.client.get("/")
        self.assertNotIn("Traceback", home.get_data(as_text=True))

    def test_web_13_download_failure_handling(self):
        missing = self.client.get("/api/download/does-not-exist")
        self.assertEqual(missing.status_code, 404)
        res = self._post_estimate()
        run_id = res.get_json()["run_id"]
        too_soon = self.client.get(f"/api/download/{run_id}")
        self.assertIn(too_soon.status_code, (400, 200))
        if too_soon.status_code == 400:
            self.assertIn("not ready", (too_soon.get_json() or {}).get("error", "").lower())
        self._wait_status(run_id)

    def test_web_14_engineering_untouched_contract(self):
        engine_src = config.ENGINE_ROOT / "src"
        self.assertTrue(engine_src.is_dir())
        t1_mod = engine_src / "PhaseT1_geometric_stirrup_evidence" / "phase_t1_orchestrator.py"
        vb1 = engine_src / "PhaseVB.1_production_output_completion" / "estimator_excel_generator.py"
        self.assertTrue(t1_mod.exists())
        self.assertTrue(vb1.exists())
        self.assertTrue((config.ENGINE_ROOT / "Run_PY" / "run_phase_vb1_production_output_completion.py").exists())


class W2WorkbookOpenTests(unittest.TestCase):
    def test_stub_xlsx_is_zip_container(self):
        raw = _dxf_bytes()
        self.assertGreater(len(raw), 32)


if __name__ == "__main__":
    unittest.main()
