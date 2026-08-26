#!/bin/bash
set -euo pipefail
ROOT=/opt/steel-beam-estimation/SteelBeamEstimator
ENGINE=$ROOT/Version10
BACKUP=/opt/steel-beam-estimation/backups/w9_predeploy_$(date -u +%Y%m%dT%H%M%SZ)
TAR=/tmp/w9_runtime.tar.gz
VENV=$ENGINE/webapp/.venv/bin/python

if [ ! -f "$TAR" ]; then
  echo "MISSING_TAR $TAR"
  exit 2
fi

mkdir -p "$BACKUP/files"
cp /etc/systemd/system/steel-beam-estimator-v10.service "$BACKUP/steel-beam-estimator-v10.service"
sudo grep -E '^[A-Z_]+=' /etc/steel-beam-estimator-v10.env | cut -d= -f1 > "$BACKUP/env_names.txt"
sudo grep -E '^HYBRID_MODE=' /etc/steel-beam-estimator-v10.env > "$BACKUP/hybrid_mode.txt"
echo "ANTHROPIC=$($VENV -c 'import anthropic; print(anthropic.__version__)')" > "$BACKUP/anthropic_version.txt"
curl -sS --max-time 10 http://127.0.0.1:8001/health > "$BACKUP/health_before.json" || true

while IFS= read -r member; do
  case "$member" in
    */) continue ;;
  esac
  rel="${member#Version10/}"
  src="$ENGINE/$rel"
  if [ -f "$src" ]; then
    mkdir -p "$BACKUP/files/$(dirname "$rel")"
    cp -a "$src" "$BACKUP/files/$rel"
  fi
done < <(tar -tzf "$TAR")

echo BACKUP="$BACKUP"
tar -xzf "$TAR" -C "$ROOT"

$VENV -m compileall -q \
  "$ENGINE/src/PhaseW8_production_vision_evidence" \
  "$ENGINE/src/PhaseW6_hybrid_production_authority" \
  "$ENGINE/src/PhaseW5_production_hybrid_shadow" \
  "$ENGINE/src/PhaseP2610A_beam_region_crop_audit" \
  "$ENGINE/src/PhaseP2610B_adaptive_beam_detail_crop" \
  "$ENGINE/src/PhaseP2610B2_render_quality_directional_recovery" \
  "$ENGINE/src/PhaseP2610C1C2_evidence_inventory_candidate_selection" \
  "$ENGINE/src/PhaseP2610C3_visual_completeness_claude_shadow/config.py" \
  "$ENGINE/src/PhaseP2610C3_visual_completeness_claude_shadow/evidence_model.py" \
  "$ENGINE/src/PhaseP2610C3_visual_completeness_claude_shadow/target_anchor_validator.py" \
  "$ENGINE/src/PhaseP2610C3_visual_completeness_claude_shadow/visual_completeness_gate.py" \
  "$ENGINE/webapp/config.py" \
  "$ENGINE/webapp/routes.py"

cd "$ENGINE"
$VENV - <<'PY'
import sys
sys.path.insert(0, "src")
from PhaseW8_production_vision_evidence.package import prepare_production_evidence
from PhaseW6_hybrid_production_authority.visuals import ensure_visuals
from PhaseW5_production_hybrid_shadow.live_invoke import call_shadow_beam
from PhaseP2610C1C2_evidence_inventory_candidate_selection.selector import select_for_type
from PhaseP2610C3_visual_completeness_claude_shadow.visual_completeness_gate import evaluate_visual_completeness
print("IMPORT_OK")
print("HAS_PREPARE", callable(prepare_production_evidence))
print("HAS_ENSURE", callable(ensure_visuals))
print("HAS_LIVE", callable(call_shadow_beam))
print("HAS_SELECT", callable(select_for_type))
print("HAS_GATE", callable(evaluate_visual_completeness))
PY

sudo cp "$ENGINE/webapp/deployment/steel-beam-estimator-v10.service" /etc/systemd/system/steel-beam-estimator-v10.service
sudo systemctl daemon-reload
sudo systemctl restart steel-beam-estimator-v10.service
sleep 4
echo UNIT="$(systemctl is-active steel-beam-estimator-v10.service)"
echo WORKERS
ps -o pid=,cmd= -C gunicorn || true
echo HEALTH
curl -sS --max-time 10 http://127.0.0.1:8001/health
echo
echo ANTHROPIC
$VENV -c 'import anthropic; print(anthropic.__version__)'
echo MODELINE
sudo grep -E '^HYBRID_MODE=' /etc/steel-beam-estimator-v10.env
echo KEYSTATUS
if sudo grep -q '^ANTHROPIC_API_KEY=.\+' /etc/steel-beam-estimator-v10.env; then echo PRESENT; else echo ABSENT; fi
echo W8
ls -ld "$ENGINE/src/PhaseW8_production_vision_evidence"
echo VISUALS
grep -n 'PhaseW8_production_vision_evidence' "$ENGINE/src/PhaseW6_hybrid_production_authority/visuals.py" | head -3
echo LIVE
grep -n 'detail_path' "$ENGINE/src/PhaseW5_production_hybrid_shadow/live_invoke.py" | head -5
