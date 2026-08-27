#!/bin/bash
curl -sS --max-time 10 http://127.0.0.1:8001/health
echo
echo '---LOG---'
tail -30 /tmp/w13_live_18.log || true
echo '---RUNJSON---'
cat /tmp/w13_live_run.json 2>/dev/null || true
