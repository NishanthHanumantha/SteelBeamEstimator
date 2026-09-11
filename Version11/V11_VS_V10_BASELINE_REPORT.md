# V11 vs V10 Baseline Report

**Date:** 2026-09-11  
**Question:** After a zero-change fork, is Version11 equivalent to frozen Version10 W.19.1?

---

## Verdict

| Question | Result |
|---|---|
| Production logic equivalent? | **YES** |
| TRUE_PIPELINE_DIFFERENCE? | **NONE** |
| UNRESOLVED_DIFFERENCE in copied logic? | **NONE** |
| Live Hybrid drawing Excel byte-compare executed? | **NO** (see below) |

Equivalence is established by SHA256 identity of the copied production boundary plus execution of the 14-stage stub pipeline and production unit tests. It is **not** claimed from “both pipelines happened to finish.”

---

## Comparison method

### 1. Source identity (primary zero-change proof)

Compared `src/`, `Run_PY/`, `config/`, `webapp/` file hashes Version11 vs Version10.

Normalization:

- Ignore `__pycache__`, `*.pyc`, `*.log`, Office lock files
- Classify known identity/packaging edits separately from pipeline logic

Result (`Version11/docs/V11_0_VERIFICATION.json`):

- **634 files SHA256-matched**
- **13 identity diffs** (listed below)
- **0 true diffs**

`compileall` of `src`, `Run_PY`, `webapp`, `config`: **PASS**.  
`ast.parse` with `utf-8-sig` (BOM on three V10 runner originals): **0 errors**.

### 2. Production imports

Package imports of W.6 orchestrator/handoff, W.5 adapter/live_invoke, W.8 generator, C.5 call/prompt/contract, P.253 client, E.2 live_caller, D.2 resolver, VB.1 orchestrator, Flask app/adapter: **all OK** (`docs/V11_0_IMPORT_CHECK.json`).

No Claude API calls.

### 3. Stub 14-stage pipeline execution

W.2 / W.6 Flask tests with `STEEL_WEB_PIPELINE_MODE=stub`, `HYBRID_MODE=off`:

- Stages executed: `VROOT1, R1, T1, R2A, R21B, R21C, R21D, L22, R3, R31, R12A, R13, HYBRID, VB1`
- Excel produced (`Estimation_Output_<run_id>.xlsx`)
- Summary in stub mode: `total_beams=0`, `total_steel_kg=0.0` (synthetic DXF, not a drawing estimate)

This proves the V11 web adapter invokes the same 14-stage contract. It is **not** a Galera/Hybrid quantity comparison.

### 4. Production tests (no Claude)

| Suite | Result |
|---|---|
| W.2 + W.16 + W.19.1 + W.6 Flask | 36 tests, 2 skipped, **OK** |
| W.6 package `unit_tests.py` | 17 tests **OK** (after copying P.26 `role_family` + W.10) |
| W.18B spacer | 15 passed |

Skipped W.16 items are Galera GN path skips already present in the Version10 tests, not V11 weakening.

---

## Difference classification

### EXPECTED_ENVIRONMENTAL_DIFFERENCE

| Item | Class | Notes |
|---|---|---|
| `ENGINE_LABEL` / `ENGINE_DISPLAY` | identity | Version11 string only; `APP_RELEASE` still `W.19.1` |
| `ENGINE_ROOT` path | identity | `.../Version11` vs `.../Version10` |
| Run IDs / timestamps in Excel / logs | run metadata | would differ on any two executions |
| Stub Excel kg/beams = 0 | stub fixture | synthetic DXF, not production drawing output |

### EXPECTED_RUN_ID_DIFFERENCE

Web `run_id` format `YYYYMMDD_HHMMSS_<hex>` is generated per invocation. Stub tests assert isolation (`run_a != run_b`), not a fixed ID.

### INTENTIONAL_PACKAGING_DIFFERENCE (not accuracy)

| File | Why |
|---|---|
| `webapp/config.py` | ENGINE identity strings |
| `webapp/services/version10_adapter.py` | accept Version11 path in ENGINE_ROOT guard |
| `webapp/tests/test_w2_smoke.py` | assert Version11 labels |
| 10 mixed-package `__init__.py` | prevent import-time load of excluded P.254/B.1 orchestrators |

These do not change handoff, Vision prompts, engineering formulas, or Excel builders.

### TRUE_PIPELINE_DIFFERENCE

**None.** After adding the proven P.26 subset and W.10 package, W.6 unit tests pass. No production Python in Version10 was edited to make V11 work.

### UNRESOLVED_DIFFERENCE

**None in copied source.**

**Deferred comparison (not a pipeline diff):** a live Hybrid run of Galera / Second–Sixth drawings through V11 vs a stored V10 Excel was **not** executed.

Reason:

- Phase V11.0 forbids consuming Claude API credits for casual validation
- A full 14-stage Hybrid drawing run is a multi-hour, credit-consuming production-like job
- Byte-for-byte Excel equality is also impossible without stripping run_id / timestamp / engine-root metadata

If a later authorized phase replays a drawing, compare after this normalization:

1. Strip run_id, timestamps, absolute paths, ENGINE_ROOT strings
2. Compare beam IDs, roles, diameters, status, matching, stirrup fields, cut lengths, quantities, steel kg, BBS rows, Excel sheet structure, W.19.1 metadata fields
3. Classify remaining diffs with the four classes in this report

Until that replay is authorized, the zero-change claim is **source-identity + contract tests**, not live Excel bytes.

---

## What was not compared

- Live Claude Vision responses (forbidden in this phase)
- Full Galera Hybrid Excel vs a historical V10 web_run
- Generated `data/output` trees (excluded from the fork by policy)
