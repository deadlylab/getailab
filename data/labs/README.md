# Lab runtime data (`data/labs/`)

Per-lab vaults live here **on your machine** after you run loops. They are **not** committed to git (see root `.gitignore`).

## What is tracked

| Path | In git? |
|------|---------|
| `*/config/lab.yaml` | ✅ yes — lab ports, scientist map |
| `*/scientists/**/book/` | ❌ no — grows with every loop |
| `*/artifacts/`, `*/merkle/`, `*/keys/` | ❌ no — runtime provenance |

## Fresh clone

1. `cp .env.example .env`
2. `./boot_chimera.sh` — Chimera config is already under `chimera/config/`
3. First loop populates `chimera/scientists/` locally

## Forged labs

`python3 scripts/create_lab.py` writes `data/labs/<your_lab>/config/` — commit **only** the config + `personas/<lab>_squad.yaml`, not the vault bulk.