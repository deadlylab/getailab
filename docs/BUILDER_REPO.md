# Builder repo vs private workspace

## Two layers — don't mix them

| | **GitHub `deadlylab/getailab`** | **Your local `getailab_live` workspace** |
|---|--------------------------------|------------------------------------------|
| Purpose | Lab **builder** — engine + forge + example lab | CryptO'Brien **live R&D** — Chimera moat |
| Personas | `example_squad.yaml` + **your** forged squads you choose to commit | `chimera_squad.yaml`, rich prompts, loop-tuned voices |
| Vault / loops | Empty example vault; testers build their own | `data/labs/chimera/scientists/**/book/`, loop reports, artifacts |
| Boot | `./boot_example.sh` or `./boot_<your_lab>.sh` | `./boot_chimera.sh` (local only, gitignored) |
| Business | Public engine + docs | Outreach, investor, competitive intel — **never push** |

The public repo answers: *"How do I run GetAiLab and forge **my** research division?"*  
It does **not** ship Project Chimera's research history, personas, or vault.

## What ships on GitHub

- Engine: `getailab/`, `lab/`, `scientists/base_agent.py`, `scientists/app_oracle.py`, `llm/`
- Lab Forge: `scripts/create_lab.py`, `scripts/persona_builder.py`, `uni_lab.py`
- Starter lab: `personas/example_squad.yaml`, `data/labs/example/`, `boot_example.sh`
- Docs: boot, operation, lab builder, peer-review quickstart

## What stays local (gitignored)

```
personas/chimera_squad.yaml
data/labs/chimera/
chimera/
loop_*_report.md
lab/artifacts/
outreach/
legal/
docs/investor/
docs/COMPETITIVE_*
boot_chimera.sh
scientists/app_albert.py … app_heisenberg.py  # Chimera reference apps
```

## First run (clone)

```bash
git clone git@github.com:deadlylab/getailab.git
cd getailab
cp .env.example .env
pip install -r requirements.txt
./boot_example.sh
python3 run_chimera.py --status
```

## Forge your lab

```bash
python3 scripts/create_lab.py
# or
python3 run_chimera.py --forge-lab
```

Then `source .env.<lab_id>` and `./boot_<lab_id>.sh`.

## Accidentally committed moat?

```bash
./scripts/repo_preflight.sh
git rm -r --cached data/labs/chimera outreach legal  # etc.
git commit -m "chore: remove private workspace files from public repo"
git push
```

Rotate any API keys if `.env` was ever committed.