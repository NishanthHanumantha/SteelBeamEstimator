# Deployment assets

Infrastructure configuration and host scripts only.

**No estimation / engineering logic lives here.**

**Package version:** D.4.2 (packaging layout)  
**Runtime baseline:** MODEL_VERSION 8.9.5 — Production Ready

---

## Layout

| Path | Purpose |
|------|---------|
| `config.yaml` | Deploy parameters + path segments |
| `gunicorn/gunicorn.conf.py` | Gunicorn workers / timeouts |
| `nginx/steel-beam-estimator.conf` | Reverse proxy site template |
| `systemd/steel-beam-estimator.service` | systemd unit template |
| `scripts/_common.sh` | **Only** path calculator + config loader |
| `scripts/01`…`10_*.sh` | Idempotent host scripts (consume `_common.sh`) |
| `scripts/validate_packaging.py` | Packaging health contract check |

---

## Path abstraction (D.4.1)

Scripts must not hardcode `Steel-Beam-Estimation/current_model`.

Configure:

```yaml
application_directory: "/opt/steel-beam-estimation"
repository_directory: "SteelBeamEstimator"   # optional
project_directory: "Steel-Beam-Estimation"
model_directory: "current_model"
```

Or leave segments unset and let `_common.sh` auto-discover a single `current_model`
under `application_directory`.

Supports:

- Fresh flat installs  
- Existing monorepo installs (`…/SteelBeamEstimator/Steel-Beam-Estimation/…`)  
- Legacy `app_subdirectory` / `model_subdirectory` keys  

---

## Rules

1. Always target **`current_model/`** via resolved `MODEL_ROOT`.
2. Independent from Concrete & Shuttering Estimator.
3. Prefer `config.yaml` + auto-discovery over hardcoded host paths.
4. Scripts are idempotent and fail safely (`set -euo pipefail`).

---

## Usage

See [../docs/DeploymentGuide.md](../docs/DeploymentGuide.md).
