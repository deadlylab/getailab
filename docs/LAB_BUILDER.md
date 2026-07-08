# GetAiLab Lab Builder (Lab Forge)

**Updated:** 8 July 2026

The Lab Forge generates **new research divisions** from the Chimera blueprint — custom squads, isolated vaults, dedicated ports, boot/stop scripts. Chimera stays pristine as the reference lab.

---

## uni_lab.py → Lab Forge (merged)

The legacy **Universal Lab Forge** (`development/dcai/labs/uni_lab.py`) built a *forked mini-codebase* in a new directory — duplicate `base_agent`, `app_lab`, Gemini-only stack, fixed ports 5024–5035.

**GetAiLab merged that wizard into Chimera** — one repo, shared engine, isolated vaults per lab:

| Old `uni_lab.py` | New Lab Forge |
|------------------|---------------|
| New directory tree | `data/labs/{id}/` + `scientists/forges/{id}/` |
| Embedded `base_agent.py` | Shared `scientists/base_agent.py` |
| `run_canvas.py` | `run_chimera.py` + `LAB_ID` |
| Fixed ports (clash risk) | Auto-allocated port blocks |
| Google Gemini only | Ollama / Google / OpenAI via `.env` |

**Compatibility:** `python3 uni_lab.py` in this repo forwards to `scripts/create_lab.py`.

## Quick start

### Interactive wizard

```bash
python3 uni_lab.py                    # legacy name — same wizard
python3 run_chimera.py --forge-lab    # Commander menu option 9
python3 scripts/create_lab.py         # direct
```

### Non-interactive (CI / scripting)

```bash
python3 scripts/create_lab.py \
  --lab-id cyber_lab \
  --display-name "Cyber Threat Research" \
  --agenda "RF anomaly detection and wireless security" \
  --profile research \
  --non-interactive \
  --scientists-json '{"tesla":{"role":"RF Analyst","persona":"spectrum analysis"},"shannon":{"role":"Info Theory","persona":"channel capacity"}}'
```

### List all labs

```bash
python3 run_chimera.py --list-labs
python3 scripts/create_lab.py --list-labs
```

---

## What gets created

| Artifact | Purpose |
|----------|---------|
| `personas/{lab_id}_squad.yaml` | Squad definitions + system prompts |
| `data/labs/{lab_id}/config/lab.yaml` | Ports, scientist apps, metadata |
| `data/labs/{lab_id}/scientists/*/book/` | **Empty** per-scientist vault (isolated) |
| `scientists/forges/{lab_id}/app_*.py` | Thin scientist wrappers (load personas + base_agent) |
| `boot_{lab_id}.sh` | Start lab + Oracle + squad |
| `stop_{lab_id}.sh` | Stop this lab only |
| `.env.{lab_id}` | `LAB_ID`, ports, URLs — source before `run_chimera.py` |

Ports auto-allocate in blocks (5124+) — **no collision** with Chimera (5024–5040).

---

## Build profiles

| Profile | Use |
|---------|-----|
| **research** | Full GetAiLab stack — vault, books, tickets, rich prompts |
| **canvas** | Thin personas, fast custom squad (uni_lab style) |

Chimera uses `reference` profile (fixed `personas/chimera_squad.yaml`).

---

## Running a forged lab

```bash
./boot_rf_research.sh
source .env.rf_research
python3 run_chimera.py --status    # 4/4: lab + oracle + N scientists
python3 run_chimera.py --problem "Your domain-specific question"
```

**Critical:** set `LAB_ID` and `PERSONAS_YAML` (or source `.env.{lab_id}`) so Commander, library, and tickets target the right vault.

```bash
export LAB_ID=rf_research
export PERSONAS_YAML=personas/rf_research_squad.yaml
export ORACLE_URL=http://localhost:5124
export LAB_URL=http://localhost:5135
```

Shutdown:

```bash
./stop_rf_research.sh
```

---

## Running multiple labs

Labs use **different port blocks** — Chimera and `rf_research` can run simultaneously.

| Lab | Oracle | Lab sandbox |
|-----|--------|-------------|
| chimera | 5024 | 5035 |
| rf_research | 5124 | 5135 |
| test_ops_lab | 5144 | 5155 |

Do **not** run two labs on the same ports. Always `./stop_<old>.sh` before reusing a port block if unsure.

---

## Isolation guarantees (8 Jul 2026 fixes)

- Each lab has its own `data/labs/{lab_id}/` vault
- Each lab has its own `agora.db` (forged) or `chimera_lab.db` (reference only)
- Library backfill reads **only that lab's** loop DB — Chimera loops never leak into forged labs
- Scientist names can repeat across labs (e.g. `tesla` in Chimera and `rf_research`) — books are isolated by `lab_id`

---

## Existing forged labs

| Lab ID | Display name | Scientists | Boot |
|--------|--------------|------------|------|
| `rf_research` | RF Threat Lab | tesla, shannon | `./boot_rf_research.sh` |

Remove a test lab: delete `data/labs/{id}/`, `personas/{id}_squad.yaml`, `scientists/forges/{id}/`, `boot_{id}.sh`, `stop_{id}.sh`, `.env.{id}`.

---

## Commander integration

- Menu **9** — Forge new lab (wizard)
- `--list-labs` — show all registered labs
- Welcome screen lists forged labs when present
- Active lab shown when `LAB_ID` ≠ chimera

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Forged scientist shows Chimera book pages | Vault contamination from old backfill — wipe `data/labs/{id}/scientists/*/book/pages` and restart |
| `--status` shows wrong squad | Source `.env.{lab_id}` or export `LAB_ID` |
| Port in use | `./stop_{lab_id}.sh` or `ss -tlnp \| grep :51` |
| `chimera` rejected as lab ID | Sacred reference — pick another ID |

---

## Next (roadmap)

- [ ] Clone-from-Chimera template (pre-fill squad structure, empty books)
- [ ] Lab switcher in Commander (set env without manual export)
- [ ] Docker profile per forged lab
- [ ] Generator tests in `evals/smoke_test.sh`

*GetAiLab Live · Lab Forge · CryptO'Brien Pty Ltd*