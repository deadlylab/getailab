# Lab runtime data (`data/labs/`)

Per-lab vaults live here **on your machine** after you run loops. They are **not** committed to git (see root `.gitignore`).

## What is tracked

| Path | In git? |
|------|---------|
| `*/config/lab.yaml` | ✅ yes — lab ports, scientist map |
| `*/scientists/**/book/` | ❌ no — grows with every loop |
| `*/artifacts/`, `*/merkle/`, `*/keys/` | ❌ no — runtime provenance |

## Fresh clone (builder repo)

1. `cp .env.example .env` — default `LAB_ID=example`
2. `./boot_example.sh` — starter lab under `example/config/`
3. First loop populates `example/scientists/` locally
4. Forge yours: `python3 scripts/create_lab.py`

**Chimera** (`data/labs/chimera/`) is a private local reference lab — not published on GitHub. See `docs/BUILDER_REPO.md`.

## Forged labs

`python3 scripts/create_lab.py` writes `data/labs/<your_lab>/config/` — commit **only** the config + `personas/<lab>_squad.yaml`, not the vault bulk.