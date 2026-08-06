#!/usr/bin/env python3
"""Alias entrypoint for Phase QA.3.0 (see run_phase_qa30_unseen_benchmark.py)."""
from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).with_name("run_phase_qa30_unseen_benchmark.py")
    runpy.run_path(str(target), run_name="__main__")
