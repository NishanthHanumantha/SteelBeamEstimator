"""W.9 First Set live Hybrid E2E against Version10 Gunicorn on Lightsail."""
from __future__ import annotations

import hashlib
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
PROTECTED = ("cut_length_mm", "cut_length_m", "spacing_mm", "stirrup_segments", "shape_code")
GEOM_KEYS = ("width_mm", "depth_mm", "span_mm", "clear_span_mm", "length_mm")


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
    boundary = "----W9SmokeBoundary"
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


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _bar_maps(model: dict) -> dict:
    out = {}
    for key in (
        "top_main_bars",
        "top_extra_bars",
        "bottom_main_bars",
        "bottom_extra_bars",
        "stirrups",
        "spacer_bars",
        "side_face_reinforcement",
    ):
        for bar in model.get(key) or []:
            if isinstance(bar, dict) and bar.get("bar_id"):
                out[(key, bar.get("bar_id"))] = bar
    return out


def audit_run(run_id: str) -> dict:
    root = RUNS / run_id
    w6 = root / "data/output/PhaseW6_hybrid_semantic_resolution"
    cov = _load(w6 / "hybrid_coverage.json") or {}
    obs = _load(w6 / "hybrid_observability.json") or {}
    handoff = _load(w6 / "hybrid_handoff_ledger.json") or {}
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
    evidence = w6 / "hybrid_evidence"
    manifests = list(evidence.glob("*/evidence_manifest.json")) if evidence.is_dir() else []
    primary = 0
    compat = 0
    unavailable = 0
    distinct_pair = 0
    same_pair = 0
    n_images_2 = 0
    vision_not_ready = 0
    sample_rows = []
    for man_path in sorted(manifests):
        man = _load(man_path) or {}
        bid = man.get("beam_id") or man_path.parent.name
        cls = str(man.get("evidence_class") or man.get("classification") or "").upper()
        if cls in ("PRIMARY", "P2610_PRIMARY"):
            primary += 1
        elif cls in ("FALLBACK", "COMPATIBILITY", "W6_COMPAT", "T1_COMPAT"):
            compat += 1
        elif cls in ("UNAVAILABLE",):
            unavailable += 1
        ctx = man_path.parent / "context" / "selected.png"
        det = man_path.parent / "detail" / "selected.png"
        ctx_ok = ctx.is_file()
        det_ok = det.is_file()
        same = False
        if ctx_ok and det_ok:
            same = _sha(ctx) == _sha(det)
            if same:
                same_pair += 1
            else:
                distinct_pair += 1
        if man.get("c3_status") == "VISION_NOT_READY" or "VISION_NOT_READY" in str(
            man.get("fallback_reason") or ""
        ):
            vision_not_ready += 1
        n_images_2 += 1
        if len(sample_rows) < 6 or cls in ("FALLBACK", "COMPATIBILITY"):
            sample_rows.append(
                {
                    "beam_id": bid,
                    "evidence_class": cls,
                    "selection_method": man.get("selection_method"),
                    "context_source": man.get("selected_context_source")
                    or man.get("context_source")
                    or ((man.get("context") or {}).get("source")),
                    "detail_source": man.get("selected_detail_source")
                    or man.get("detail_source")
                    or ((man.get("detail") or {}).get("source")),
                    "fallback_reason": man.get("fallback_reason"),
                    "c3_status": man.get("c3_status") or man.get("readiness"),
                    "context_exists": ctx_ok,
                    "detail_exists": det_ok,
                    "same_image": same,
                }
            )

    cut_over = 0
    stirrup_qty_over = 0
    geom_over = 0
    if isinstance(pre, dict) and isinstance(post, dict):
        pre_models = {m.get("beam_id"): m for m in (pre.get("models") or []) if isinstance(m, dict)}
        for model in post.get("models") or []:
            if not isinstance(model, dict):
                continue
            old = pre_models.get(model.get("beam_id")) or {}
            old_bars = _bar_maps(old)
            new_bars = _bar_maps(model)
            for ident, bar in new_bars.items():
                prev = old_bars.get(ident) or {}
                for key in PROTECTED:
                    if key in bar and key in prev and bar.get(key) != prev.get(key):
                        if key.startswith("cut_length"):
                            cut_over += 1
                if ident[0] == "stirrups":
                    if bar.get("quantity") != prev.get("quantity") and prev.get("quantity") is not None:
                        # quantity may be Vision-preferred on longitudinal; stirrup engineering quantity must hold
                        if "engineering" in str(bar.get("quantity_source") or "").lower():
                            stirrup_qty_over += 1
                    if bar.get("count") != prev.get("count") and prev.get("count") is not None:
                        if bar.get("spacing_mm") == prev.get("spacing_mm"):
                            stirrup_qty_over += 1
            for gkey in GEOM_KEYS:
                if gkey in model and gkey in old and model.get(gkey) != old.get(gkey):
                    geom_over += 1
            old_geom = old.get("geometry") if isinstance(old.get("geometry"), dict) else {}
            new_geom = model.get("geometry") if isinstance(model.get("geometry"), dict) else {}
            if old_geom and new_geom and old_geom != new_geom:
                geom_over += 1

    n_images_from_obs = 0
    beams_obs = []
    if isinstance(obs, dict):
        beams_obs = [b for b in (obs.get("beams") or []) if isinstance(b, dict)]
        for b in beams_obs:
            audit = b.get("audit") or {}
            if int(audit.get("n_images") or b.get("n_images") or 0) == 2:
                n_images_from_obs += 1

    payload = {
        "run_id": run_id,
        "coverage": {
            k: cov.get(k)
            for k in (
                "total_production_beams",
                "hybrid_eligible",
                "p2610_primary_evidence",
                "native_t1_crop",
                "generated_fallback_crop",
                "visual_context_unavailable",
                "evidence_packages_generated",
                "claude_invocations",
                "claude_attempted",
                "claude_success",
                "claude_failure",
                "deterministic_fallback",
                "hybrid_resolved",
                "unresolved",
                "unexplained",
                "identity_ok",
            )
        },
        "obs": {
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
        },
        "steel": {
            k: steel.get(k)
            for k in ("total_weight_kg", "total_beams", "total_bars", "calculation_method")
        },
        "evidence": {
            "manifest_count": len(manifests),
            "primary": primary,
            "compat_or_fallback": compat,
            "unavailable": unavailable,
            "distinct_context_detail": distinct_pair,
            "same_context_detail": same_pair,
            "vision_not_ready": vision_not_ready,
            "n_images_assumed_2_from_c5": n_images_2,
            "n_images_2_from_observability": n_images_from_obs,
            "sample": sample_rows,
        },
        "authority": {
            "cut_length_overwrites": cut_over,
            "stirrup_quantity_overwrites": stirrup_qty_over,
            "geometry_overwrites": geom_over,
            "handoff_protected_keys": (handoff.get("engineering_protected_keys") if isinstance(handoff, dict) else None),
        },
        "unexplained": cov.get("unexplained"),
        "identity_ok": cov.get("identity_ok"),
    }
    print("COVERAGE", json.dumps(payload["coverage"], indent=2))
    print("OBS", json.dumps(payload["obs"], indent=2))
    print("STEEL", json.dumps(payload["steel"]))
    print("EVIDENCE", json.dumps(payload["evidence"], indent=2, default=str))
    print("AUTHORITY", json.dumps(payload["authority"]))
    print("UNEXPLAINED", payload["unexplained"], "IDENTITY_OK", payload["identity_ok"])
    out = Path("/tmp") / f"W9_{run_id}_audit.json"
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print("AUDIT_JSON", out)
    return payload


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
        "key_status",
        hybrid.get("api_key_status"),
        "stages",
        health.get("production_stages"),
    )
    blob = json.dumps(health).lower()
    print("SECRET_LEAK", "sk-ant-" in blob)
    if hybrid.get("mode") != "production":
        print("NOT_PRODUCTION")
        return 3
    if health.get("phase") not in {"W.8", "W.9", "W.10", "W.11"}:
        print("UNEXPECTED_PHASE", health.get("phase"))
        return 4
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
            last.get("progress"),
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
    print("ELAPSED_S", round(time.perf_counter() - t0, 1))
    if last.get("status") != "success":
        snap("failed")
        return 1
    st, raw = get(f"/api/download/{run_id}", timeout=120)
    out = Path("/tmp") / f"W9_{run_id}.xlsx"
    out.write_bytes(raw)
    print("DOWNLOAD", st, "bytes", len(raw), "pk", raw[:2])
    audit_run(run_id)
    snap("after")
    return 0 if st == 200 and raw[:2] == b"PK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
