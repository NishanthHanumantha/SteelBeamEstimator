"""
phase_vtest33_orchestrator.py — Phase V.TEST.3.3 orchestrator.
MODEL_VERSION: 8.1.4
"""
from __future__ import annotations

import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from artifact_loader import PropagationArtifactLoader  # noqa: E402
from propagation_export import PropagationExport  # noqa: E402
from propagation_reporter import PropagationReporter  # noqa: E402
from propagation_trace_engine import PropagationTraceEngine  # noqa: E402
from propagation_validator import PropagationValidator  # noqa: E402

MODEL_VERSION = "8.1.4"
PHASE_ID = "V.TEST.3.3"

_REPO = pathlib.Path(__file__).resolve().parents[3]
_V7 = _REPO / "Version7"


class PhaseVTEST33Orchestrator:

    def run(self):
        print("=" * 72)
        print("Phase V.TEST.3.3 — Reinforcement Propagation Trace & Root Cause")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("READ-ONLY — No production code modified")
        print("=" * 72)

        print("\n[1/4] Loading pipeline artefacts ...")
        loader = PropagationArtifactLoader(_V7)
        loader.load_all()
        print(f"  Annotations: {sum(len(v) for v in loader.annotations_by_beam.values())}")
        print(f"  Facts:       {len(loader.facts_by_id)}")
        print(f"  Beams:       {len(loader.all_beam_ids)}")

        print("\n[2/4] Building propagation trace ...")
        result = PropagationTraceEngine(loader).run()

        print("\n[3/4] Validating ...")
        result.validation = PropagationValidator().validate(result)
        v = result.validation
        print(f"  Validation: {v['passed']}/{v['total']} rules passed")

        print("\n[4/4] Exporting ...")
        md = PropagationReporter().generate(result)
        paths = PropagationExport().export_all(result, md)
        for name in paths:
            print(f"  {name}")

        s = result.statistics
        print("\n" + "=" * 72)
        print(f"Annotations: {s.get('annotations_discovered')} on {s.get('beams_with_annotations')} beams")
        print(f"Engineering bars: {s.get('engineering_bars_created')} | Steel beams: {s.get('beams_with_steel')}")
        print(f"Recommendation: {result.recommendation}")
        print("=" * 72)
        return result
