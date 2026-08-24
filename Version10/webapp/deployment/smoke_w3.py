"""W.3 small-smoke + single-flight against local Version10 Gunicorn."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8001"
ROOT = Path("/home/ubuntu/w3_smoke/smoke/1st Set Drawings-Galera_OHT&STP")
GN = ROOT / "general_note" / "SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf"
FR = ROOT / "framing" / "SampleBeam_FramingPlan_DXF.dxf"
RE = ROOT / "reinforcement" / "SampleBeam_Reinforcement&StirrupsDetials_DXF.dxf"


def snap(tag: str) -> None:
    free = subprocess.check_output(["free", "-m"], text=True)
    df = subprocess.check_output(["df", "-h", "/"], text=True)
    try:
        ps = subprocess.check_output(
            ["ps", "-o", "pid,rss,pcpu,cmd", "-C", "gunicorn"], text=True
        )
    except subprocess.CalledProcessError:
        ps = "gunicorn-missing"
    print("SNAP", tag)
    print(free)
    print(df.splitlines()[0])
    print(df.splitlines()[1])
    print(ps)


def multipart(fields: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = "----W3SmokeBoundary"
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
    print("BYTES", GN.stat().st_size, FR.stat().st_size, RE.stat().st_size)
    st, raw = get("/health")
    health = json.loads(raw.decode("utf-8"))
    print("HEALTH", st, health.get("engine_root"), health.get("engine_label"), health.get("t1_included"))
    fields = {
        "general_notes": (GN.name, GN.read_bytes()),
        "framing": (FR.name, FR.read_bytes()),
        "reinforcement": (RE.name, RE.read_bytes()),
    }
    snap("before_estimate")
    t0 = time.perf_counter()
    code, payload = post_estimate(fields)
    print("ESTIMATE", code, payload)
    if code != 200:
        return 1
    busy_code, busy_payload = post_estimate(fields)
    print("BUSY", busy_code, busy_payload)
    run_id = payload["run_id"]
    last = {}
    while time.perf_counter() - t0 < 1800:
        st, raw = get(f"/api/status/{run_id}")
        last = json.loads(raw.decode("utf-8"))
        elapsed = round(time.perf_counter() - t0, 1)
        print(
            "STATUS",
            last.get("status"),
            last.get("message"),
            last.get("error"),
            "elapsed",
            elapsed,
        )
        snap(f"t={elapsed}")
        if last.get("status") in {"success", "error"}:
            break
        time.sleep(15)
    print("FINAL", json.dumps(last, indent=2))
    if last.get("status") != "success":
        return 1
    st, raw = get(f"/api/download/{run_id}", timeout=120)
    out = Path("/tmp") / f"W3_smoke_{run_id}.xlsx"
    out.write_bytes(raw)
    print("DOWNLOAD", st, "bytes", len(raw), "pk", raw[:2], "t1", last.get("t1_executed"))
    print("SAVED", out)
    run_root = Path(
        "/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs"
    ) / run_id
    print("RUN_ROOT", run_root, "exists", run_root.is_dir())
    print("ISOLATED_NOT_V8", "Version8" not in str(run_root))
    t1 = run_root / "data/output/PhaseT1_geometric_stirrup_evidence/stirrup_geometry_evidence.json"
    print("T1_ARTEFACT", t1.exists(), t1)
    snap("after")
    code2, payload2 = post_estimate(fields)
    print("SECOND_AFTER", code2, payload2)
    return 0 if st == 200 and raw[:2] == b"PK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
