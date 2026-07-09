# GetAiLab — Lab Builder

[![CI](https://github.com/deadlylab/getailab/actions/workflows/ci.yml/badge.svg)](https://github.com/deadlylab/getailab/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)

**Self-hosted research operating system + lab forge.** Clone this repo, run it on **your** hardware, and build **your own** multi-agent research division.

GetAiLab is a **method**, not a chatbot: hypothesis → implement → execute → synthesize → pick next direction. Each stage is ticketed; artifacts land in your isolated vault.

**Status (8 July 2026):** Engine proven. Example lab + Lab Forge ready for testers.

---

## Your data. Your model. Your choice.

GetAiLab is **local-first and sovereign by design**:

- **Runs on your machine** — lab, oracle, scientists, vault, and loop reports stay under your project directory unless *you* point inference elsewhere.
- **Default: local Ollama** — no vendor account required to boot the example lab. Prompts and artifacts never leave the host if you keep `LLM_PROVIDER=ollama`.
- **Or plug in what you already trust** — OpenAI, Google Gemini, or Anthropic via `.env`. Same engine; you supply the API key and model name. Switch anytime.
- **No baked-in cloud** — this repo does not ship CryptO'Brien API keys or a mandatory SaaS backend. You control cost, retention, and compliance.

That combination matters for research teams, air-gapped labs, and anyone who wants multi-agent rigour **without** handing hypotheses, code, and vault bulk to a black box.

```bash
cp .env.example .env
# Local (default):  LLM_PROVIDER=ollama
# Or your stack:    LLM_PROVIDER=openai | google | anthropic
```

| Provider | Typical use | Data leaves your machine? | Get started (official) |
|----------|-------------|---------------------------|-------------------------|
| **Ollama** (default) | Local or LAN models, air-gap friendly | **No** — inference stays on host | [ollama.com](https://ollama.com/) |
| **OpenAI** | GPT-4o and familiar OpenAI stack | Only prompts you send to the API | [API keys](https://platform.openai.com/api-keys) |
| **Google** | Gemini | Only prompts you send to the API | [AI Studio keys](https://aistudio.google.com/apikey) |
| **Anthropic** | Claude | Only prompts you send to the API | [Console keys](https://console.anthropic.com/settings/keys) |
| **Auto** | Ollama if up, else first cloud key in `.env` | Depends on what connects | — |

Links above go to each vendor's own site — GetAiLab is not affiliated with or endorsed by those providers; you create accounts and accept their terms separately.

Full variable reference: [`.env.example`](.env.example) · peer-review notes: [`docs/peer-review/FAQ.md`](docs/peer-review/FAQ.md)

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

## What's in this repo

The **engine**, a minimal **example lab**, Lab Forge, boot/Docker tooling, and docs. Loop output and forged vaults are generated on **your** disk under `data/labs/<lab_id>/` when you run — not pre-shipped. Maintainer notes: [`docs/BUILDER_REPO.md`](docs/BUILDER_REPO.md).

**Contributing:** [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

Copyright (c) 2025–2026 CryptO'Brien Pty Ltd.