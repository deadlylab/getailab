# GetAiLab Lab Builder (Lab Forge)

**Updated:** 21 July 2026 (ai_dev dial-in adopted into forge defaults)

The Lab Forge generates **new research divisions** from the GetAiLab engine — custom squads, isolated vaults, dedicated ports, boot/run/stop scripts. Forge your own division; the shipped example lab stays minimal.

**Commercial SKUs** default to `getailab-products/<lab_id>/` (`--product`). Founder R&D uses `--private`.

**Dial-in lab:** `ai_dev` is the wind tunnel. Pipe wins (RESULT contract, isolation, anti-circle, Oracle clean next-problems, Chimera-depth YAML structure with ship outcomes) are adopted into `getailab/forge_defaults.py` so **new labs do not go backwards**.

---

## Standing laws every forged lab inherits

| Law | Where |
|-----|--------|
| RESULT PASS/FAIL + `sys.exit(1)` on FAIL | `forge_defaults` research + canvas prompts |
| Import/extend green `product/` — no rewrite thrash | Anti-circle rules in `core_debate_rules` |
| Chimera-depth persona structure (research profile) | `philosophy` + `core_debate_rules` + dense Phase 1/2 prompts + `example_interactions` |
| Oracle: correct loop_id, plain-text next problems, **this lab's** leads only | `research_oracle_prompt` |
| Commander menu after synthesis | `run_<lab>.sh` clears `GETAILAB_LOOP_ONCE` (unless `FORCE_LAB_LOOP_ONCE=1`) |
| Engine isolation | `lab/app_lab.py` per-agent artifact dirs + product on PYTHONPATH |
| Phase-4 menu | `run_lab.py` re-prompts on empty Enter; `/dev/tty` fallback |

**Do not dilute:** Chimera *dialectic heat* (named challenge, rigor, contribution_to_loops) stays. Cosmology is optional per lab agenda — outcomes (ship, falsify, smoke) are not.

---

## uni_lab.py → Lab Forge (merged)

The legacy **Universal Lab Forge** (`development/dcai/labs/uni_lab.py`) built a *forked mini-codebase* in a new directory — duplicate `base_agent`, `app_lab`, Gemini-only stack, fixed ports 5024–5035.

**GetAiLab merged that wizard into GetAiLab** — one repo, shared engine, isolated vaults per lab:

| Old `uni_lab.py` | New Lab Forge |
|------------------|---------------|
| New directory tree | `data/labs/{id}/` + `scientists/forges/{id}/` |
| Embedded `base_agent.py` | Shared `scientists/base_agent.py` |
| `run_canvas.py` | `run_lab.py` + `LAB_ID` |
| Fixed ports (clash risk) | Auto-allocated port blocks |
| Google Gemini only | Ollama / Google / OpenAI via `.env` |

**Compatibility:** `python3 uni_lab.py` in this repo forwards to `scripts/create_lab.py`.

## Quick start

### Interactive wizard

```bash
python3 uni_lab.py                    # legacy name — same wizard
python3 run_lab.py --forge-lab    # Commander menu option 9
python3 scripts/create_lab.py         # direct
```

### Non-interactive (CI / scripting)

```bash
# Commercial product (default destination)
python3 scripts/create_lab.py \
  --lab-id my_product \
  --display-name "My Product Lab" \
  --agenda "…" \
  --profile research \
  --product \
  --non-interactive \
  --scientists-json '{"alpha":{"role":"Lead","persona":"domain focus"},"beta":{"role":"Critic","persona":"stress-test claims"}}'

# Founder R&D only
python3 scripts/create_lab.py --lab-id toy_rd --private --profile research --non-interactive \
  --scientists-json '{"a":{"role":"A","persona":"x"},"b":{"role":"B","persona":"y"}}'
```

### List all labs

```bash
python3 run_lab.py --list-labs
python3 scripts/create_lab.py --list-labs
```

---

## What gets created

| Artifact | Purpose |
|----------|---------|
| `personas/{lab_id}_squad.yaml` | Squad YAML (or symlink into products/private) |
| `data/labs/{lab_id}/` | Vault (or symlink) + `config/lab.yaml` |
| `scientists/forges/{lab_id}/app_*.py` | Thin scientist wrappers |
| `boot_{lab_id}.sh` · `run_{lab_id}.sh` · `stop_{lab_id}.sh` | Lifecycle + identity wrapper |
| `.env.{lab_id}` | Ports / LAB_ID (example lab → `.env.example_lab`) |
| `--product` pack skeleton | `getailab-products/{lab_id}/` PRODUCT.yaml + vault + personas |

Ports auto-allocate in free blocks (5124+) — avoid clashing with example/chimera.

---

## Build profiles

| Profile | Use |
|---------|-----|
| **research** | Full GetAiLab stack — vault, books, tickets, **Chimera-depth YAML** + outcome laws (`forge_defaults`) |
| **canvas** | Thin personas, fast custom squad — still gets RESULT + anti-rewrite minimums |

Large operational deployments may hand-author `personas/<lab_id>_squad.yaml` (e.g. `ai_dev` v3, Chimera private) after forge — then keep dial-in upgrades in the hand YAML so the lab does not regress.

**Hand-authored reference labs (do not overwrite lightly):**
- Chimera / chimera_clone — full dialectic cosmology + heat
- ai_dev — outcome dial-in (personas v3.0 ship bar)

---

## forge_defaults.py

Shared standing orders for generated squads:

```text
getailab/forge_defaults.py
  OUTCOME_PHILOSOPHY
  CORE_DEBATE_RULES
  research_system_prompt / research_oracle_prompt
  canvas_system_prompt / canvas_oracle_prompt
  enrich_squad_yaml_meta  → philosophy + core_debate_rules on research YAML
```

When you tighten the machine on `ai_dev`, **port the win here** so every next lab inherits it.

---

## Running a forged lab

```bash
./boot_<lab_id>.sh
./run_<lab_id>.sh --status
./run_<lab_id>.sh --problem "Your domain-specific question"
./stop_<lab_id>.sh
```

**Critical:** use the **`run_<lab_id>.sh` wrapper** so a root `.env` pin (e.g. `LAB_ID=chimera`) cannot steal the loop. Dashboard password gates HTML only; `/execute` and `/literature` stay open for loops.

Shutdown:

```bash
./stop_<lab_id>.sh
```

---

## Running multiple labs

Labs use **different port blocks** — the example lab and a forged lab can run simultaneously.

| Lab | Oracle | Lab sandbox |
|-----|--------|-------------|
| example | 5124 | 5135 |
| my_lab (forged) | 5144 | 5155 |
| another_lab | 5164 | 5175 |

Do **not** run two labs on the same ports. Always `./stop_<old>.sh` before reusing a port block if unsure.

---

## Isolation guarantees (8 Jul 2026 fixes)

- Each lab has its own `data/labs/{lab_id}/` vault
- Each lab has its own `data/labs/<lab_id>/agora.db` loop database
- Library backfill reads **only that lab's** loop DB — dialectic loops never leak into forged labs
- Scientist names can repeat across labs (e.g. `tesla` in the example lab and `rf_research`) — books are isolated by `lab_id`

---

Remove a test lab: delete `data/labs/{id}/`, `personas/{id}_squad.yaml`, `scientists/forges/{id}/`, `boot_{id}.sh`, `stop_{id}.sh`, `.env.{id}`.

---

## Commander integration

- Menu **9** — Forge new lab (wizard)
- `--list-labs` — show all registered labs
- Welcome screen lists forged labs when present
- Active lab shown when `LAB_ID` ≠ example

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Forged scientist shows the example lab book pages | Vault contamination from old backfill — wipe `data/labs/{id}/scientists/*/book/pages` and restart |
| `--status` shows wrong squad | Source `.env.{lab_id}` or export `LAB_ID` |
| Port in use | `./stop_{lab_id}.sh` or `ss -tlnp \| grep :51` |
| `example` rejected as lab ID | Sacred reference — pick another ID |

---

## Next (roadmap)

- [ ] Clone-from-the example lab template (pre-fill squad structure, empty books)
- [ ] Lab switcher in Commander (set env without manual export)
- [ ] Docker profile per forged lab
- [ ] Generator tests in `evals/smoke_test.sh`

*GetAiLab Live · Lab Forge · CryptO'Brien Pty Ltd*