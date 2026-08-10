"""
Pytest-compatible wrappers for P2.2 unit tests.
MODEL_VERSION: 10.5.4

Run:
  python -m PhaseP22_leader_chain_evidence.unit_tests
  pytest src/PhaseP22_leader_chain_evidence/test_evaluator.py -q
"""
from __future__ import annotations

from .unit_tests import run_unit_tests


def test_all_leader_chain_evidence_unit_tests():
    result = run_unit_tests()
    assert result["overall_pass"], result.get("failed_ids")
