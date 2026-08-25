"""Bounded live Claude smoke for TEST-W6-03. Does not print secrets."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parents[1]
V10 = WEBAPP_ROOT.parent
REPO = V10.parent
SRC = V10 / "src"
for p in (str(V10), str(SRC), str(WEBAPP_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


def _prime() -> bool:
    if (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        return True
    env_path = REPO / ".env"
    if env_path.is_file():
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    return bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())


def main() -> int:
    present = _prime()
    print("API_KEY_CONFIGURED", "YES" if present else "NO")
    if not present:
        return 2
    crop = next(
        V10.glob("data/output/PhaseP252_vision_candidate_set/candidates/**/local_crop.png"),
        None,
    )
    if crop is None or not crop.is_file():
        print("NO_REAL_CROP")
        return 2
    r13_src = V10 / "data/web_runs/20260824_162034_01481ff0/data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json"
    data = json.loads(r13_src.read_text(encoding="utf-8"))
    models = data.get("models") if isinstance(data, dict) else data
    model = next(m for m in models if isinstance(m, dict) and m.get("beam_id") == "B1")
    tmp = Path(tempfile.mkdtemp(prefix="w6_live_smoke_"))
    r13_rel = Path("data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json")
    crop_rel = Path("data/output/PhaseT1_geometric_stirrup_evidence/opencv_renders/B1_crop.png")
    (tmp / r13_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp / crop_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp / r13_rel).write_text(json.dumps({"models": [model]}, indent=2), encoding="utf-8")
    shutil.copy2(crop, tmp / crop_rel)
    os.environ["HYBRID_MODE"] = "production"
    os.environ["HYBRID_MAX_LIVE_CALLS"] = "1"
    os.environ.pop("HYBRID_MAX_WALL_S", None)
    from PhaseW6_hybrid_production_authority.orchestrator import run_production_hybrid

    result = run_production_hybrid(run_id="w6-live-smoke", staging=tmp, persist=True)
    safe = {
        "classification": result.get("classification"),
        "applied": result.get("production_authority_applied"),
        "request_count": result.get("request_count"),
        "successful_invocation_count": result.get("successful_invocation_count"),
        "failed_invocation_count": result.get("failed_invocation_count"),
        "hybrid_latency_s": result.get("hybrid_latency_s"),
        "model": result.get("model"),
        "fallback_used": result.get("fallback_used"),
        "reason": result.get("reason"),
        "staging": str(tmp),
    }
    print("LIVE_SMOKE", json.dumps(safe, indent=2))
    blob = json.dumps(result, default=str).lower()
    if "sk-ant-" in blob:
        print("SECRET_LEAK")
        return 1
    if int(result.get("request_count") or 0) < 1:
        print("NO_CLAUDE_CALL")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
