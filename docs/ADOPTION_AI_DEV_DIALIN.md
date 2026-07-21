# Adopting ai_dev dial-in into the main brains (Lab Forge)

**Date:** 2026-07-21  
**Goal:** Do not go backwards. `ai_dev` is the wind tunnel; the product is the **lab builder machine**.

## Principles

1. **Bones solid** — forge + vault + dialectic loop stay.
2. **Screws from ai_dev** — RESULT, isolation, Oracle hygiene, menu, package SoR — become **forge defaults**.
3. **Chimera dialectic retained** — heat, named challenge, dense persona structure (`philosophy`, `core_debate_rules`, `contribution_to_loops`, `example_interactions`). Cosmology is optional per lab; **rigor is not**.
4. **Hand-authored labs** (Chimera, ai_dev v3) remain the gold references; forge emits the same *laws* for every new lab.

## Pipe wins adopted into engine (shared runtime)

| Win | Module |
|-----|--------|
| Per-agent artifact dirs + product PYTHONPATH | `lab/app_lab.py` `/execute` |
| Oracle: squad leads from PERSONAS_YAML, clean problem text, loop_id | `scientists/app_oracle.py` |
| Phase-4: empty Enter re-prompts; `/dev/tty`; clean next problem | `run_lab.py` |
| RESULT / import cheatsheet | `scientists/base_agent.py` |
| Outcome standing orders for **new** squads | `getailab/forge_defaults.py` + `scripts/create_lab.py` |
| run wrapper clears LOOP_ONCE | forged `run_<lab>.sh` template |

## Persona depth

| Lab | Role |
|-----|------|
| Chimera (private YAML) | Full dialectic cosmology + heat |
| ai_dev (`personas/ai_dev_squad.yaml` v3) | Same **detail density**, ship/falsify **outcomes** |
| Forged research labs | `forge_defaults.research_system_prompt` (~3.5k) + `core_debate_rules` |

## Operator rule

When you tighten the machine on `ai_dev`:

1. Fix the **engine** (shared runtime).
2. Port standing orders into **`forge_defaults.py`**.
3. Update hand YAML only for reference labs that must stay ahead of the forge.

## Verify forge emit

```bash
cd /home/deadly/x/github
python3 -c "from scripts.create_lab import build_squad_yaml; ..."
# or forge a throwaway lab under --engine and inspect personas/<id>_squad.yaml
```

## Do not

- Overwrite Chimera private personas with thin forge templates.
- Ship labs without RESULT contract.
- Let LOOP_ONCE default on for interactive commanders.
