"""Sample local Python RSS during a web estimation (stdlib only)."""
from __future__ import annotations

import csv
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def _ps_sample() -> list[tuple[str, str, str]]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-Process python*,gunicorn* -ErrorAction SilentlyContinue | "
            "Select-Object Id,ProcessName,@{N='WS_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}},CPU | "
            "ConvertTo-Csv -NoTypeInformation"
        ),
    ]
    raw = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")
    rows = list(csv.DictReader(raw.splitlines()))
    out = []
    for r in rows:
        out.append((r.get("Id", ""), r.get("ProcessName", ""), r.get("WS_MB", ""), r.get("CPU", "")))
    return out


def main() -> None:
    dest = Path(__file__).resolve().parent / "w21_resource_samples.csv"
    interval = 5.0
    with dest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["utc", "pid", "name", "ws_mb", "cpu_s"])
        fh.flush()
        print(f"sampling -> {dest}", flush=True)
        while True:
            ts = datetime.now(timezone.utc).isoformat()
            try:
                rows = _ps_sample()
            except Exception as exc:
                w.writerow([ts, "", "ERROR", str(exc), ""])
                fh.flush()
                time.sleep(interval)
                continue
            total = 0.0
            for pid, name, ws, cpu in rows:
                w.writerow([ts, pid, name, ws, cpu])
                try:
                    total += float(ws)
                except Exception:
                    pass
            w.writerow([ts, "", "TOTAL_PYTHON_WS_MB", f"{total:.1f}", ""])
            fh.flush()
            time.sleep(interval)


if __name__ == "__main__":
    main()
