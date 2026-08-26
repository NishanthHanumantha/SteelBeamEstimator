#!/bin/bash
set -euo pipefail
echo HOST="$(hostname)"
echo DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo KERNEL="$(uname -r)"
echo MEM
free -m
echo DISK
df -h / | tail -1
echo UNIT_ACTIVE="$(systemctl is-active steel-beam-estimator-v10.service)"
systemctl show steel-beam-estimator-v10.service -p ActiveState,SubState,NRestarts,FragmentPath,ExecMainStartTimestamp,EnvironmentFiles,User --no-pager
echo UNIT_WORKERS
grep -n "workers" /etc/systemd/system/steel-beam-estimator-v10.service || true
echo WORKERS
ps -o pid=,rss=,pcpu=,cmd= -C gunicorn || true
echo ENVFILE
sudo ls -l /etc/steel-beam-estimator-v10.env
echo ENVNAMES
sudo grep -E '^[A-Z_]+=' /etc/steel-beam-estimator-v10.env | cut -d= -f1
echo MODELINE
sudo grep -E '^HYBRID_MODE=' /etc/steel-beam-estimator-v10.env
echo KEYLINECOUNT
sudo grep -c '^ANTHROPIC_API_KEY=' /etc/steel-beam-estimator-v10.env || true
echo KEYSTATUS
if sudo grep -q '^ANTHROPIC_API_KEY=.\+' /etc/steel-beam-estimator-v10.env; then echo PRESENT; else echo ABSENT; fi
echo ANTHROPIC
/opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp/.venv/bin/python -c 'import anthropic; print(anthropic.__version__)'
echo REQUIREMENTS
grep -n anthropic /opt/steel-beam-estimation/SteelBeamEstimator/Version10/requirements.txt | head -3
echo HEALTH_LOCAL
curl -sS --max-time 10 http://127.0.0.1:8001/health
echo
echo HEALTH_PUBLIC
curl -sS --max-time 10 http://127.0.0.1/health
echo
echo APP_RELEASE
grep -n 'APP_RELEASE' /opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp/config.py | head -3
echo PHASE_ROUTE
grep -n 'phase' /opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp/routes.py | head -5
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
echo M1
if [ -f /opt/steel-beam-estimation/SteelBeamEstimator/Version10/src/PhaseM.1_engineering_vision_dataset/dxf_renderer.py ]; then echo M1_PRESENT; else echo M1_ABSENT; fi
echo C5
if [ -f /opt/steel-beam-estimation/SteelBeamEstimator/Version10/src/PhaseP2610C5_stratified_vision_semantic_benchmark/claude_call.py ]; then echo C5_PRESENT; else echo C5_ABSENT; fi
echo VISUALS_W8
grep -n 'PhaseW8_production_vision_evidence' /opt/steel-beam-estimation/SteelBeamEstimator/Version10/src/PhaseW6_hybrid_production_authority/visuals.py | head -5 || echo VISUALS_NO_W8
echo LIVE_INVOKE_DETAIL
grep -n 'detail_path' /opt/steel-beam-estimation/SteelBeamEstimator/Version10/src/PhaseW5_production_hybrid_shadow/live_invoke.py | head -8 || echo LIVE_INVOKE_NO_DETAIL
echo GIT
git -C /opt/steel-beam-estimation/SteelBeamEstimator rev-parse HEAD 2>/dev/null || echo NOGIT
echo NGINX
systemctl is-active nginx
echo SMOKE_DXF
ls -ld /home/ubuntu/w3_smoke/smoke/1st\ Set\ Drawings-Galera_OHT\&STP || true
echo W7_CANONICAL
ls -ld /opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260825_113725_9a8d6014 2>/dev/null || echo W7_RUN_ABSENT
