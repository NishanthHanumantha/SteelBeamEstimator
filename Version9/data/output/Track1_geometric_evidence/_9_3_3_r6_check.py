"""
9.3.3 R6 flag-off check — confirms enable_geometry_stirrup_evidence=false
still soft-exits (no detection output produced), without touching the
on-disk config/geometric_stirrup_evidence.yaml. Purely in-process: monkey-
patches PhaseT1Orchestrator.cfg after construction, then calls run().
Read-only otherwise; writes to a throwaway temp output dir, not any real
run_root's output.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # Version9
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import PhaseT1_geometric_stirrup_evidence.phase_t1_orchestrator as t1_mod  # noqa: E402
from PhaseT1_geometric_stirrup_evidence.phase_t1_orchestrator import (  # noqa: E402
    PhaseT1Orchestrator,
)

RUN_ROOT = ROOT / "data" / "web_runs" / "qa2_First_Set_Drawings_20260803_132045"


def main() -> None:
    tmp_out = Path(tempfile.mkdtemp(prefix="t1_r6_check_"))
    orig_is_enabled = t1_mod.is_enabled
    t1_mod.is_enabled = lambda engine_root: False  # simulate enable_geometry_stirrup_evidence: false
    try:
        orch = PhaseT1Orchestrator(
            engine_root=ROOT, run_root=RUN_ROOT, output_root=tmp_out
        )
        result = orch.run(skip_renderer_validation=True)
        print(json.dumps(result, indent=2))
        ev = json.loads(
            (tmp_out / "PhaseT1_geometric_stirrup_evidence" / "stirrup_geometry_evidence.json")
            .read_text(encoding="utf-8")
        )
        print("\nsoft_exit evidence by_beam count:", len(ev.get("by_beam") or {}))
        print("enabled:", ev.get("enabled"))
    finally:
        t1_mod.is_enabled = orig_is_enabled
        shutil.rmtree(tmp_out, ignore_errors=True)


if __name__ == "__main__":
    main()
