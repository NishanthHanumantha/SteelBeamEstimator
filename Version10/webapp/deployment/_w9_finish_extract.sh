#!/bin/bash
set -euo pipefail
ROOT=/opt/steel-beam-estimation/SteelBeamEstimator
ENGINE=$ROOT/Version10
TAR=/tmp/w9_runtime.tar.gz
UNPACK=/tmp/w9_unpack
VENV=$ENGINE/webapp/.venv/bin/python

rm -rf "$UNPACK"
mkdir -p "$UNPACK"
tar -xzf "$TAR" -C "$UNPACK"

echo UNPACK_FILES
find "$UNPACK/Version10" -type f | wc -l

# Copy file-by-file so existing Python files are replaced.
while IFS= read -r src; do
  rel="${src#$UNPACK/Version10/}"
  dest="$ENGINE/$rel"
  mkdir -p "$(dirname "$dest")"
  cp -f "$src" "$dest"
done < <(find "$UNPACK/Version10" -type f)

echo APP
grep -n 'APP_RELEASE' "$ENGINE/webapp/config.py" | head -2
echo VISUALS
grep -n 'PhaseW8_production_vision_evidence' "$ENGINE/src/PhaseW6_hybrid_production_authority/visuals.py" | head -3
echo LIVE
grep -n 'detail_path' "$ENGINE/src/PhaseW5_production_hybrid_shadow/live_invoke.py" | head -5
echo C1_INIT
head -2 "$ENGINE/src/PhaseP2610C1C2_evidence_inventory_candidate_selection/__init__.py"
echo C3_INIT
head -2 "$ENGINE/src/PhaseP2610C3_visual_completeness_claude_shadow/__init__.py"

$VENV -m compileall -q \
  "$ENGINE/src/PhaseW8_production_vision_evidence" \
  "$ENGINE/src/PhaseW6_hybrid_production_authority" \
  "$ENGINE/src/PhaseW5_production_hybrid_shadow" \
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
print("ENSURE", ensure_visuals.__module__)
print("LIVE_ARGS", call_shadow_beam.__code__.co_varnames[:12])
PY

sudo cp "$ENGINE/webapp/deployment/steel-beam-estimator-v10.service" /etc/systemd/system/steel-beam-estimator-v10.service
sudo systemctl daemon-reload
sudo systemctl restart steel-beam-estimator-v10.service
sleep 5
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
