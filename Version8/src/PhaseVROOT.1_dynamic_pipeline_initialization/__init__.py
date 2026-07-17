"""
Phase V.ROOT.1 -- Dynamic DXF Discovery & Pipeline Initialization
MODEL_VERSION: 7.1.0

Mandatory entry point for every production pipeline run.
Completely eliminates all project-specific hardcoding, Version5 dependencies,
and Benchmark Set 1 assumptions.

Architecture:
    Input Folder -> V.ROOT.1 -> L.2 -> SI.0 -> SI.1 -> L.2.2 -> L.2.1
                             -> L.3 -> Steel -> BBS -> Excel
"""
MODEL_VERSION  = "7.1.0"
PHASE_ID       = "V.ROOT.1"
PHASE_NAME     = "Dynamic DXF Discovery & Pipeline Initialization"
PHASE_FOLDER   = "PhaseVROOT.1_dynamic_pipeline_initialization"
