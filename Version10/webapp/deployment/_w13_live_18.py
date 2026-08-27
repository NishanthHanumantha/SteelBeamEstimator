#!/usr/bin/env python3
"""Submit the retained 18-beam SampleBeam drawing to local Gunicorn. No secrets."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8001"
STAGING = Path(
    "/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_102310_1a616a17"
)


def post() -> str:
    files = {
        "general_notes": next((STAGING / "general_notes").glob("*.dxf")),
        "framing": next((STAGING / "framing").glob("*.dxf")),
        "reinforcement": next((STAGING / "reinforcement").glob("*.dxf")),
    }
    boundary = "----w13Boundary"
    chunks = []
    for field, path in files.items():
        data = path.read_bytes()
        chunks.append(f"--{boundary}\r\n".encode("ascii"))
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{field}"; filename="{path.name}"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode("ascii")
        )
        chunks.append(data)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    body = b"".join(chunks)
    req = urllib.request.Request(
        BASE + "/api/estimate",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    print("START", payload)
    return payload["run_id"]


def poll(run_id: str) -> dict:
    deadline = time.time() + 3600
    last = {}
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE + f"/api/status/{run_id}", timeout=30) as resp:
                last = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            print("POLL_ERR", type(exc).__name__)
            time.sleep(5)
            continue
        status = last.get("status")
        print(
            "POLL",
            status,
            last.get("message"),
            last.get("elapsed_s"),
            (last.get("progress") or {}).get("beam_id"),
        )
        if status in {"success", "error"}:
            return last
        time.sleep(5)
    raise SystemExit("timeout")


def main() -> None:
    run_id = post()
    status = poll(run_id)
    print("FINAL", json.dumps({k: status.get(k) for k in (
        "ok", "run_id", "status", "workbook_name", "duration_s", "download_ready",
        "excel_exists", "result_lifecycle", "summary", "error", "hybrid",
    )}, default=str))
    Path("/tmp/w13_live_run.json").write_text(json.dumps(status, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
