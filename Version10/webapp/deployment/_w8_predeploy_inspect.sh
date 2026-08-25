#!/bin/bash
set -euo pipefail
echo HOST="$(hostname)"
echo DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo UNIT_ACTIVE="$(systemctl is-active steel-beam-estimator-v10.service)"
systemctl show steel-beam-estimator-v10.service -p ActiveState,SubState,NRestarts,FragmentPath,ExecMainStartTimestamp --no-pager
echo WORKERS
ps -o pid=,cmd= -C gunicorn || true
echo ENVFILE
sudo ls -l /etc/steel-beam-estimator-v10.env
echo ENVNAMES
sudo grep -E '^[A-Z_]+=' /etc/steel-beam-estimator-v10.env | cut -d= -f1
echo MODELINE
sudo grep -E '^HYBRID_MODE=' /etc/steel-beam-estimator-v10.env
echo KEYLINECOUNT
sudo grep -c '^ANTHROPIC_API_KEY=' /etc/steel-beam-estimator-v10.env || true
echo ANTHROPIC
/opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp/.venv/bin/python -c 'import anthropic; print(anthropic.__version__)'
echo HEALTH
curl -sS --max-time 10 http://127.0.0.1:8001/health
echo
echo APP_RELEASE
grep -n 'APP_RELEASE' /opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp/config.py | head -3
echo W8
if [ -d /opt/steel-beam-estimation/SteelBeamEstimator/Version10/src/PhaseW8_production_vision_evidence ]; then echo W8_PRESENT; else echo W8_ABSENT; fi
echo P2610A
if [ -f /opt/steel-beam-estimation/SteelBeamEstimator/Version10/src/PhaseP2610A_beam_region_crop_audit/cropper.py ]; then echo P2610A_PRESENT; else echo P2610A_ABSENT; fi
echo P2610B
if [ -f /opt/steel-beam-estimation/SteelBeamEstimator/Version10/src/PhaseP2610B_adaptive_beam_detail_crop/envelope.py ]; then echo P2610B_PRESENT; else echo P2610B_ABSENT; fi
echo P2610C1
if [ -f /opt/steel-beam-estimation/SteelBeamEstimator/Version10/src/PhaseP2610C1C2_evidence_inventory_candidate_selection/selector.py ]; then echo P2610C1_PRESENT; else echo P2610C1_ABSENT; fi
echo P2610C3
if [ -f /opt/steel-beam-estimation/SteelBeamEstimator/Version10/src/PhaseP2610C3_visual_completeness_claude_shadow/visual_completeness_gate.py ]; then echo P2610C3_PRESENT; else echo P2610C3_ABSENT; fi
echo GIT
git -C /opt/steel-beam-estimation/SteelBeamEstimator rev-parse --short HEAD 2>/dev/null || echo NOGIT
echo REQUIREMENTS
grep -n anthropic /opt/steel-beam-estimation/SteelBeamEstimator/Version10/requirements.txt | head -3
