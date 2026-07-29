# Technical Debt Register — MODEL_VERSION 8.9.5

**Purpose:** Future work only. Do **not** implement as part of the production
baseline freeze.

Engineering behaviour in 8.9.5 matches 8.9.4. Items below are optional
enhancements or residual offline/dev debt.

---

## Architecture / I/O (non-blocking)

| ID | Item | Notes |
|----|------|-------|
| TD-01 | R.2A `Benchmark_Set_2` GN offline fallback | Web uses pointer file; offline factory still scans folder name |
| TD-02 | `v7_root` parameter naming in R13/VB1 APIs | Alias for Version8 engine/run root — rename in a future API cleanup |
| TD-03 | Shared `PRODUCTION_EXCEL` / `V7_ROOT` / `ARTEFACT_SEED_ROOT` settings | Documented unused by web stages; remove when offline tools no longer need them |
| TD-04 | R.1.2A `--full` forensic nested rebuild | Not in PRODUCTION_STAGES; offline diagnostic only |
| TD-05 | Excel header strings “Benchmark Set 1/2” | Cosmetic Drawing Reference labels — changing alters workbook content |

---

## Accuracy / engineering (future branches)

| ID | Item |
|----|------|
| TD-10 | Estimator parity / accuracy campaigns on new drawing sets |
| TD-11 | Reinforcement interpretation enhancements |
| TD-12 | Stirrup / small-bar family improvements |
| TD-13 | Multi-project General Notes robustness |

---

## Performance / ops (future)

| ID | Item |
|----|------|
| TD-20 | Pipeline stage timing / profiling |
| TD-21 | Parallel-safe stage execution (if ever required) |
| TD-22 | Lightsail TLS cutover / hardened reverse proxy |

---

## AI / product (future)

| ID | Item |
|----|------|
| TD-30 | New AI models or assisted review features |
| TD-31 | UI diagnostics / engineering review screens |

---

## Explicit non-goals for 8.9.5 baseline

- No estimation rule changes
- No Excel layout redesign
- No RunContext redesign
- No new PRODUCTION_STAGES without a dedicated phase
