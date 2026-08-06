#!/usr/bin/env python3
"""
run_phase_track1_visual_chain.py
Post-VB1 Track1 visual chain: T16 → T17 → T18 → T181 → T182 → T183 → T1831
MODEL_VERSION: 9.6.0

Usage:
  python Run_PY/run_phase_track1_visual_chain.py [run_root]
"""
from __future__ import annotations

import sys
from pathlib import Path

_V9 = Path(__file__).resolve().parents[1]
_SRC = _V9 / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    from PhaseQA2B0_pipeline_integration.track1_chain_runner import (
        run_track1_visual_chain,
    )

    argv = [a for a in sys.argv[1:] if not str(a).startswith("--")]
    if argv:
        run_root = Path(argv[0])
    else:
        from config.run_context import resolve_run_context

        ctx = resolve_run_context(engine_root=_V9)
        run_root = Path(ctx.run_root)

    force = "--force" in sys.argv
    print(f"[T16CHAIN] engine={_V9}")
    print(f"[T16CHAIN] run_root={run_root}")
    result = run_track1_visual_chain(
        _V9, run_root, force=force, ensure_envelopes=True
    )
    print(f"[T16CHAIN] success={result.get('success')}")
    for st in result.get("stages") or []:
        flag = "SKIP" if st.get("skipped") else ("OK" if st.get("success") else "FAIL")
        print(f"  {st.get('stage')}: {flag}" + (f" ({st.get('error')})" if st.get("error") else ""))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
