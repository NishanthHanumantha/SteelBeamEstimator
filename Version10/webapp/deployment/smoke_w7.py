"""W.7 First Set live Hybrid E2E against local Version10 Gunicorn."""
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
RUNS = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs")


def snap(tag: str) -> None:
    free = subprocess.check_output(["free", "-m"], text=True)
    try:
        ps = subprocess.check_output(
            ["ps", "-o", "pid,rss,pcpu,cmd", "-C", "gunicorn"], text=True
        )
    except subprocess.CalledProcessError:
        ps = "gunicorn-missing"
    print("SNAP", tag)
    print(free)
    print(ps)


def multipart(fields: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = "----W7SmokeBoundary"
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


def _load(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def audit_run(run_id: str) -> None:
    root = RUNS / run_id
    w6 = root / "data/output/PhaseW6_hybrid_semantic_resolution"
    cov = _load(w6 / "hybrid_coverage.json") or {}
    obs = _load(w6 / "hybrid_observability.json") or {}
    steel = _load(root / "data/output/Production_Output/steel_weight_summary.json") or {}
    pre = _load(
        root
        / "data/output/PhaseR1.3_pipeline_integration"
        / "beam_reinforcement_models_production.pre_hybrid.json"
    )
    post = _load(
        root
        / "data/output/PhaseR1.3_pipeline_integration"
        / "beam_reinforcement_models_production.json"
    )
    print("COVERAGE", json.dumps({
        k: cov.get(k)
        for k in (
            "total_production_beams",
            "hybrid_eligible",
            "native_t1_crop",
            "generated_fallback_crop",
            "visual_context_unavailable",
            "claude_invocations",
            "claude_success",
            "claude_failure",
            "deterministic_fallback",
            "unresolved",
            "unexplained",
            "identity_ok",
        )
    }, indent=2))
    print("OBS", json.dumps({
        k: obs.get(k)
        for k in (
            "classification",
            "hybrid_mode",
            "claude_invocation_count",
            "successful_invocation_count",
            "failed_invocation_count",
            "hybrid_latency_s",
            "model",
            "production_authority_applied",
            "beams_patched",
            "fields_patched",
            "fallback_used",
        )
    }, indent=2))
    print("STEEL", json.dumps({
        k: steel.get(k)
        for k in ("total_weight_kg", "total_beams", "total_bars", "calculation_method")
    }))
    cut_changed = 0
    cut_same = 0
    if isinstance(pre, dict) and isinstance(post, dict):
        pre_models = {m.get("beam_id"): m for m in (pre.get("models") or []) if isinstance(m, dict)}
        for model in post.get("models") or []:
            if not isinstance(model, dict):
                continue
            old = pre_models.get(model.get("beam_id")) or {}
            for key in (
                "top_main_bars",
                "top_extra_bars",
                "bottom_main_bars",
                "bottom_extra_bars",
                "stirrups",
                "spacer_bars",
                "side_face_reinforcement",
            ):
                old_bars = {b.get("bar_id"): b for b in (old.get(key) or []) if isinstance(b, dict)}
                for bar in model.get(key) or []:
                    if not isinstance(bar, dict):
                        continue
                    prev = old_bars.get(bar.get("bar_id")) or {}
                    if "cut_length_mm" in bar or "cut_length_mm" in prev:
                        if bar.get("cut_length_mm") == prev.get("cut_length_mm"):
                            cut_same += 1
                        else:
                            cut_changed += 1
    print("CUT_LENGTH_SAME", cut_same, "CUT_LENGTH_CHANGED", cut_changed)
    crops = w6 / "crops"
    t1 = root / "data/output/PhaseT1_geometric_stirrup_evidence/opencv_renders"
    print("W6_CROPS", len(list(crops.glob("*_crop.png"))) if crops.is_dir() else 0)
    print("T1_CROPS", len(list(t1.glob("*_crop.png"))) if t1.is_dir() else 0)


def main() -> int:
    for p in (GN, FR, RE):
        if not p.exists():
            print("MISSING", p)
            return 2
    st, raw = get("/health")
    health = json.loads(raw.decode("utf-8"))
    hybrid = health.get("hybrid") or {}
    print(
        "HEALTH",
        st,
        health.get("phase"),
        health.get("app_release"),
        hybrid.get("mode"),
        "key",
        hybrid.get("api_key_configured"),
        "stages",
        health.get("production_stages"),
    )
    blob = json.dumps(health).lower()
    print("SECRET_LEAK", "sk-ant-" in blob)
    if hybrid.get("mode") != "production":
        print("NOT_PRODUCTION")
        return 3
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
    while time.perf_counter() - t0 < 5400:
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
        if int(elapsed) % 60 < 20:
            snap(f"t={elapsed}")
        if last.get("status") in {"success", "error"}:
            break
        time.sleep(20)
    print("FINAL_STATUS", last.get("status"), last.get("workbook_name"))
    print("FINAL_HYBRID", json.dumps(last.get("hybrid") or {}, indent=2))
    print("FINAL_SUMMARY", json.dumps(last.get("summary") or {}, indent=2))
    if last.get("status") != "success":
        snap("failed")
        return 1
    st, raw = get(f"/api/download/{run_id}", timeout=120)
    out = Path("/tmp") / f"W7_{run_id}.xlsx"
    out.write_bytes(raw)
    print("DOWNLOAD", st, "bytes", len(raw), "pk", raw[:2])
    audit_run(run_id)
    snap("after")
    return 0 if st == 200 and raw[:2] == b"PK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
