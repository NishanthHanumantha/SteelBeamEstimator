"""W.3 Fifth Set production-scale validation against Version10 Gunicorn."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8001"
ROOT = Path("/home/ubuntu/w3_smoke/smoke/Fifth Set Drawings")
GN = ROOT / "general_notes" / "SE-100_GENRAL NOTE_(SH-01 &SH-02)_R0 1.dxf"
FR = ROOT / "framing" / "9TH Floor_INIZIO_FRAMINIG_PLAN.dxf"
RE = ROOT / "reinforcement" / "SE-222_PODIUM FLOOR  REINFORCEMENT BEAM DETAILS (9TH FLOOR)_R0_(SH-01 TO 04).dxf"

PEAK = {
    "used_mb": 0,
    "avail_mb": 99999,
    "python_rss_sum_kb": 0,
    "python_rss_max_kb": 0,
    "cpu": 0.0,
}


def python_rss() -> tuple[int, int]:
    out = subprocess.check_output(["ps", "-eo", "rss,pcpu,cmd"], text=True)
    total = 0
    mx = 0
    cpu = 0.0
    for line in out.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        cmd = parts[2]
        if "python" not in cmd.lower() and "gunicorn" not in cmd.lower():
            continue
        rss = int(float(parts[0]))
        cpu += float(parts[1])
        total += rss
        mx = max(mx, rss)
    PEAK["cpu"] = max(PEAK["cpu"], cpu)
    return total, mx


def snap(tag: str) -> None:
    free = subprocess.check_output(["free", "-m"], text=True)
    lines = free.splitlines()
    mem = lines[1].split()
    used = int(mem[2])
    avail = int(mem[6]) if len(mem) > 6 else int(mem[3])
    PEAK["used_mb"] = max(PEAK["used_mb"], used)
    PEAK["avail_mb"] = min(PEAK["avail_mb"], avail)
    total_rss, max_rss = python_rss()
    PEAK["python_rss_sum_kb"] = max(PEAK["python_rss_sum_kb"], total_rss)
    PEAK["python_rss_max_kb"] = max(PEAK["python_rss_max_kb"], max_rss)
    print(
        "SNAP",
        tag,
        "used_mb",
        used,
        "avail_mb",
        avail,
        "py_rss_sum_mb",
        round(total_rss / 1024, 1),
        "py_rss_max_mb",
        round(max_rss / 1024, 1),
    )


def multipart(fields: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = "----W3FifthBoundary"
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


def post_estimate(fields, timeout=180):
    body, ctype = multipart(fields)
    req = urllib.request.Request(
        BASE + "/api/estimate",
        data=body,
        method="POST",
        headers={"Content-Type": ctype},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def main() -> int:
    for p in (GN, FR, RE):
        if not p.exists():
            print("MISSING", p)
            return 2
    total = GN.stat().st_size + FR.stat().st_size + RE.stat().st_size
    print("TEST_SET Fifth Set Drawings")
    print("TOTAL_MB", round(total / 1048576, 2))
    st, raw = get("/health")
    health = json.loads(raw.decode("utf-8"))
    print("HEALTH", st, health.get("engine_root"), health.get("busy"))
    fields = {
        "general_notes": (GN.name, GN.read_bytes()),
        "framing": (FR.name, FR.read_bytes()),
        "reinforcement": (RE.name, RE.read_bytes()),
    }
    snap("before")
    t0 = time.perf_counter()
    code, payload = post_estimate(fields)
    print("ESTIMATE", code, payload)
    if code != 200:
        return 1
    run_id = payload["run_id"]
    last = {}
    while time.perf_counter() - t0 < 2400:
        st, raw = get(f"/api/status/{run_id}")
        last = json.loads(raw.decode("utf-8"))
        elapsed = round(time.perf_counter() - t0, 1)
        print("STATUS", last.get("status"), last.get("message"), last.get("error"), "elapsed", elapsed)
        snap(f"t={elapsed}")
        if last.get("status") in {"success", "error"}:
            break
        time.sleep(10)
    print("FINAL", json.dumps(last, indent=2))
    print("PEAK", json.dumps(PEAK, indent=2))
    if last.get("status") != "success":
        try:
            oom = subprocess.check_output(["dmesg", "-T"], text=True, stderr=subprocess.STDOUT)
            for line in oom.splitlines():
                if "oom" in line.lower() or "killed process" in line.lower():
                    print("DMESG", line)
        except Exception as exc:
            print("DMESG_ERR", exc)
        return 1
    st, raw = get(f"/api/download/{run_id}", timeout=180)
    out = Path("/tmp") / f"W3_fifth_{run_id}.xlsx"
    out.write_bytes(raw)
    print("DOWNLOAD", st, "bytes", len(raw), "pk", raw[:2], "t1", last.get("t1_executed"))
    print("SAVED", out)
    return 0 if st == 200 and raw[:2] == b"PK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
