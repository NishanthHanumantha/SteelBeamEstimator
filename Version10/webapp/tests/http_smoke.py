"""Quick HTTP smoke against a running Version10 webapp (no live pipeline)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5000"


def get(path: str):
    try:
        with urllib.request.urlopen(BASE + path, timeout=20) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def main() -> None:
    status, raw, _ = get("/health")
    health = json.loads(raw.decode("utf-8"))
    print("HEALTH_STATUS", status)
    print("ENGINE_LABEL", health.get("engine_label"))
    print("ENGINE_ROOT", health.get("engine_root"))
    print("T1", health.get("t1_included"), health.get("production_stages"))
    print("APP_RELEASE", health.get("app_release"))
    html = get("/")[1].decode("utf-8", "replace")
    print("HOME_HAS_895", "8.9.5" in html)
    print("HOME_HAS_V10", "Version10 production pipeline" in html)

    boundary = "----x"
    def part(name: str, filename: str, data: bytes) -> bytes:
        hdr = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("ascii")
        return hdr + data + b"\r\n"

    dxf = b"  0\nSECTION\n  2\nHEADER\n  0\nENDSEC\n  0\nEOF\n" * 4
    body = (
        part("general_notes", "notes.txt", b"hello")
        + part("framing", "framing.dxf", dxf)
        + part("reinforcement", "rebar.dxf", dxf)
        + f"--{boundary}--\r\n".encode("ascii")
    )
    req = urllib.request.Request(
        BASE + "/api/estimate",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        print("INVALID_UNEXPECTED_200")
    except urllib.error.HTTPError as exc:
        print("INVALID", exc.code, exc.read().decode("utf-8", "replace"))

    status, raw, _ = get("/api/download/not-a-run")
    print("DOWNLOAD_MISSING", status, raw.decode("utf-8", "replace"))


if __name__ == "__main__":
    main()
