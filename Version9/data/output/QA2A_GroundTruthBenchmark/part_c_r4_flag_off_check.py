"""R4 — flag-off equivalence for enable_dimension_text_scan."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

V9 = Path(r"C:\Users\nishanth.h\SteelBeamEstimator\Version9")
YAML = V9 / "config" / "generalized_reinforcement_discovery.yaml"
OUT = Path(__file__).resolve().parent


def set_flag(enabled: bool) -> None:
    text = YAML.read_text(encoding="utf-8")
    text = re.sub(
        r"enable_dimension_text_scan:\s*(true|false)",
        f"enable_dimension_text_scan: {'true' if enabled else 'false'}",
        text,
    )
    YAML.write_text(text, encoding="utf-8")


def sig(doc):
    rows = []
    for bid, anns in (doc.get("by_beam") or {}).items():
        for a in anns:
            rows.append(
                (
                    bid,
                    round(float(a.get("x") or 0), 1),
                    round(float(a.get("y") or 0), 1),
                    (a.get("clean_text") or "").strip(),
                    a.get("role"),
                    a.get("diameter_mm"),
                    a.get("quantity"),
                    a.get("spacing_mm"),
                )
            )
    return sorted(rows)


def stir_count(doc) -> int:
    n = 0
    for anns in (doc.get("by_beam") or {}).values():
        for a in anns:
            if a.get("role") == "STIRRUP":
                n += 1
    return n


def main() -> int:
    runs = {
        "First": V9 / "data/web_runs/qa2_First_Set_Drawings_20260731_154657",
        "Second": V9 / "data/web_runs/qa2_Second_Set_Drawings_20260731_154739",
        "Third": V9 / "data/web_runs/qa2_Third_Set_Drawings_20260731_154835",
    }
    baselines = {
        "Second": OUT
        / "part_c_baselines/qa2_Second_Set_Drawings_20260731_154739_prepatch_reinforcement_annotations.json",
        "Third": OUT
        / "part_c_baselines/qa2_Third_Set_Drawings_20260731_154835_prepatch_reinforcement_annotations.json",
    }

    set_flag(False)
    print("Flag FALSE")
    results = {}
    env = os.environ.copy()
    env["STEEL_ENGINE_ROOT"] = str(V9)

    for name, run in runs.items():
        t0 = time.perf_counter()
        p = subprocess.run(
            [
                sys.executable,
                str(V9 / "Run_PY/run_phase_r1_generalized_reinforcement_discovery.py"),
                str(run),
            ],
            cwd=str(V9),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        elapsed = round(time.perf_counter() - t0, 2)
        ann_path = (
            run
            / "data/output/PhaseR.1_generalized_reinforcement_discovery"
            / "reinforcement_annotations.json"
        )
        cur = json.loads(ann_path.read_text(encoding="utf-8"))
        if name == "First":
            ok = cur.get("total_annotations") == 65 and stir_count(cur) == 0
            results[name] = {
                "elapsed_s": elapsed,
                "total": cur.get("total_annotations"),
                "stirrup": stir_count(cur),
                "identical_to_prepatch_day1_counts": ok,
                "exit": p.returncode,
            }
        else:
            base = json.loads(baselines[name].read_text(encoding="utf-8"))
            identical = sig(cur) == sig(base)
            results[name] = {
                "elapsed_s": elapsed,
                "total": cur.get("total_annotations"),
                "stirrup": stir_count(cur),
                "baseline_total": base.get("total_annotations"),
                "identical_signature": identical,
                "exit": p.returncode,
            }
        print(name, results[name])

    set_flag(True)
    print("Flag restored TRUE")
    out = OUT / "part_c_r4_flag_off.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Wrote", out)
    ok_all = (
        results["First"].get("identical_to_prepatch_day1_counts")
        and results["Second"].get("identical_signature")
        and results["Third"].get("identical_signature")
    )
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
