# Builder repo vs private workspace

## Two layers — don't mix them

| | **GitHub `deadlylab/getailab`** | **Your local workspace** |
|---|--------------------------------|--------------------------|
| Purpose | Lab **builder** — engine + forge + example lab | **Live R&D** — operator data you never push |
| Personas | `example_squad.yaml` + squads **you** forge and choose to commit | Rich, loop-tuned squad YAML, custom voices |
| Vault / loops | Empty example vault; testers build their own | `data/labs/<your_lab>/scientists/**/book/`, loop reports, artifacts |
| Boot | `./boot_example.sh` or `./boot_<your_lab>.sh` | `./boot_<your_lab>.sh` for any lab you run locally |
| Business | Public engine + docs | Outreach, investor, competitive intel — **never push** |

The public repo answers: *"How do I run GetAiLab and forge **my** research division?"*

It does **not** ship a mature operational lab's research history, tuned personas, or vault bulk. That kind of output is what you produce **after** you run the builder — it stays on your machine.

## What ships on GitHub

- Engine: `getailab/`, `lab/`, `scientists/base_agent.py`, `scientists/app_oracle.py`, `llm/`
- Lab Forge: `scripts/create_lab.py`, `scripts/persona_builder.py`, `uni_lab.py`
- Starter lab: `personas/example_squad.yaml`, `data/labs/example/`, `boot_example.sh`
- Docs: boot, operation, lab builder, peer-review quickstart

## What stays local (gitignored)

```
personas/<private_lab>_squad.yaml    # operator-tuned squads (not example)
data/labs/<your_lab>/scientists/     # vault bulk
data/labs/<your_lab>/artifacts/
data/labs/<your_lab>/codex/
loop_*_report.md
lab/artifacts/
outreach/
legal/
docs/investor/
docs/COMPETITIVE_*
boot_<private_lab>.sh                # e.g. large local deployments
scientists/app_*.py                  # legacy root-level scientist stubs
*.db
```

The shipped `boot_example.sh` and `personas/example_squad.yaml` **are** tracked — they are the public starter kit.

## First run (clone)

```bash
git clone git@github.com:deadlylab/getailab.git
cd getailab
cp .env.example .env
pip install -r requirements.txt
./boot_example.sh
python3 run_chimera.py --status   # lab + oracle + 2 scientists
```

## Forge your lab

```bash
python3 scripts/create_lab.py
# or
python3 run_chimera.py --forge-lab
```

Then `source .env.<lab_id>` and `./boot_<lab_id>.sh`.

## Accidentally committed private data?

```bash
./scripts/repo_preflight.sh
git rm -r --cached data/labs/<your_lab>/scientists outreach legal  # etc.
git commit -m "chore: remove private workspace files from public repo"
git push
```

Rotate any API keys if `.env` was ever committed.