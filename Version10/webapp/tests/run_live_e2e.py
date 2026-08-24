"""Optional live Version10 pipeline E2E (slow). Set STEEL_WEB_LIVE_E2E=1.

Uses the Flask test client by default, or HTTP if STEEL_WEB_BASE is set
(e.g. http://127.0.0.1:5000).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WEBAPP_ROOT.parent.parent
if str(WEBAPP_ROOT) not in sys.path:
    sys.path.insert(0, str(WEBAPP_ROOT))

FIRST_SET = REPO_ROOT / "Test_Input" / "1st Set Drawings-Galera_OHT&STP"
GN = FIRST_SET / "general_note" / "SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf"
FR = FIRST_SET / "framing" / "SampleBeam_FramingPlan_DXF.dxf"
RE = FIRST_SET / "reinforcement" / "SampleBeam_Reinforcement&StirrupsDetials_DXF.dxf"


def _multipart(fields: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = "----W2LiveBoundary"
    chunks: list[bytes] = []
    for name, (filename, data) in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("ascii"))
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode("ascii")
        )
        chunks.append(data)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class HttpClient:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")

    def get(self, path: str):
        req = urllib.request.Request(self.base + path)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                return resp.status, raw, dict(resp.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), dict(exc.headers)

    def post_files(self, path: str, files: dict[str, Path]):
        fields = {}
        for name, p in files.items():
            fields[name] = (p.name, p.read_bytes())
        body, ctype = _multipart(fields)
        req = urllib.request.Request(
            self.base + path,
            data=body,
            method="POST",
            headers={"Content-Type": ctype},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                payload = json.loads(exc.read().decode("utf-8"))
            except Exception:
                payload = {"ok": False, "error": str(exc)}
            return exc.code, payload


def main() -> int:
    os.environ.pop("STEEL_WEB_PIPELINE_MODE", None)
    os.environ.pop("STEEL_WEB_FAIL_STAGE", None)
    for path in (GN, FR, RE):
        if not path.exists():
            print(f"MISSING_INPUT {path}")
            return 2

    base = (os.environ.get("STEEL_WEB_BASE") or "").strip()
    if base:
        client = HttpClient(base)
        status, raw, _ = client.get("/health")
        health = json.loads(raw.decode("utf-8"))
        print("HEALTH", health.get("engine_root"), "T1", health.get("t1_included"), status)
        code, payload = client.post_files(
            "/api/estimate",
            {"general_notes": GN, "framing": FR, "reinforcement": RE},
        )
        print("ESTIMATE", code, payload)
        if code != 200:
            return 1
        run_id = payload["run_id"]
        busy_code, busy_payload = client.post_files(
            "/api/estimate",
            {"general_notes": GN, "framing": FR, "reinforcement": RE},
        )
        print("BUSY", busy_code, busy_payload)
        deadline = time.time() + int(os.environ.get("STEEL_WEB_LIVE_TIMEOUT_S", "10800"))
        last = {}
        while time.time() < deadline:
            st, raw, _ = client.get(f"/api/status/{run_id}")
            last = json.loads(raw.decode("utf-8"))
            print("STATUS", last.get("status"), last.get("message"), last.get("error"))
            if last.get("status") in {"success", "error"}:
                break
            time.sleep(15)
        print("FINAL", last)
        if last.get("status") != "success":
            return 1
        dl_status, dl_raw, headers = client.get(f"/api/download/{run_id}")
        print(
            "DOWNLOAD",
            dl_status,
            last.get("workbook_name"),
            "t1",
            last.get("t1_executed"),
            "bytes",
            len(dl_raw),
            "pk",
            dl_raw[:2],
        )
        return 0 if dl_status == 200 and dl_raw[:2] == b"PK" else 1

    from app import create_app
    import config

    app = create_app()
    client = app.test_client()
    health = client.get("/health").get_json()
    print("HEALTH", health["engine_root"], "T1", health["t1_included"])

    data = {
        "general_notes": (GN.open("rb"), GN.name),
        "framing": (FR.open("rb"), FR.name),
        "reinforcement": (RE.open("rb"), RE.name),
    }
    res = client.post("/api/estimate", data=data, content_type="multipart/form-data")
    payload = res.get_json() or {}
    print("ESTIMATE", res.status_code, payload)
    if res.status_code != 200:
        return 1
    run_id = payload["run_id"]
    busy = client.post("/api/estimate", data={
        "general_notes": (GN.open("rb"), GN.name),
        "framing": (FR.open("rb"), FR.name),
        "reinforcement": (RE.open("rb"), RE.name),
    }, content_type="multipart/form-data")
    print("BUSY", busy.status_code, busy.get_json())
    deadline = time.time() + int(os.environ.get("STEEL_WEB_LIVE_TIMEOUT_S", "10800"))
    last = {}
    while time.time() < deadline:
        last = client.get(f"/api/status/{run_id}").get_json() or {}
        print("STATUS", last.get("status"), last.get("message"), last.get("error"))
        if last.get("status") in {"success", "error"}:
            break
        time.sleep(10)
    print("FINAL", last)
    if last.get("status") != "success":
        return 1
    download = client.get(f"/api/download/{run_id}")
    print("DOWNLOAD", download.status_code, last.get("workbook_name"), "t1", last.get("t1_executed"))
    excel = config.WEB_RUNS_ROOT / run_id / config.VB1_EXCEL_REL
    print("EXCEL", excel, "exists", excel.exists(), "size", excel.stat().st_size if excel.exists() else 0)
    t1 = config.WEB_RUNS_ROOT / run_id / config.T1_EVIDENCE_REL
    print("T1_ARTEFACT", t1.exists())
    return 0 if download.status_code == 200 and excel.exists() else 1


if __name__ == "__main__":
    if os.environ.get("STEEL_WEB_LIVE_E2E") != "1":
        print("Set STEEL_WEB_LIVE_E2E=1 to run the live Version10 pipeline.")
        sys.exit(0)
    raise SystemExit(main())
