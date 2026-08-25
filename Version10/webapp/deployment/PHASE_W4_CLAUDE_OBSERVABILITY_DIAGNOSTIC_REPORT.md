# PHASE W.4 — PRODUCTION CLAUDE API OBSERVABILITY & DIAGNOSTIC REPORT

**Phase:** W.4  
**Type:** Investigation / diagnostic only  
**MODEL_VERSION (engineering label, not web release):** 10.0.0 (project header)  
**Date:** 2026-08-25  
**Outcome:** **PRODUCTION_CLAUDE_DIAGNOSTIC_PASS**

No production estimation behaviour, systemd, Nginx, or secrets were changed.

---

## 1. Phase identification

Phase W.4 investigates whether live Claude / Anthropic API calls occur during the public Version10 web estimator, after the Claude Platform dashboard appeared to stop at approximately 2026-08-22 while later production Excel runs succeeded.

## 2. Investigation objective

Determine, with labelled evidence, whether production is configured for Claude, whether the running systemd process can see credentials, which stages can call Claude, whether recent public runs reached those stages, and why dashboard usage may not have moved.

## 3. Production environment inspected

| Item | Observed 2026-08-25 |
|------|---------------------|
| Public URL | http://13.127.104.99/ |
| `/health` | `engine_label=Version10`, `app_release=W.3`, `t1_included=true` |
| systemd | `steel-beam-estimator-v10.service` **active** and **enabled** |
| Gunicorn | `127.0.0.1:8001`, workers=1, MainPID 152912 |
| Engine root | `/opt/steel-beam-estimation/SteelBeamEstimator/Version10` |
| Web runs | `/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/` |
| Old 8.9.x | still on `127.0.0.1:8000` (not used for this investigation) |

Inspection method: static code trace of the local Version10 tree (same architecture as W.3 deploy) plus SSH read-only systemd / process / journal / run-tree inspection. Secrets were not printed.

## 4. Exact code-level Claude execution map

**Public Excel estimator (what Nginx actually runs):**

```
Browser
  → Nginx :80
  → Gunicorn wsgi:app  (steel-beam-estimator-v10)
  → start_estimation() / single-flight
  → invoke_version10_pipeline()
  → PRODUCTION_STAGES subprocesses only:
       VROOT1 → R1 → T1 → R2A → R21B → R21C → R21D
       → L22 → R3 → R31 → R12A → R13 → VB1
  → Estimation_Output.xlsx
```

None of those runners import `anthropic`, `ClaudeClient`, `call_claude_vision`, or `PromptExecutor`.  
**CONFIRMED** by searching `Version10/webapp/` (zero Claude matches) and the production `Run_PY` / production `src/PhaseR*`, `PhaseT1*`, `PhaseL.2.2*`, `PhaseVB.1*`, `PhaseVROOT.1*` packages.

**Claude-capable tree (research / shadow / live-benchmark only; not the web Excel path):**

```
INPUT DRAWING (web upload)
    |
    +--> Version10 production stages (ALWAYS)
    |       deterministic DXF / geometry / T1 / VB.1
    |       Excel generated
    |       Claude is never consulted
    |
    +--> Hybrid D/E and P2.5/P2.6 runners (NOT invoked by webapp)
            |
            +--> LIVE_BENCHMARK / pilot runner selected?
                    |
                    +--> NO  --> offline / replay / shadow artefacts
                    |
                    +--> YES --> call_claude_vision()
                                   |
                                   +--> ClaudeClient.generate_vision_response()
                                          messages.create (Anthropic HTTP)
```

## 5. All Claude-capable stages

Live HTTP is centralized in:

| Location | Function | Purpose | On web Excel path? |
|----------|----------|---------|--------------------|
| `src/llm/claude_client.py` | `ClaudeClient.generate_response` / `generate_vision_response` | Anthropic `messages.create` | **NO** |
| `src/llm/prompt_executor.py` | `PromptExecutor.execute*` | Text prompts via ClaudeClient | **NO** |
| `src/ai/Phase AI.1 …/reasoning_manager.py` | engineering reasoning | Uses PromptExecutor | **NO** |
| `src/PhaseP253_…/claude_vision_client.py` | `call_claude_vision` | Vision wrapper | **NO** |
| P2.5.4 / P2.5.5 / P2.5.7 / P2.6 / P2.6.1 / P2.6.6 / P2.6.7 | vision observers / live callers | Shadow or live benchmark | **NO** |
| P2.6.10-C.3 / C.5 | Claude shadow / stratified vision | Research | **NO** |
| P2.6.10-E.2 `live_caller.py` | `LIVE_CLAUDE_CALL = True` only in `LIVE_BENCHMARK` (default mode is `OFFLINE_VALIDATION`) | Hybrid live vision benchmark | **NO** |
| P2.6.10-E.1 | `LIVE_CLAUDE_CALL = False` | Hybrid replay | **NO** |
| P2.6.10-D.1–D.4 | documented “Does not call Claude” | Shadow hybrid | **NO** |

`anthropic` is listed in `Version10/requirements.txt` because the research tree and `src/llm` ship with Version10. Presence of the package is **not** evidence of production invocation.

## 6. Trigger conditions

Web production trigger: three DXF uploads → `PRODUCTION_STAGES` only (`Version10/webapp/config.py`).  
T16CHAIN is excluded. Hybrid D/E is excluded (`version10_adapter.py` does not import hybrid runners).

Research Claude trigger (not used by Gunicorn): explicit `Run_PY/run_phase_p25*` / `p26*` / `p2610c3` / `p2610e2` with live mode, plus `ANTHROPIC_API_KEY` loaded via `ClaudeConfig` (see §11).

P2.5.5 `should_invoke_claude` defaults to full shadow for that experiment; that gate is not imported by the web adapter.

## 7. Expected conditions for live API usage

Live Claude is expected only when an operator runs a Claude-capable **research/benchmark** runner in live mode with a working API key.

It is **not** expected when a user clicks Estimate on http://13.127.104.99/.

## 8. Whether every production run should generate Claude usage

**No. CONFIRMED.**

Answers to the required questions:

| Q | Answer | Evidence level |
|---|--------|----------------|
| A. Claude on EVERY drawing? | **No** | CONFIRMED |
| B. Only ambiguous cases? | Not on the web path. Ambiguity gates exist only in P2.5.5+ research | CONFIRMED for web; N/A for production Excel |
| C. Only when deterministic logic fails? | Web path does not escalate to Claude on failure; it errors or completes deterministically | CONFIRMED |
| D. Shadow-only? | Hybrid D/E and most P2.6.10-D/E web-adjacent research is shadow / `PRODUCTION_WRITE=false`. Live Claude exists in separate benchmark modes | CONFIRMED |
| E. Benchmark/test only? | Live Claude is used by P2.5.x / P2.6.x / E.2 live benchmark runners, not Flask | CONFIRMED |
| F. Disabled in normal production? | Production **omits** Claude stages rather than setting a live-Claude flag false in Gunicorn | CONFIRMED |
| G. Successful Excel with ZERO Claude calls? | **Yes — that is the designed path** | CONFIRMED |
| H. Recent production results consistent with zero Claude? | **Yes** | CONFIRMED |

## 9. Production configuration findings

systemd unit (`steel-beam-estimator-v10.service`):

- WorkingDirectory: `.../Version10/webapp`
- Environment: `FLASK_ENV=production`, `PYTHONUNBUFFERED=1`, `MPLBACKEND=Agg`, `GUNICORN_BIND=127.0.0.1:8001`
- EnvironmentFile: `-.../webapp/.env` (`ignore_errors=yes`)
- No `ANTHROPIC_API_KEY` in unit Environment

Local/dev: `ClaudeConfig.DOTENV_PATH` is hardcoded to  
`C:\Users\nishanth.h\SteelBeamEstimator\.env`  
(`src/llm/claude_config.py`). That path cannot exist on Ubuntu Lightsail.

W.3 packager skips `*.env` files. Webapp `.env` was never created on the instance (W.3 secret write was not performed).

## 10. systemd environment findings

Process environ keys for MainPID 152912 (**CONFIRMED** names only):

`FLASK_ENV, GUNICORN_BIND, HOME, INVOCATION_ID, JOURNAL_STREAM, LANG, LOGNAME, MEMORY_PRESSURE_WATCH, MEMORY_PRESSURE_WRITE, MPLBACKEND, NOTIFY_SOCKET, PATH, PYTHONUNBUFFERED, SHELL, SYSTEMD_EXEC_PID, USER`

No `CLAUDE*` or `*_API_KEY` keys.

## 11. Secret-safe credential availability status

| Item | Status |
|------|--------|
| `ANTHROPIC_API_KEY` in Gunicorn process | **ABSENT** |
| `Version10/webapp/.env` | **ABSENT** |
| `Version10/.env` | **ABSENT** |
| repo-root `.env` on instance | **ABSENT** |
| systemd EnvironmentFile | referenced, ignore-errors, file missing → **NOT_VISIBLE_TO_SYSTEMD** / unused |
| `ClaudeConfig.DOTENV_PATH` | Windows workstation path — **CONFIGURED_BUT_UNUSED** on Linux even if a key were later added to systemd, unless `load_api_key()` is changed (not done in W.4) |

This is a **secondary** finding. The web Excel path would still not call Claude if a key were present.

## 12. Runtime log findings

`journalctl -u steel-beam-estimator-v10 --since 2026-08-22`:

- Matches for `claude` / `anthropic`: **ClaudeBot crawler User-Agent** on GET `/` and `/favicon.ico` (2026-08-25 01:52 UTC). **Not** API usage.
- `api_key`, rate limit, 401, 429, fallback: **0**
- Adapter logs show `Runner start/finish` for the 13 production stages only

There is no Claude invocation event, cache event, or Anthropic HTTP log on the production service.

**CLAUDE_RUNTIME_OBSERVABILITY_INSUFFICIENT** for answering “did Claude run?” from a dedicated telemetry field — but the stage list and code path are sufficient to conclude it did not run on these jobs.

## 13. Recent production run analysis

All runs under `data/web_runs/` on the instance:

| run_id | started_at (UTC) | beams | kg | notes |
|--------|------------------|-------|----|--------|
| `20260824_120944_1498af3a` | 2026-08-24T12:09:44 | 18 | 1424.397 | W.3 First Set smoke |
| `20260824_121014_8338f856` | 2026-08-24T12:10:14 | 18 | 1424.397 | W.3 sequential smoke |
| `20260824_124732_f0dfc013` | 2026-08-24T12:47:32 | 143 | 36271.834 | W.3 Fifth Set |
| `20260825_053226_38f86499` | 2026-08-25T05:32:27 | **118** | **21690.436** | public production |
| `20260825_054727_3d59d221` | 2026-08-25T05:47:27 | 139 | 12878.322 | public production |

Every run: `pipeline_mode=live` (adapter meaning: real Run_PY, not stub), `t1_included=true`, same 13 stages.  
No run tree contained files named claude / anthropic / vision / hybrid / p2610. **CONFIRMED.**

A third public set after W.3 is **UNKNOWN** if it was not written under this `web_runs` root; only two post-W.3 public successes are on disk.

## 14. Analysis of the ~118 beam / 21,690.436 kg / ~233 s run

| Field | Evidence |
|-------|----------|
| run_id | `20260825_053226_38f86499` |
| Timestamp | 2026-08-25 05:32:27–05:36:20 UTC |
| Duration | **233.08 s** (journal `Pipeline complete`) |
| T1 | **194.45 s**, exit 0 |
| Summary | 118 beams, 505 bars, 21690.436 kg |
| Excel | 66132 bytes at run `Production_Output/Estimation_Output.xlsx` |
| Inputs | GN `SE-100_GENRAL_NOTE_SH-01_SH-02_R0_1.dxf`; framing `INIZIO_BASEMENT-_01_FRAMING_PLAN_10-04-2026.dxf`; reinforcement `SE-204_BASEMENT-01_FLOOR_BEAM_REINFORCEMENT_DETAILSSH-01_TO_03.dxf` |
| Stages reached | VROOT1, R1, T1, R2A, R21B, R21C, R21D, L22, R3, R31, R12A, R13, VB1 |
| Claude-eligible stage reached | **NO** (those stages are not in `PRODUCTION_STAGES`) |
| Live Claude call executed | **NO** |
| Cache / fallback | **NO** evidence of Claude cache; not applicable |
| Outcome | success, workbook generated |

Cannot be proven from this host: Anthropic account dashboard contents, or any Claude usage from a **different** machine (developer laptop hybrid/E.3). **UNKNOWN** for the dashboard itself; **CONFIRMED** that this Lightsail job did not call Claude.

## 15. Claude cache / fallback analysis

Web adapter has no Claude cache. Research runners may replay frozen vision JSON (P2.5.8, E.1 `LIVE_CLAUDE_CALL=False`). Those runners were not executed for the 118-beam job. **CONFIRMED** no Claude cache/fallback on the investigated production runs.

If `ClaudeClient` were constructed on Linux without a key, `load_api_key()` raises `ClaudeAuthenticationError` when the Windows `.env` path is missing — it does **not** fall back to empty-key live calls. That code was not entered by Gunicorn for these runs.

## 16. Existing safe diagnostic availability

`/health` reports engine, T1, stages, busy — **not** Claude.

There is no production dry-run or “ping Anthropic” command on the web service.

Instantiating `ClaudeClient` would not be a documented production health check and was **not** executed (would fail on missing Windows `.env` without proving dashboard usage).

**NO_SAFE_EXISTING_LIVE_CLAUDE_DIAGNOSTIC**

A follow-up could add a non-invasive `/health` field such as `claude_on_production_excel_path: false` without calling the API.

## 17. Observability gaps

If a future phase wires Claude into Excel production, current logs cannot emit:

- Claude invocation yes/no
- model name
- cache vs live vs skip reason
- correlation with `run_id`

Today those gaps do **not** block the conclusion for the **current** architecture: the stage list is the invocation list.

## 18. Evidence table

| Claim | Level |
|-------|-------|
| Public app is Version10 W.3 production Excel pipeline | CONFIRMED |
| Web `PRODUCTION_STAGES` never includes Claude/hybrid runners | CONFIRMED |
| Production subprocesses for 118-beam and 139-beam runs were those 13 stages only | CONFIRMED |
| `ANTHROPIC_API_KEY` absent from systemd Gunicorn environ | CONFIRMED |
| `.env` files absent on instance | CONFIRMED |
| Journal “claude” hits are ClaudeBot crawler, not API | CONFIRMED |
| Successful Excel requires zero Claude calls | CONFIRMED |
| Anthropic dashboard last-used 2026-08-22 | UNKNOWN (not inspected; user report) |
| Dashboard gap caused by Lightsail web runs not calling Claude | STRONGLY_INDICATED |
| Any Claude usage after Aug 22 from a laptop hybrid/E.3 run | UNKNOWN |

## 19. Primary classification

**CLAUDE_DETERMINISTIC_RESOLUTION**

The public estimator completes via the deterministic Version10 production stage list. Claude-capable stages are never reached, so no live API usage is required or produced for these jobs.

## 20. Secondary findings

1. **CLAUDE_CONFIG_MISSING** / **CLAUDE_CONFIG_NOT_VISIBLE_TO_SERVICE** for any future live Claude on this host: no key in process env; no `.env`; `DOTENV_PATH` is a Windows path.
2. Hybrid E.2 can live-call Claude in `LIVE_BENCHMARK` only; E.1 default is no live call; neither is started by Flask.
3. `src/llm` and P2.5.3 exist on the deployed disk but are unused by `steel-beam-estimator-v10`.
4. August 22 dashboard activity is consistent with **workstation** hybrid/vision research, not with Lightsail web traffic after W.3.

## 21. Production mutation statement

| Change | |
|--------|--|
| Production estimation logic changed | **NO** |
| Production configuration changed | **NO** |
| systemd changed | **NO** |
| Nginx changed | **NO** |
| Live Claude calls intentionally forced | **NO** |
| Secrets printed or committed | **NO** |

Public `/health` remained Version10 during inspection.

## 22. Recommended next action

**A. NO ACTION REQUIRED — Claude behaviour is correct.**

The public product is the deterministic Excel pipeline. Zero Claude dashboard usage after 2026-08-22 is the expected consequence of processing drawings through http://13.127.104.99/.

Do **not** “restore Claude configuration” to make the dashboard move unless a separate phase explicitly adds Claude Vision (or another Claude stage) to the **web production** stage list. That would be a product/architecture change, not a W.4 fix.

Optional later (not W.4): observability-only `/health` flag `production_excel_invokes_claude: false` so this question does not recur.
