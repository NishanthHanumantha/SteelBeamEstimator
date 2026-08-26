#!/bin/bash
set -euo pipefail
ROOT=/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_065256_4ba41266/data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence
echo TWO_IMAGE
python3 - <<'PY'
import hashlib, json
from pathlib import Path
root = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_065256_4ba41266/data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence")
rows = []
for man in sorted(root.glob("*/evidence_manifest.json")):
    d = json.loads(man.read_text(encoding="utf-8"))
    ctx = man.parent / "context" / "selected.png"
    det = man.parent / "detail" / "selected.png"
    def sha(p):
        if not p.is_file():
            return None
        h = hashlib.sha256()
        h.update(p.read_bytes())
        return h.hexdigest()[:12]
    cs, ds = sha(ctx), sha(det)
    rows.append({
        "beam_id": d.get("beam_id") or man.parent.name,
        "evidence_class": d.get("evidence_class"),
        "visual_source": d.get("visual_source"),
        "fallback_status": d.get("fallback_status"),
        "fallback_reason": d.get("fallback_reason"),
        "n_images": 2 if ctx.is_file() and det.is_file() else 0,
        "same_sha": bool(cs and ds and cs == ds),
        "ctx_sha": cs,
        "det_sha": ds,
        "contract": d.get("claude_image_contract"),
        "ctx_phase": (d.get("selected_context_evidence") or {}).get("source_phase"),
        "det_phase": (d.get("selected_detail_evidence") or {}).get("source_phase"),
    })
primary = [r for r in rows if r["evidence_class"] == "PRIMARY"]
compat = [r for r in rows if r["evidence_class"] in ("COMPATIBILITY", "FALLBACK")]
print("TOTAL", len(rows))
print("PRIMARY", len(primary), "distinct", sum(1 for r in primary if not r["same_sha"]), "same", sum(1 for r in primary if r["same_sha"]))
print("COMPAT_FALLBACK", len(compat), "distinct", sum(1 for r in compat if not r["same_sha"]), "same", sum(1 for r in compat if r["same_sha"]))
print(json.dumps(rows, indent=2))
PY
