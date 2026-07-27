# Deployment assets

This folder holds **infrastructure configuration only**.

It must not contain estimation / engineering logic.

---

## Layout

| Path | Purpose | Status |
|------|---------|--------|
| `gunicorn/` | Gunicorn config | Placeholder (use `current_model/wsgi.py` later) |
| `nginx/` | Nginx site / upstream config | Placeholder |
| `systemd/` | systemd unit files | Placeholder |
| `scripts/validate_packaging.py` | Local packaging checklist | **Ready (D.3)** |

---

## Rules

1. Reference the application as **`../current_model/`** (or an absolute path ending in `current_model`).
2. Do **not** hardcode model version directory names.
3. Keep this package independent from the Concrete & Shuttering Estimator deployment.
4. Prefer environment variables for ports, workers, and secrets.

---

## Next phases

Concrete files will be added in later deployment phases (see `docs/DeploymentGuide.md`).
