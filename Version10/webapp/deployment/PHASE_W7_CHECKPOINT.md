# PHASE W.7 — CHECKPOINT

Saved: 2026-08-25  
Classification: **W7_PASS_WITH_LIMITATIONS**

## Production state (resumable)

| Item | State |
|------|--------|
| Public URL | http://13.127.104.99/ |
| `/health` | `phase=W.7`, `app_release=W.7`, `status=ok` |
| Hybrid mode | **production** |
| API key | configured (`PRESENT`); file `/etc/steel-beam-estimator-v10.env` mode 600 |
| Stages | `… → R13 → HYBRID → VB1` |
| Gunicorn | `127.0.0.1:8001`, **1 worker**, `steel-beam-estimator-v10` active |
| Nginx | still Version10 `:8001` |
| Old 8.9.x | still on `:8000` |
| Instance | 2 GB, no swap, not resized |
| anthropic | **0.125.0** (must remain `<1`) |

## Canonical go-live run

`20260825_113725_9a8d6014` — First Set, 18/18 Claude, Hybrid 176.5 s, Excel 1432.237 kg, unexplained=0.

## Immediate Hybrid disable

```bash
sudo sed -i 's/^HYBRID_MODE=production$/HYBRID_MODE=off/' /etc/steel-beam-estimator-v10.env
sudo systemctl restart steel-beam-estimator-v10
```

Nginx switch is not required.

## Do not

- Unpin `anthropic` to 1.x
- Rewrite T1 to force OpenCV crops
- Enable `HYBRID_MODE=authoritative`
- Resize the 2 GB instance without a new approval
- Copy workstation `.env` onto the instance
