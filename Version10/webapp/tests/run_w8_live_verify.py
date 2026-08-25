"""W.8 local live verification. No secret print. No Lightsail."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from PhaseW5_production_hybrid_shadow.paths import ENGINE_ROOT, ensure_src_on_path

ensure_src_on_path()

from PhaseP2610A_beam_region_crop_audit.title_localizer import collect_beam_titles
from PhaseW5_production_hybrid_shadow.settings import load_settings
from PhaseW6_hybrid_production_authority.config import COVERAGE_FILENAME, OUTPUT_DIRNAME, R13_REL
from PhaseW6_hybrid_production_authority.orchestrator import run_production_hybrid
from PhaseW6_hybrid_production_authority.unit_tests import _r13_model
from PhaseW8_production_vision_evidence.package import prepare_production_evidence

REPO = ENGINE_ROOT.parent
FIRST_DXF = (
    REPO
    / "Test_Input"
    / "1st Set Drawings-Galera_OHT&STP"
    / "reinforcement"
    / "SampleBeam_Reinforcement&StirrupsDetials_DXF.dxf"
)
OUT = ENGINE_ROOT / "webapp" / "deployment" / "_w8_live_verify.json"


def _prime() -> str:
    if (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        return "PRESENT"
    env_path = REPO / ".env"
    if env_path.is_file():
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    return "PRESENT" if (os.environ.get("ANTHROPIC_API_KEY") or "").strip() else "ABSENT"


def _beam_ids(dxf: Path) -> list[str]:
    import ezdxf

    doc = ezdxf.readfile(str(dxf))
    titles = collect_beam_titles(doc.modelspace())
    ids = sorted({str(t.get("beam_id")) for t in titles if t.get("beam_id")})
    return ids


def main() -> int:
    os.environ["HYBRID_MODE"] = "production"
    os.environ["HYBRID_MAX_LIVE_CALLS"] = os.environ.get("HYBRID_MAX_LIVE_CALLS") or "1"
    key = _prime()
    payload: dict = {
        "api_key_configured": key == "PRESENT",
        "max_live_calls": os.environ.get("HYBRID_MAX_LIVE_CALLS"),
        "dxf_present": FIRST_DXF.is_file(),
    }
    if not FIRST_DXF.is_file():
        payload["ok"] = False
        payload["reason"] = "FIRST_SET_DXF_MISSING"
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("FAIL FIRST_SET_DXF_MISSING")
        return 2
    beam_ids = _beam_ids(FIRST_DXF)
    payload["discovered_beam_ids"] = beam_ids
    payload["discovered_count"] = len(beam_ids)
    root = Path(tempfile.mkdtemp(prefix="w8_live_"))
    try:
        reinf = root / "reinforcement"
        reinf.mkdir()
        shutil.copy2(FIRST_DXF, reinf / FIRST_DXF.name)
        evidence = prepare_production_evidence(root, beam_ids=beam_ids)
        payload["evidence"] = {
            k: evidence.get(k)
            for k in (
                "p2610_primary",
                "w6_compatibility",
                "t1_compatibility",
                "unavailable",
                "evidence_packages_generated",
                "context_selected",
                "detail_selected",
                "distinct_context_detail",
                "coverage_identity",
            )
        }
        payload["evidence_by_id"] = evidence.get("by_id")
        r13 = root / R13_REL
        r13.parent.mkdir(parents=True, exist_ok=True)
        models = []
        for bid in beam_ids:
            rec = dict(_r13_model())
            rec["beam_id"] = bid
            rec["top_main_bars"] = [dict(rec["top_main_bars"][0], bar_id=f"R13-{bid}-TOP")]
            rec["stirrups"] = [dict(rec["stirrups"][0], bar_id=f"R13-{bid}-STIR")]
            models.append(rec)
        r13.write_text(json.dumps({"models": models}), encoding="utf-8")
        if key != "PRESENT":
            payload["ok"] = True
            payload["live"] = {"skipped": True, "reason": "API_KEY_ABSENT"}
            print("EVIDENCE_OK LIVE_SKIPPED_NO_KEY")
            return 0
        result = run_production_hybrid(
            run_id="w8-live-bounded",
            staging=root,
            settings=load_settings(),
            persist=True,
        )
        payload["hybrid"] = {
            "classification": result.get("classification"),
            "applied": result.get("production_authority_applied"),
            "request_count": result.get("request_count"),
            "successful": result.get("successful_invocation_count"),
            "failed": result.get("failed_invocation_count"),
            "coverage": result.get("coverage"),
        }
        cov_path = root / "data" / "output" / OUTPUT_DIRNAME / COVERAGE_FILENAME
        if cov_path.is_file():
            cov = json.loads(cov_path.read_text(encoding="utf-8"))
            payload["coverage"] = {
                k: cov.get(k)
                for k in (
                    "hybrid_eligible",
                    "p2610_primary_evidence",
                    "generated_fallback_crop",
                    "native_t1_crop",
                    "visual_context_unavailable",
                    "claude_invocations",
                    "claude_success",
                    "claude_failure",
                    "unexplained",
                    "identity_ok",
                )
            }
        blob = json.dumps(payload).lower()
        payload["secret_scan_clean"] = "sk-ant-" not in blob
        payload["ok"] = bool(
            payload.get("evidence", {}).get("evidence_packages_generated")
            and result.get("request_count", 0) >= 1
            and payload["secret_scan_clean"]
        )
        print(
            "W8_LIVE",
            payload["ok"],
            "beams",
            len(beam_ids),
            "primary",
            payload["evidence"].get("p2610_primary"),
            "calls",
            result.get("request_count"),
            "class",
            result.get("classification"),
        )
        return 0 if payload["ok"] else 1
    finally:
        OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print("OUT", str(OUT))


if __name__ == "__main__":
    raise SystemExit(main())
