# Evaluation Harness

**Goal:** Know when a change breaks the loop before a tester finds out.  
**Updated:** 8 July 2026

## Planned

- `golden_loops.yaml` — loops 7, 14, 23, **29** as regression references
- `smoke_test.sh` — `doctor.sh` + status 13/13 + optional dry-run review
- `results/` — timestamped outputs

## Manual smoke (until scripted)

```bash
./doctor.sh
python3 run_chimera.py --status   # expect 13/13
python3 scripts/collaborative_review.py --dry-run --text "smoke" -q "ok?"
```

All services should report `healthy` (or lab `active`) before external sends.

## Golden loop candidates

| Loop | Why |
|------|-----|
| 23 | Original flagship — Orch-OR dialectic |
| 29 | κ_c falsification — Oracle rejects mechanism |
| 33 | Q≈0 regime — full arc closure before 34 |