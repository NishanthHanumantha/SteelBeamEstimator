"""Ensure Version5 root is on sys.path and the working directory for runners."""

import os
import sys
from pathlib import Path

VERSION5_ROOT = Path(__file__).resolve().parents[1]


def setup() -> Path:
    os.chdir(VERSION5_ROOT)
    root_str = str(VERSION5_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return VERSION5_ROOT


setup()
