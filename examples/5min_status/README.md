# 5-Minute Status Demo

**Purpose:** Show a stranger the squad is real infrastructure, not a slide deck.

## Run

```bash
cd getailab_live
./doctor.sh
python3 run_chimera.py --status
```

## Expected output (8 July 2026 build)

- **13/13 healthy:** `lab` (active), `oracle`, and 11 scientists including `tesla`
- Ollama reachable at `http://localhost:11434`
- Scientific stack OK (numpy, pandas, pyarrow, …)
- Each scientist shows `book.pages` ~500+ and `skills` ~350+

## Screenshot checklist

- [ ] `doctor.sh` green checks
- [ ] `--status` JSON showing all scientist names
- [ ] Dashboard http://localhost:5035 loading

## If not 13/13

```bash
./boot_chimera.sh
# wait 10s, re-run doctor.sh
```

See `docs/BOOT_MANUAL.md` for port conflicts.