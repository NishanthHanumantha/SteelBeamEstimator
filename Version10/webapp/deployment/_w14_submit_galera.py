#!/usr/bin/env python3
"""Submit W.14 Galera DXFs to local production gunicorn. No secrets."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path("/tmp/w14_galera")
FILES = {
    "general_notes": ("SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf", ROOT / "gn.dxf"),
    "framing": ("Galera_GF_FramingPlan.dxf", ROOT / "fr.dxf"),
    "reinforcement": ("Galera_GF_BeamReinforcementDetails.dxf", ROOT / "re.dxf"),
}
URL = "http://127.0.0.1:8001/api/estimate"


def main() -> int:
    boundary = "----w14LocalBoundary"
    chunks = []
    for field, (filename, path) in FILES.items():
        data = path.read_bytes()
        print(f"FILE {field} {filename} {len(data)}")
        chunks.append(f"--{boundary}\r\n".encode("ascii"))
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode("ascii")
        )
        chunks.append(data)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    body = b"".join(chunks)
    req = urllib.request.Request(
        URL,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
        print("HTTP", resp.status)
        print(json.dumps(payload))
        print("RUN_ID", payload.get("run_id"))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
