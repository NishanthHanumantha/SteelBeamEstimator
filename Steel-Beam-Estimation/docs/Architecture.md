# Architecture — Steel Beam Reinforcement Estimation

**Phase:** D.2 (application foundation)  
**Scope:** Flask application framework around the existing estimation engine.  
Estimation algorithms remain inside the engine referenced by `STEEL_ENGINE_ROOT` / packaged `current_model/`.

---

## High-level request flow

```text
Browser
    ↓
Nginx          (TLS termination, static files, reverse proxy)
    ↓
Gunicorn       (WSGI workers)
    ↓
Flask          (upload UI + API — current_model/webapp)
    ↓
Beam Estimation Engine   (current_model/src — version-swappable)
    ↓
Excel Output   (current_model/outputs)
```

---

## Component boundaries

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Edge | `deployment/nginx/` | HTTPS, routing, security headers |
| Process | `deployment/gunicorn/` + `deployment/systemd/` | App process lifecycle |
| Presentation | `current_model/webapp/` | Upload, status, download — **no engineering formulas** |
| Engine | `current_model/src/` | DXF interpretation → steel / BBS / Excel |
| Runtime data | `current_model/{inputs,temp,outputs,logs}/` | Ephemeral and generated artefacts |

---

## Version-agnostic model slot

```text
Steel-Beam-Estimation/
└── current_model/          ← always the active package
       ├── src/
       ├── webapp/
       ├── config/
       └── ...
```

- Deployment units (Nginx, Gunicorn, systemd, scripts) **must** reference `current_model/`.
- Upgrading from one engine release to the next means **replacing `current_model/` contents**.
- Deployment configs must **not** hardcode names such as `Version8`, `Version9`, or `Version10`.

---

## Independence from Concrete Estimator

This package is a separate application:

- Separate repository folder / service name
- Separate Nginx site / systemd unit (to be defined in later phases)
- Separate Python virtualenv and working directory
- No shared runtime paths with the Concrete & Shuttering Estimator

---

## Data flow (functional)

```text
3 × DXF uploads (General Notes, Framing, Reinforcement)
        ↓
    Flask validation + staging (temp/)
        ↓
    Estimation engine pipeline
        ↓
    Estimation_Output.xlsx (outputs/)
        ↓
    Browser download
```

---

## What is intentionally out of scope for D.1

- Concrete Gunicorn / Nginx / systemd files
- AWS Lightsail instance provisioning
- Copying or packaging an active engine into `current_model/`
- Engineering logic changes

Those belong to later deployment phases.
