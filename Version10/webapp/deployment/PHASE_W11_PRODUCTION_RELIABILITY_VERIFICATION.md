# PHASE W.11 — PRODUCTION RELIABILITY VERIFICATION

Saved: 2026-08-26

---

## Deployment

| Item | Value |
|------|--------|
| Backup | `/opt/steel-beam-estimation/backups/w11_predeploy_20260826T102128Z` |
| Env file | `/etc/steel-beam-estimator-v10.env` preserved; timeout keys **appended** only |
| Local `.env` | not copied |
| Workers | 1 |
| Anthropic | 0.125.0 |
| HYBRID_MODE | production (restored after rollback probe) |
| Nginx | unchanged |
| Public `/health` | `phase=W.11`, `app_release=W.11`, `api_key_status=PRESENT`, no `sk-ant-` |

---

## Controlled production run

**`20260826_102310_1a616a17`** — First Set Galera OHT&STP (18 beams)

| Check | Result |
|-------|--------|
| Status progression | `Preparing visual evidence... Processing beam B16 (8 of 18)` then `Resolving reinforcement semantics... Processing beam B9 (18 of 18)` |
| Busy reject | second POST → 409 |
| Excel | download 200, PK zip, `Estimation_Output_20260826_102310_1a616a17.xlsx` |
| Wall | **360.2 s** |
| Evidence duration | **96.588 s** |
| Hybrid / Vision | **223.774 s** / **222.316 s** (avg **12.351 s**) |
| Claude | 18/18, timeout_count **0** |
| P2.6.10 primary | 13; explicit fallback 5 |
| Unexplained | 0 |
| Classification | `HYBRID_SUCCESS` |
| Steel | 1402.1 kg / 92 bars |
| Overwrites | cut_length **0**, geometry **0**, stirrup quantity **0** |

Compared with W.9 First Set (~321 s pipeline, Hybrid ~201 s): W.11 smoke is similar (360 s wall including polling granularity). No speed claim.

---

## Timeout verification

| Test | Where | Result |
|------|-------|--------|
| Hanging client bounded | local TEST-W11-03 | TimeoutExpired in &lt; 3 s; remaining path continues |
| Simulated TimeoutError | local TEST-W11-02 / W.6 | `VISION_TIMEOUT`, Excel fingerprint unchanged |
| One beam timeout, others continue | local TEST-W11-04/05 | B1 timed out, B2 not |
| All Vision fail | local TEST-W11-06 | Excel still present |
| Network exception | local TEST-W11-07 | `ConnectionError` classified; continue |
| Evidence timeout helper | local TEST-W11-08 | bounded |
| Production hang injection | **not done** | would be an outage; local hang test used instead |

---

## Original stuck run (forensic, pre-hardening)

**`20260826_084708_f74912b8`** completed after the 45-minute spinner:

- 143 beams, evidence **3707 s**, Vision **1543 s** (avg 10.8 s), Claude 143/143
- Excel **25738.789 kg**, `IS_456_DETERMINISTIC`
- Confirms the incident was slow sequential evidence, not a dead process

---

## Rollback

`HYBRID_MODE=off` + restart → `mode=off`, `production_may_invoke_claude=false`. Restored to `production`. 1 worker. File rollback: copy from `w11_predeploy_*`.

---

## Remaining production note

A 143-beam typical-floor drawing will still take on the order of **one hour of evidence + ~25 minutes of Vision**. W.11 makes that **visible and bounded**, not instant.
