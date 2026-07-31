"""One-shot E2 matrix diff script — M.2 follow-up evidence."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROLES = [
    "TOP_MAIN",
    "TOP_EXTRA",
    "BOTTOM_MAIN",
    "BOTTOM_EXTRA",
    "STIRRUP",
    "STIRRUP_HOOK",
    "SIDE_FACE_REINFORCEMENT",
    "SPACER_BAR",
]
STATUSES = [
    "MATCH",
    "PARTIAL_MATCH",
    "MISSING",
    "EXTRA",
    "ACCEPTABLE_EXTRA",
    "WRONG_DIAMETER",
    "WRONG_QUANTITY",
    "WRONG_ROLE",
]
SETS = [
    ("First Set Drawings", "First_Set_Drawings"),
    ("Second Set Drawings", "Second_Set_Drawings"),
    ("Third Set Drawings", "Third_Set_Drawings"),
]


def matrix_from_rows(rows):
    m = defaultdict(lambda: defaultdict(int))
    for r in rows:
        role = (r.get("bar_role") or r.get("model_role") or "UNKNOWN").upper()
        st = r.get("status") or "UNKNOWN"
        m[role][st] += 1
    return m


def main() -> None:
    v8 = Path(__file__).resolve().parents[3].parent / "Version8" / "data" / "output" / "QA2A_GroundTruthBenchmark"
    # script lives in Version9/.../QA2A... so parents[3] is Version9
    root = Path(__file__).resolve().parent
    v9 = root
    v8 = Path(r"C:\Users\nishanth.h\SteelBeamEstimator\Version8\data\output\QA2A_GroundTruthBenchmark")

    deltas = []
    out_lines = []
    for name, safe in SETS:
        before_rows = json.loads((v8 / safe / "bar_matching.json").read_text(encoding="utf-8")).get("rows") or []
        after_rows = json.loads((v9 / safe / "bar_matching.json").read_text(encoding="utf-8")).get("rows") or []
        before = matrix_from_rows(before_rows)
        after = matrix_from_rows(after_rows)
        out_lines.append("=" * 78)
        out_lines.append(name)
        out_lines.append(
            f"{'Role':28s} {'Status':18s} {'Before':>7s} {'After':>7s} {'Delta':>7s}"
        )
        for role in ROLES:
            for st in STATUSES:
                b = before.get(role, {}).get(st, 0)
                a = after.get(role, {}).get(st, 0)
                if b == 0 and a == 0:
                    continue
                d = a - b
                flag = ""
                if role != "SPACER_BAR" and d != 0:
                    flag = " *** SIDE EFFECT ***"
                    deltas.append(
                        {"set": name, "role": role, "status": st, "before": b, "after": a, "delta": d}
                    )
                out_lines.append(f"{role:28s} {st:18s} {b:7d} {a:7d} {d:+7d}{flag}")

    out_lines.append("=" * 78)
    out_lines.append(f"NON-SPACER DELTAS: {len(deltas)}")
    for x in deltas:
        out_lines.append(str(x))

    text = "\n".join(out_lines)
    (root / "m2_followup_role_status_diff.txt").write_text(text, encoding="utf-8")
    (root / "m2_followup_non_spacer_deltas.json").write_text(
        json.dumps(deltas, indent=2), encoding="utf-8"
    )
    print(text)


if __name__ == "__main__":
    main()
