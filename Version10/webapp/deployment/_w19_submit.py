#!/usr/bin/env python3
"""Submit renamed DXFs to local Gunicorn with original display filenames."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/w19_galera")
URL = "http://127.0.0.1:8001/api/estimate"
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))


def main() -> int:
    boundary = "----w19LocalBoundary"
    chunks = []
    for field, spec in MANIFEST.items():
        filename = spec["filename"]
        path = ROOT / spec["file"]
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
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
        print("HTTP", resp.status)
        print(json.dumps(payload))
        print("RUN_ID", payload.get("run_id"))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
