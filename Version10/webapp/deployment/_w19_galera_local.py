"""W.19 local Galera GF production-equivalent pipeline (HYBRID_MODE=off).

Copies the actual Galera DXFs into an isolated web_runs staging dir and
invokes invoke_version10_pipeline. Does not reconstruct 0.25L extents.
"""
from __future__ import annotations

import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
WEBAPP = ROOT / "Version10" / "webapp"
sys.path.insert(0, str(WEBAPP))

os.environ["HYBRID_MODE"] = "off"
os.environ["STEEL_WEB_PIPELINE_MODE"] = "live"

import config  # noqa: E402
from services.version10_adapter import invoke_version10_pipeline  # noqa: E402

GN = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w16_gn\galera_gn.dxf")
FR = ROOT / "Test_Input" / "2nd Set Drawings-Galera_GF" / "framing" / "Galera_GF_FramingPlan.dxf"
RE = (
    ROOT / "Test_Input" / "2nd Set Drawings-Galera_GF" / "reinforcement"
    / "Galera_GF_BeamReinforcementDetails_SpreadOut.dxf"
)


def main() -> int:
    for p, label in ((GN, "GN"), (FR, "FR"), (RE, "RE")):
        if not p.is_file():
            print(f"MISSING {label} {p}")
            return 2
        print(f"INPUT {label} {p.name} {p.stat().st_size}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    staging = config.WEB_RUNS_ROOT / run_id
    (staging / "general_notes").mkdir(parents=True, exist_ok=True)
    (staging / "framing").mkdir(parents=True, exist_ok=True)
    (staging / "reinforcement").mkdir(parents=True, exist_ok=True)
    (staging / "data" / "output").mkdir(parents=True, exist_ok=True)
    (staging / "logs").mkdir(parents=True, exist_ok=True)

    gn_dest = staging / "general_notes" / "SE-100-R0-SH-01SH-02GENERAL_NOTES.dxf"
    fr_dest = staging / "framing" / "Galera_GF_FramingPlan.dxf"
    re_dest = staging / "reinforcement" / "Galera_GF_BeamReinforcementDetails_SpreadOut.dxf"
    shutil.copy2(GN, gn_dest)
    shutil.copy2(FR, fr_dest)
    shutil.copy2(RE, re_dest)
    print("RUN_ID", run_id)
    print("STAGING", staging)
    print("HYBRID_MODE", os.environ.get("HYBRID_MODE"))

    def on_stage(stage_id: str, label: str) -> None:
        print(f"STAGE {stage_id} {label}", flush=True)

    result = invoke_version10_pipeline(
        run_id=run_id,
        staging=staging,
        gn_path=gn_dest,
        on_stage=on_stage,
    )
    print("SUCCESS", result.success)
    print("DURATION_S", result.duration_s)
    print("STAGES", result.stages_run)
    print("EXCEL", result.output_path)
    print("SUMMARY", result.summary)
    print("WARNINGS", result.warnings)
    print("ERROR", result.error)
    (staging / "w19_pipeline_result.json").write_text(
        __import__("json").dumps({
            "run_id": run_id,
            "success": result.success,
            "duration_s": result.duration_s,
            "stages_run": result.stages_run,
            "output_path": result.output_path,
            "summary": result.summary,
            "warnings": result.warnings,
            "error": result.error,
            "hybrid_mode": os.environ.get("HYBRID_MODE"),
        }, indent=2),
        encoding="utf-8",
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
