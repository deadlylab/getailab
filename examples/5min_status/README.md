# 5-minute status check

Verify the example lab is up before a demo or peer-review session.

## Steps

```bash
./boot_example.sh
./doctor.sh
python3 run_chimera.py --status
```

## Pass criteria (example lab)

- **4 services healthy:** `lab` (active), `oracle`, `researcher`, `critic`
- Dashboard loads at **http://localhost:5135**
- Oracle health: `curl -s http://localhost:5124/health`

## If not healthy

```bash
./stop_example.sh
./boot_example.sh
python3 run_chimera.py --status
```

Check `logs/example_*.log` for scientist startup errors. Ensure Ollama or your configured cloud model is reachable per `.env`.