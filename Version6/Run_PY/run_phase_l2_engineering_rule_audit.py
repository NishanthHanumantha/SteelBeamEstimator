"""Runner for Phase L.2 — Engineering Rule Audit Engine."""

from __future__ import annotations

import sys
from pathlib import Path

import _bootstrap  # noqa: F401

PHASE_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "PhaseL.2 - engineering_rule_audit"
)
if str(PHASE_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE_DIR))

from engineering_rule_audit_engine import EngineeringRuleAuditEngine  # noqa: E402

if __name__ == "__main__":
    engine = EngineeringRuleAuditEngine(Path.cwd())
    result = engine.run()
    val_status = (result.get("validation") or {}).get("status", "FAIL")
    sys.exit(0 if val_status == "PASS" else 1)
