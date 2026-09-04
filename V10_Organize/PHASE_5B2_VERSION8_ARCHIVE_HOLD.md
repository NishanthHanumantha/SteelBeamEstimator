# Phase 5b.2 — Version8 Rollback Preservation / Archive Hold

**Date:** 2026-09-02  
**Baseline:** `aef345a7fe1fdb25d73e7e04c78d8e998ce90a2f`  
  `docs: verify Lightsail Version8 rollback status`  
**Server mutated:** No  
**Version8 mutated:** No  
**Production code mutated:** No

---

## Decision

VERSION8 :8000 = TEMPORARILY PRESERVED

Owner/operator: keep `steel-beam-estimator.service` running on loopback `:8000` during Version10 Hybrid estimator acceptance.

---

## Current Production

Version10 W.19.1 Hybrid remains the only current public production system.

Public path:

http://13.127.104.99/

Nginx :80
→ 127.0.0.1:8001
→ Version10 webapp
→ 14 production stages
→ W.6 Hybrid
→ VB.1

Live Version8 execute / required-read / required-write = none (Phase 5a / 5b). VROOT1 Version8 coupling is closed.

---

## Legacy Rollback

Version8 remains running on:

127.0.0.1:8000

Service:

steel-beam-estimator.service

Status:

ACTIVE_BUT_UNUSED

(Phase 5b.1: process is live; active Nginx does not route to it.)

---

## Reason for Preservation

Estimators are still testing and validating Version10 Hybrid production.

The old Version8 service is retained temporarily as a rollback/fallback option during this acceptance period.

---

## Archive Gate

Version8 archive/move is explicitly DEFERRED.

Do NOT archive until:

1. Version10 Hybrid production acceptance is complete.
2. Owner/operator confirms the old Version8 rollback is no longer required.
3. Owner explicitly requests the Version8 archive phase.

Do not stop, disable, move, rename, delete, or modify Version8, and do not change Lightsail systemd/Nginx for this rollback, until that authorization.

---

## Current Status

Version8 archive status:

CONDITIONAL_GO — ARCHIVE HOLD
