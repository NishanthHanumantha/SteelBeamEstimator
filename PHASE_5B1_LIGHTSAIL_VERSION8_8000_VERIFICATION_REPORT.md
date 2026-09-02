# Phase 5b.1 — Lightsail Version8 :8000 Verification

Read-only SSH inspect. No services stopped/started, no Nginx/systemd changes, no estimate, no Claude call, no Version8/Version10 code change.

---

## 1. Verification Date

- **Server time:** 2026-09-02 05:39:33 UTC
- **Host:** `ubuntu@13.127.104.99` (Lightsail)
- **Repository baseline:** `4d4dad540ec8f528b0b2f8242a70dfce0c1a9eab`  
  `docs: finalize Version8 archive Go-No-Go decision`
- **Method:** SSH + `ss` / `systemctl` / `ps` / `nginx -T` / loopback and public `GET /health` only

---

## 2. Current Public Production Path

Verified:

```
Internet http://13.127.104.99/  (:80)
  → Nginx 1.24.0 (active, enabled)
  → 127.0.0.1:8001
  → steel-beam-estimator-v10.service
  → Version10/webapp Gunicorn wsgi:app (1 worker)
  → 14-stage Hybrid production pipeline (W.19.1)
```

Evidence:

- Public `/health` HTTP 200 from Nginx: `engine_label=Version10`, `app_release=W.19.1`, `engine_root=.../Version10`, stages `VROOT1…HYBRID…VB1` (14).
- Loopback `http://127.0.0.1:8001/health` matches the public payload.
- Active site `/etc/nginx/sites-enabled/steel-beam-estimator.conf` upstream is **`127.0.0.1:8001`**. Compiled `nginx -T` contains **no** `8000`.
- Static aliases point at `Version10/webapp/static/`.
- `/etc/steel-beam-estimator-v10.env` has `HYBRID_MODE=production` (value only; no secrets printed). Public `/health` hybrid `mode` is `production`.
- Gunicorn PIDs **190246** (master) / **190247** (worker), user `ubuntu`, cwd `.../Version10/webapp`.

This matches `PRODUCTION_TRUTH.md`. No hard-stop on routing.

---

## 3. Port :8000

| Check | Result |
|------|--------|
| :8000 listening | **YES** (`127.0.0.1:8000` only — not public) |
| Process | Gunicorn `wsgi:app` from `Steel-Beam-Estimation/current_model/.venv` |
| PID | master **164315**, worker **164316** |
| User | `ubuntu` |
| Service | `steel-beam-estimator.service` (active, enabled) |
| Version8 involved | **YES** — `/health` `engine_root=.../Version8`, `model_version=8.9.4`, `phase=D.4.2` |
| Active Nginx route to :8000 | **NO** |
| Current estimator uses :8000 | **NO** |
| Rollback service active | **YES** (loopback only) |

`:8000` is a live loopback process. It is **not** the public estimator.

---

## 4. steel-beam-estimator.service

| Field | Value |
|-------|--------|
| Exists | **Yes** (`/etc/systemd/system/steel-beam-estimator.service`, mode 0600) |
| Loaded | **Yes** |
| Active | **Yes** (`active` / `running`) |
| Enabled | **Yes** (`UnitFileState=enabled`) |
| ExecStart | `.../Steel-Beam-Estimation/current_model/.venv/bin/gunicorn --config .../deployment/gunicorn/gunicorn.conf.py --bind 127.0.0.1:8000 wsgi:app` |
| Working directory | `/opt/steel-beam-estimation/SteelBeamEstimator/Steel-Beam-Estimation/current_model` |
| Port | **127.0.0.1:8000** |
| Version8 dependency | **Yes** — `/health` `engine_root` is `.../Version8`; `web_runs_root` is `.../Version8/data/web_runs`. Server tree `.../Version8` still exists. |

Associated Gunicorn: PIDs 164315 / 164316 as above.

`systemctl cat` of this unit was permission-denied (0600); `systemctl show` + process argv + `/health` were sufficient.

Historical rollback copies still present (unused by active Nginx): `/opt/steel-beam-estimation/rollback-w3/` (`steel-beam-estimator.conf` upstream **:8000**, captured 2026-08-24). Active Nginx comment still says rollback is restore of the old conf.

---

## 5. Operational Classification

**ACTIVE_BUT_UNUSED**

The old 8.9.4 / Version8 Gunicorn is **running** on loopback `:8000` and the systemd unit is **enabled**. Active public routing does **not** use it. The estimator URL is Version10 `:8001`. Existence of a running rollback process is not evidence that current production traffic requires it. It remains a usable Nginx-restore fallback until operators retire it.

---

## 6. Version8 Archive Impact

**ARCHIVE_CONDITIONAL_GO**

Server evidence does **not** support **ARCHIVE_GO** (rollback process still active and Version8-backed) and does **not** require **ARCHIVE_NO_GO** (current estimator does not use `:8000`).

Git-archiving `Version8/` would not by itself stop this service, but the live `:8000` app **reads Version8** as `engine_root`. Moving/deleting Version8 on the server, or deploying a tree without it, would break that rollback process. Operator must explicitly retire `:8000` / `steel-beam-estimator.service` **or** accept losing that rollback before a Version8 archive/move.

This phase did **not** archive, stop, or reconfigure anything.

---

## 7. Recommendation

Operator should explicitly retire or accept loss of `steel-beam-estimator.service` / loopback `:8000` before any Version8 archive/move.
