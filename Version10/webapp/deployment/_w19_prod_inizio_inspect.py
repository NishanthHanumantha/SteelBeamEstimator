#!/usr/bin/env python3
import json
from pathlib import Path

root = Path(
    "/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/"
    "20260829_073647_c0df30a7/data/output"
)
s = json.loads((root / "PhaseR.2A_engineering_context" / "engineering_context_summary.json").read_text())
keep = {
    k: s.get(k)
    for k in s
    if any(x in k.lower() for x in ("cover", "steel", "dev", "grade", "source", "factor"))
}
print("R2A", json.dumps(keep, default=str))
srp = root / "PhaseR1.3_pipeline_integration" / "spacer_rule_report.json"
if srp.exists():
    sr = json.loads(srp.read_text())
    print(
        "SPACER",
        sr.get("model_version"),
        "cover",
        sr.get("cover_mm_used"),
        "fallback_rows",
        sr.get("extent_fallback_rows"),
        "emitted",
        sr.get("rows_emitted"),
    )
