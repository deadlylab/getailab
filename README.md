# GetAiLab — Lab Builder

[![CI](https://github.com/deadlylab/getailab/actions/workflows/ci.yml/badge.svg)](https://github.com/deadlylab/getailab/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)

**Self-hosted research operating system + lab forge.** Clone this repo to run the engine and build **your own** multi-agent research division.

GetAiLab is a **method**, not a chatbot: hypothesis → implement → execute → synthesize → pick next direction. Each stage is ticketed; artifacts land in your isolated vault.

> **What ships here:** the **engine**, a minimal **example lab**, and the **Lab Forge** so you can spin up custom squads. A mature operational deployment might accumulate thousands of loop reports and vault pages locally — that output is yours, not part of this builder repo. See [`docs/BUILDER_REPO.md`](docs/BUILDER_REPO.md).

**Status (8 July 2026):** Engine proven. Example lab + Lab Forge ready for testers.

---

## Clone & run (example lab)

```bash
git clone git@github.com:deadlylab/getailab.git
cd getailab
cp .env.example .env
pip install -r requirements.txt
./boot_example.sh
./doctor.sh
python3 run_chimera.py --status   # expect lab + oracle + 2 scientists
```

Dashboard: **http://localhost:5135**

**Docker:** `./docker.sh up` → same ports, full example lab in containers.

---

## Forge your own lab

```bash
python3 scripts/create_lab.py          # interactive wizard
python3 run_chimera.py --forge-lab     # Commander menu
python3 scripts/persona_builder.py     # LLM-assisted persona research
```

Creates: `personas/<lab>_squad.yaml`, `data/labs/<lab>/config/`, `scientists/forges/<lab>/`, `boot_<lab>.sh`, `.env.<lab>`.

Full guide: [`docs/LAB_BUILDER.md`](docs/LAB_BUILDER.md)

---

## What runs today

| Layer | Status |
|-------|--------|
| Dialectic loop (hypothesis → implement → execute → synthesize → direction) | ✅ |
| Lab Forge — custom squads + isolated vaults | ✅ |
| Example lab (2 scientists + Oracle) | ✅ shipped |
| Sandbox execute + artifacts | ✅ |
| Per-stage job tickets | ✅ |
| GetAiLabLibrary vault + integrity verify | ✅ |
| Literature search + Sauron vision | ✅ |
| Adaptive learner (dashboard) | ✅ |
| `doctor.sh` + `evals/smoke_test.sh` | ✅ |

---

## Dialectic loop (accurate)

```
Intake → Hypothesis (×N) → Implement → Execute → Synthesize → [Archive] → Direction picker
```

CLI shows **four headers** (implement + execute share Phase 2). Details: [`docs/OPERATION_MANUAL.md`](docs/OPERATION_MANUAL.md) §1.

---

## Architecture

| Component | Location |
|-----------|----------|
| CLI / Commander | `run_chimera.py` |
| Lab sandbox + dashboard | `lab/app_lab.py` |
| Oracle | `scientists/app_oracle.py` |
| Forged scientists | `scientists/forges/<lab_id>/app_*.py` |
| Personas | `personas/<lab_id>_squad.yaml` |
| Lab config | `data/labs/<lab_id>/config/lab.yaml` |
| Engine | `getailab/` |

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/BUILDER_REPO.md`](docs/BUILDER_REPO.md) | What ships on GitHub vs stays local |
| [`docs/LAB_BUILDER.md`](docs/LAB_BUILDER.md) | Forge custom labs |
| [`docs/BOOT_MANUAL.md`](docs/BOOT_MANUAL.md) | Boot, stop, troubleshoot |
| [`docs/OPERATION_MANUAL.md`](docs/OPERATION_MANUAL.md) | Loop flow + runtime |
| [`docs/peer-review/QUICKSTART_15MIN.md`](docs/peer-review/QUICKSTART_15MIN.md) | Evaluator path |
| [`GITHUB_SETUP.md`](GITHUB_SETUP.md) | Publish / push workflow |
| [`docs/REPOSITORY_CHECKLIST.md`](docs/REPOSITORY_CHECKLIST.md) | Pre-push gate |

---

## Scope

**In (public repo):** Engine, Lab Forge, example lab, boot tooling, self-host, SQLite/file vaults.

**Out (your local workspace):** Operator-tuned squad YAML, loop reports, outreach, investor/competitive docs, large vault bulk.

**Contributing:** [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

Copyright (c) 2025–2026 CryptO'Brien Pty Ltd.