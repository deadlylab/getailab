# Evidence & Case Studies

**Purpose:** Publishable receipts — not hype, proof.  
**Updated:** 8 July 2026

## Live traction (on disk)

| Asset | Count / status |
|-------|----------------|
| Loop reports (`loop_*_report.md`) | **18** |
| Complete recent arc | Loops **29–33** (κ_c → Orch-OR → Q≈0) |
| Partial / degraded mode | Loop **34** (credits exhausted — clean 503s) |
| Vault page files | **~9,800** in `data/labs/chimera/scientists/*/book/pages/` |
| Sandbox artifacts | **~400** in `lab/artifacts/` |
| Squad | **13/13** when booted (11 scientists + Oracle + lab) |

## Planned evidence (priority order)

| Doc | Source | Status |
|-----|--------|--------|
| `LOOP_29_CASE_STUDY.md` | κ_c falsification — **primary external story** | ⬜ todo |
| `LOOP_23_CASE_STUDY.md` | Orch-OR metabolic cost dialectic | ⬜ todo |
| `GRACEFUL_DEGRADATION_34.md` | Loop 34 partial + 503 log receipt | ⬜ todo |
| `OLLAMA_VS_GOOGLE_COMPARISON.md` | Same problem, two backends | ⬜ scaffold |
| `VALIDATION_SPRINT_01.md` | Literature/data check on Direction #2 | ⬜ todo |
| `VAULT_SNAPSHOT.md` | Integrity verify output + page counts | ⬜ todo |

## Integrity command (vault snapshot)

```bash
python3 -c "from getailab.integrity.verify import full_integrity_report; import json; print(json.dumps(full_integrity_report(), indent=2))"
```

Run after major loops or before sending a peer-review pack.

## Best loops for external citation

1. **Loop 29** — Oracle falsifies κ_c resonance mechanism (~4,282 lines)
2. **Loop 33** — Q≈0 critically damped regime; Oracle → Direction 2 for 34
3. **Loop 23** — Original flagship Orch-OR dialectic (~3,580 lines)
4. **Loop 34** (partial) — Graceful failure when LLM unavailable