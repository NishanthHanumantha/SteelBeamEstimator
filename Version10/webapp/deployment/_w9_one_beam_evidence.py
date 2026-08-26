"""One-beam W.9 evidence generation check on production. No Claude. No secrets."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ENGINE = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10")
sys.path.insert(0, str(ENGINE / "src"))

from PhaseW8_production_vision_evidence.generator import DxfSession, build_beam_evidence  # noqa: E402

DXF = Path(
    "/home/ubuntu/w3_smoke/smoke/1st Set Drawings-Galera_OHT&STP/reinforcement/"
    "SampleBeam_Reinforcement&StirrupsDetials_DXF.dxf"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if not DXF.is_file():
        print("MISSING_DXF", DXF)
        return 2
    os.environ.setdefault("HYBRID_MODE", "production")
    staging = Path(tempfile.mkdtemp(prefix="w9_evidence_"))
    (staging / "data/output").mkdir(parents=True)
    reinf = staging / "reinforcement"
    reinf.mkdir(parents=True, exist_ok=True)
    dest = reinf / DXF.name
    if not dest.is_file():
        dest.write_bytes(DXF.read_bytes())
    session = DxfSession(staging)
    row = build_beam_evidence(staging=staging, beam_id="B1", session=session)
    ctx = Path(row.get("context_path") or "")
    det = Path(row.get("detail_path") or "")
    same = ctx.is_file() and det.is_file() and sha(ctx) == sha(det)
    summary = {
        "ok": bool(row.get("ok")),
        "available": bool(row.get("available")),
        "evidence_class": row.get("evidence_class"),
        "visual_source": row.get("visual_source"),
        "fallback_status": row.get("fallback_status"),
        "fallback_reason": row.get("fallback_reason"),
        "context_exists": ctx.is_file(),
        "detail_exists": det.is_file(),
        "same_image": same,
        "n_images": 2 if ctx.is_file() and det.is_file() else int(ctx.is_file()) + int(det.is_file()),
        "staging": str(staging),
    }
    print(json.dumps(summary, indent=2))
    man = staging / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence/B1/evidence_manifest.json"
    if not man.is_file():
        # package layout uses EVIDENCE_REL
        from PhaseW8_production_vision_evidence.generator import manifest_path

        man = manifest_path(staging, "B1")
    if man.is_file():
        payload = json.loads(man.read_text(encoding="utf-8"))
        print("MANIFEST_CLASS", payload.get("evidence_class"))
        print("MANIFEST_SOURCE", payload.get("visual_source"))
        print("CONTRACT", payload.get("claude_image_contract"))
    if not row.get("ok") or not ctx.is_file() or not det.is_file():
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
