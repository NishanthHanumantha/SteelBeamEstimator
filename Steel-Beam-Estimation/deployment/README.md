# Deployment assets

Infrastructure configuration and host scripts only.

**No estimation / engineering logic lives here.**

---

## Layout (Phase D.4)

| Path | Purpose |
|------|---------|
| `config.yaml` | Deploy parameters (IP, paths, repo, service names) |
| `gunicorn/gunicorn.conf.py` | Gunicorn workers / timeouts |
| `nginx/steel-beam-estimator.conf` | Reverse proxy site template |
| `systemd/steel-beam-estimator.service` | systemd unit template |
| `scripts/_common.sh` | Shared loader for `config.yaml` |
| `scripts/01`…`10_*.sh` | Idempotent host setup / update scripts |
| `scripts/validate_packaging.py` | Packaging health contract check |

---

## Rules

1. Always target **`current_model/`** — never hardcode model version folder names.
2. Keep this package independent from the Concrete & Shuttering Estimator.
3. Prefer `config.yaml` + environment variables over hardcoded host paths in scripts.
4. Scripts must be idempotent and fail safely (`set -euo pipefail`).

---

## Usage

See [../docs/DeploymentGuide.md](../docs/DeploymentGuide.md) for:

- Script purposes  
- Deployment sequence  
- GitHub update procedure  
- Rollback procedure  

**D.4 generates assets only — it does not SSH or deploy.**
