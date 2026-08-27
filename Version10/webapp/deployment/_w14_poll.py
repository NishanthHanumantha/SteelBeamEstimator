#!/usr/bin/env python3
"""Poll a W.14 production run until complete. No secrets."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

BASE = os.environ.get("STEEL_W14_BASE", "http://13.127.104.99").rstrip("/")
RUN = sys.argv[1] if len(sys.argv) > 1 else ""
POLL_S = float(os.environ.get("STEEL_W14_POLL_S", "20"))
TIMEOUT_S = float(os.environ.get("STEEL_W14_TIMEOUT_S", "15000"))


def main() -> int:
    if not RUN:
        print("USAGE poll_w14.py <run_id>")
        return 2
    print("POLL_RUN", RUN)
    deadline = time.time() + TIMEOUT_S
    last = {}
    while time.time() < deadline:
        with urllib.request.urlopen(f"{BASE}/api/status/{RUN}", timeout=30) as resp:
            last = json.loads(resp.read().decode("utf-8"))
        print(
            "POLL",
            last.get("status"),
            last.get("result_lifecycle"),
            last.get("message"),
            last.get("elapsed_s"),
            last.get("hybrid"),
        )
        if last.get("status") in {"success", "error"}:
            print("FINAL_STATUS", json.dumps(last, default=str)[:4000])
            return 0 if last.get("status") == "success" else 1
        time.sleep(POLL_S)
    print("TIMEOUT", json.dumps(last, default=str)[:2000])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
