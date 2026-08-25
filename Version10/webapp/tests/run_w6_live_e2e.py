"""Optional live W.6 Hybrid production-authority E2E.

Does not print secrets. Uses repo-root .env via python-dotenv override=False
or an already-exported ANTHROPIC_API_KEY.

Env:
  STEEL_WEB_LIVE_E2E=1          required
  W6_LIVE_MAX_CALLS             optional live-call cap (default unlimited / production)
  STEEL_WEB_LIVE_TIMEOUT_S      default 10800
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WEBAPP_ROOT.parent.parent
if str(WEBAPP_ROOT) not in sys.path:
    sys.path.insert(0, str(WEBAPP_ROOT))

FIRST_SET = REPO_ROOT / "Test_Input" / "1st Set Drawings-Galera_OHT&STP"
GN = FIRST_SET / "general_note" / "SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf"
FR = FIRST_SET / "framing" / "SampleBeam_FramingPlan_DXF.dxf"
RE = FIRST_SET / "reinforcement" / "SampleBeam_Reinforcement&StirrupsDetials_DXF.dxf"


def _prime_dotenv() -> str:
    if (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        return "PRESENT"
    env_path = REPO_ROOT / ".env"
    if env_path.is_file():
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    if (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        return "PRESENT"
    return "ABSENT"


def main() -> int:
    if os.environ.get("STEEL_WEB_LIVE_E2E") != "1":
        print("SKIP set STEEL_WEB_LIVE_E2E=1")
        return 0
    os.environ.pop("STEEL_WEB_PIPELINE_MODE", None)
    os.environ.pop("STEEL_WEB_FAIL_STAGE", None)
    key_status = _prime_dotenv()
    print("API_KEY_CONFIGURED", "YES" if key_status == "PRESENT" else "NO")
    if key_status != "PRESENT":
        print("FAIL ANTHROPIC_API_KEY not configured")
        return 2
    for path in (GN, FR, RE):
        if not path.exists():
            print("MISSING_INPUT", path)
            return 2

    os.environ["HYBRID_MODE"] = "production"
    max_calls = (os.environ.get("W6_LIVE_MAX_CALLS") or "").strip()
    if max_calls:
        os.environ["HYBRID_MAX_LIVE_CALLS"] = max_calls
    else:
        os.environ.pop("HYBRID_MAX_LIVE_CALLS", None)
    os.environ.pop("HYBRID_MAX_WALL_S", None)

    import config
    from app import create_app

    app = create_app()
    client = app.test_client()
    health = client.get("/health").get_json()
    print("HEALTH_PHASE", health.get("phase"))
    print("HEALTH_HYBRID_MODE", (health.get("hybrid") or {}).get("mode"))
    print("HEALTH_API_KEY_CONFIGURED", (health.get("hybrid") or {}).get("api_key_configured"))
    print("HEALTH_PRODUCTION_AUTHORITY", (health.get("hybrid") or {}).get("production_authority"))
    files = {
        "general_notes": (GN.open("rb"), GN.name),
        "framing": (FR.open("rb"), FR.name),
        "reinforcement": (RE.open("rb"), RE.name),
    }
    t0 = time.perf_counter()
    res = client.post("/api/estimate", data=files, content_type="multipart/form-data")
    payload = res.get_json() or {}
    print("ESTIMATE", res.status_code, {k: payload.get(k) for k in ("run_id", "ok", "error")})
    if res.status_code != 200:
        return 1
    run_id = payload["run_id"]
    deadline = time.time() + int(os.environ.get("STEEL_WEB_LIVE_TIMEOUT_S", "10800"))
    last = {}
    while time.time() < deadline:
        last = client.get(f"/api/status/{run_id}").get_json() or {}
        print("STATUS", last.get("status"), last.get("message"), last.get("error"))
        if last.get("status") in {"success", "error"}:
            break
        time.sleep(15)
    elapsed = round(time.perf_counter() - t0, 2)
    print("ELAPSED_S", elapsed)
    print("FINAL_STATUS", last.get("status"))
    print("SUMMARY", last.get("summary"))
    print("HYBRID", last.get("hybrid"))
    print("WARNINGS", last.get("warnings"))
    if last.get("status") != "success":
        return 1
    staging = config.WEB_RUNS_ROOT / run_id
    excel = staging / config.VB1_EXCEL_REL
    print("EXCEL", excel.exists(), excel.stat().st_size if excel.exists() else 0)
    obs_path = staging / config.W6_OBSERVABILITY_REL
    res_path = staging / config.W6_RESOLUTION_REL
    print("W6_OBS", obs_path.exists())
    print("W6_RES", res_path.exists())
    if obs_path.is_file():
        obs = json.loads(obs_path.read_text(encoding="utf-8"))
        print(
            "W6",
            {
                "classification": obs.get("classification"),
                "applied": obs.get("production_authority_applied"),
                "calls": obs.get("claude_invocation_count"),
                "success": obs.get("successful_invocation_count"),
                "failed": obs.get("failed_invocation_count"),
                "latency_s": obs.get("hybrid_latency_s"),
                "model": obs.get("model"),
                "fallback_used": obs.get("fallback_used"),
            },
        )
    dl = client.get(f"/api/download/{run_id}")
    print("DOWNLOAD", dl.status_code, len(dl.data or b""))
    return 0 if dl.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
