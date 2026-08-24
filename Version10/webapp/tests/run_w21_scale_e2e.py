"""W.2.1 production-scale live E2E against a running web server (Fifth Set)."""
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

FIFTH = REPO_ROOT / "Test_Input" / "Fifth Set Drawings"
GN = FIFTH / "general_notes" / "SE-100_GENRAL NOTE_(SH-01 &SH-02)_R0 1.dxf"
FR = FIFTH / "framing" / "9TH Floor_INIZIO_FRAMINIG_PLAN.dxf"
RE = FIFTH / "reinforcement" / "SE-222_PODIUM FLOOR  REINFORCEMENT BEAM DETAILS (9TH FLOOR)_R0_(SH-01 TO 04).dxf"
BASE = (os.environ.get("STEEL_WEB_BASE") or "http://127.0.0.1:8000").rstrip("/")


def _multipart(fields: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = "----W21ScaleBoundary"
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


def get(path: str, timeout: int = 60):
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main() -> int:
    for path in (GN, FR, RE):
        if not path.exists():
            print("MISSING_INPUT", path)
            return 2
    print("TEST_SET Fifth Set Drawings")
    print("GN", GN, "MB", round(GN.stat().st_size / 1048576, 2))
    print("FR", FR, "MB", round(FR.stat().st_size / 1048576, 2))
    print("RE", RE, "MB", round(RE.stat().st_size / 1048576, 2))
    st, raw = get("/health")
    health = json.loads(raw.decode("utf-8"))
    print("HEALTH", st, health.get("engine_root"), "T1", health.get("t1_included"))
    fields = {
        "general_notes": (GN.name, GN.read_bytes()),
        "framing": (FR.name, FR.read_bytes()),
        "reinforcement": (RE.name, RE.read_bytes()),
    }
    body, ctype = _multipart(fields)
    req = urllib.request.Request(
        BASE + "/api/estimate",
        data=body,
        method="POST",
        headers={"Content-Type": ctype},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            code = resp.status
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))
        code = exc.code
        print("ESTIMATE", code, payload)
        return 1
    print("ESTIMATE", code, payload)
    run_id = payload["run_id"]
    deadline = time.time() + int(os.environ.get("STEEL_WEB_LIVE_TIMEOUT_S", "14400"))
    last = {}
    while time.time() < deadline:
        st, raw = get(f"/api/status/{run_id}", timeout=60)
        last = json.loads(raw.decode("utf-8"))
        print("STATUS", last.get("status"), last.get("message"), last.get("error"), "elapsed", round(time.perf_counter() - t0, 1))
        if last.get("status") in {"success", "error"}:
            break
        time.sleep(20)
    print("FINAL", json.dumps(last, indent=2))
    if last.get("status") != "success":
        return 1
    st, raw = get(f"/api/download/{run_id}", timeout=120)
    print("DOWNLOAD", st, "bytes", len(raw), "pk", raw[:2], "t1", last.get("t1_executed"))
    out = WEBAPP_ROOT / "outputs" / f"W21_Fifth_{run_id}.xlsx"
    out.write_bytes(raw)
    print("SAVED", out)
    return 0 if st == 200 and raw[:2] == b"PK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
