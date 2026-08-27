#!/usr/bin/env python3
"""Poll W.15 production run. Observational only. No secrets."""
from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = "http://13.127.104.99"
RUN = sys.argv[1] if len(sys.argv) > 1 else "20260827_110320_4e330c37"
POLL_S = 20.0
TIMEOUT_S = 20000.0


def main() -> int:
    print("POLL_RUN", RUN)
    deadline = time.time() + TIMEOUT_S
    last = {}
    while time.time() < deadline:
        with urllib.request.urlopen(f"{BASE}/api/status/{RUN}", timeout=30) as resp:
            last = json.loads(resp.read().decode("utf-8"))
        progress = last.get("progress") or {}
        print(
            "POLL",
            last.get("status"),
            last.get("result_lifecycle"),
            last.get("elapsed_s"),
            last.get("message"),
            "progress=",
            json.dumps(progress, default=str)[:800],
            "hybrid=",
            json.dumps(last.get("hybrid"), default=str)[:400] if last.get("hybrid") else None,
        )
        if last.get("status") in {"success", "error"}:
            print("FINAL_STATUS", json.dumps({
                k: last.get(k) for k in (
                    "status", "run_id", "result_lifecycle", "download_ready",
                    "excel_generated", "excel_exists", "workbook_name",
                    "duration_s", "summary", "hybrid", "error", "filenames",
                )
            }, default=str)[:6000])
            return 0 if last.get("status") == "success" else 1
        time.sleep(POLL_S)
    print("TIMEOUT", json.dumps(last, default=str)[:2000])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
