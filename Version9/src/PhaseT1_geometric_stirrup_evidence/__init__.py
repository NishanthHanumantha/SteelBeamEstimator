"""
Phase T1 — Geometric Stirrup Evidence Engine.
MODEL_VERSION: 9.3.3

Vector-space stirrup detection + zone/spacing refinement for residual
TARGET_MISSING / TARGET_WRONG_QTY beams only. Evidence provider for R.2.1D.

9.3.3: local-extent crop rendering + beam-scoped bbox for the OpenCV
fallback's crop generation (render/crop mechanism fix only — no T1.2
detection threshold, T1.3 fusion, or T1.4 zone-refinement changes).
"""
MODEL_VERSION = "9.3.3"
PHASE_ID = "T1"
