"""Package-level import check for Version11 production path."""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

V11 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V11 / "src"))
sys.path.insert(0, str(V11 / "webapp"))

MODULES = [
    "config",
    "app",
    "services.version10_adapter",
    "PhaseW6_hybrid_production_authority.orchestrator",
    "PhaseW6_hybrid_production_authority.handoff",
    "PhaseW5_production_hybrid_shadow.adapter",
    "PhaseW5_production_hybrid_shadow.live_invoke",
    "PhaseW8_production_vision_evidence.generator",
    "PhaseP2610C5_stratified_vision_semantic_benchmark.claude_call",
    "PhaseP2610C5_stratified_vision_semantic_benchmark.vision_prompt",
    "PhaseP2610C5_stratified_vision_semantic_benchmark.vision_contract",
    "PhaseP253_claude_vision_interpretation_pilot.claude_vision_client",
    "PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.live_caller",
    "PhaseP2610D2_shadow_hybrid_semantic_resolver.resolver",
    "PhaseVB.1_production_output_completion.phase_vb1_orchestrator",
]

# VB.1 package folder contains dots; load by file path.
SPECIAL = {
    "PhaseVB.1_production_output_completion.phase_vb1_orchestrator": V11
    / "src"
    / "PhaseVB.1_production_output_completion"
    / "phase_vb1_orchestrator.py",
}


def main() -> int:
    rows = []
    import importlib
    import importlib.util

    for name in MODULES:
        row = {"module": name, "ok": False, "error": None}
        try:
            if name in SPECIAL:
                spec = importlib.util.spec_from_file_location(name.replace(".", "_"), SPECIAL[name])
                mod = importlib.util.module_from_spec(spec)
                # For run_context, relative imports may fail; still try
                spec.loader.exec_module(mod)
            else:
                importlib.import_module(name)
            row["ok"] = True
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["trace"] = traceback.format_exc()[-600:]
        rows.append(row)
        print(("OK  " if row["ok"] else "FAIL"), name, row.get("error") or "")

    out = {
        "ok": all(r["ok"] for r in rows),
        "rows": rows,
    }
    dest = V11 / "docs" / "V11_0_IMPORT_CHECK.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
