# GetAiLab Live — Project Chimera

[![CI](https://github.com/deadlylab/getailab/actions/workflows/ci.yml/badge.svg)](https://github.com/deadlylab/getailab/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)

**Official build.** This directory (`getailab_live`) is the working lab, the git source, and what testers receive.

GetAiLab is a **self-hosted research operating system**: eleven specialist scientists, one Oracle, structured dialectic loops, sandbox experiments, and a checksum-signed vault trail. Not a chatbot — a method.

**Status (8 July 2026):** Working product. Full squad operational. Loops 29–33 complete on `minimax-m2.5:cloud`; graceful LLM degradation proven (Loop 34, credits exhausted).

---

## Clone from GitHub (testers)

```bash
git clone git@github.com:deadlylab/getailab.git
cd getailab
cp .env.example .env          # set LLM_MODEL=minimax-m2.5:cloud
pip install -r requirements.txt
./boot_chimera.sh
./doctor.sh
```

Publish or invite collaborators: [`GITHUB_SETUP.md`](GITHUB_SETUP.md)  
Repo quality gate: [`docs/REPOSITORY_CHECKLIST.md`](docs/REPOSITORY_CHECKLIST.md)  
Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## What runs today

| Layer | Status |
|-------|--------|
| Full dialectic loop (hypothesis → implement → execute → synthesize → directions) | ✅ |
| 11 scientists + Oracle + lab sandbox | ✅ 13/13 when booted |
| Per-scientist books + skills retrieval in loops | ✅ |
| Literature search (PubMed / arXiv / Semantic Scholar) | ✅ Auto at hypothesis |
| Council chat (real LLM) | ✅ |
| Sauron vision + web reader | ✅ |
| Merkle vault + integrity verify + optional Ed25519 signing | ✅ |
| Job tickets (per-phase provenance) | ✅ |
| Adaptive learner (Gabby) | ✅ Post-loop + dashboard |
| Collaborative review script | ✅ Built (`scripts/collaborative_review.py`) |
| LLM tool-artifact sanitizer | ✅ |
| Graceful degradation (503 when LLM unavailable) | ✅ |
| `doctor.sh` one-command health check | ✅ |
| Docker full squad | ✅ `./docker_chimera.sh squad` |

**Model stack (locked for loops):** `minimax-m2.5:cloud` via Ollama. Do **not** use m3 for loops — Loop 28 produced tool-call garbage in hypotheses.

**Personas:** `personas/chimera_squad.yaml` v1.4 (collaboration pass). Squad includes **Tesla** (port 5030). Fixed Chimera division — personalities unchanged in structure.

---

## Quick start (local checkout)

```bash
cd getailab_live   # or cloned getailab/
cp .env.example .env          # set LLM_MODEL=minimax-m2.5:cloud
pip install -r requirements.txt
./boot_chimera.sh               # native — full squad in background
```

Another terminal:

```bash
./doctor.sh                     # stack + Ollama + full squad status
python3 run_chimera.py --status # 13/13: lab, oracle, 11 scientists
```

Dashboard: **http://localhost:5035**

Run a loop:

```bash
python3 run_chimera.py --problem "Your research question here"
# or interactive: python3 run_chimera.py
# or council chat: python3 run_chimera.py --chat
```

Peer reviewers: start at [`docs/peer-review/QUICKSTART_15MIN.md`](docs/peer-review/QUICKSTART_15MIN.md).

---

## Research arc (live evidence)

Recent coherent κ_c / Orch-OR thread (loops 24–33):

| Loop | Status | Notes |
|------|--------|-------|
| 24–27 | ✅ Complete | κ_c, anesthetics, complementarity |
| 28 | ❌ Abandoned | m3 tool-call corruption |
| 29–33 | ✅ Complete | κ_c resonance → THz dielectric → Frohlich → Orch-OR detection → Q≈0 regime |
| 34 | ⚠️ Partial | Credits exhausted; Albert hypothesis only; graceful 503s |

Flagship falsification story: **Loop 29** (Oracle rejects demonstratable κ_c resonance). Showcase: [`examples/loop_23_showcase/`](examples/loop_23_showcase/) and Loop 29 for peer review.

---

## Architecture

```
Problem → Hypothesis (×11) → Implement → Sandbox execute → Oracle synthesize → Researcher picks next direction
```

| Component | Location |
|-----------|----------|
| CLI / Commander | `run_chimera.py` |
| Lab sandbox + dashboard | `lab/app_lab.py` (:5035) |
| Oracle synthesis | `scientists/app_oracle.py` (:5024) |
| Scientist agents | `scientists/app_*.py` (:5025–5040) |
| Personas | `personas/chimera_squad.yaml` + `personas/loader.py` |
| Library vault | `data/labs/chimera/` |
| Loop reports | `loop_*_report.md` (root) |
| Artifacts | `lab/artifacts/{loop_id}/` |

Ports: see [`docs/BOOT_MANUAL.md`](docs/BOOT_MANUAL.md).

---

## Documentation map

| Doc | Purpose |
|-----|---------|
| [`docs/BOOT_MANUAL.md`](docs/BOOT_MANUAL.md) | Boot, stop, troubleshoot |
| [`docs/OPERATION_MANUAL.md`](docs/OPERATION_MANUAL.md) | Runtime architecture + loop flow |
| [`docs/CAPABILITIES_AND_USE_CASES.md`](docs/CAPABILITIES_AND_USE_CASES.md) | What it does + positioning |
| [`docs/COMPETITIVE_AUDIT_JULY_2026.md`](docs/COMPETITIVE_AUDIT_JULY_2026.md) | Field comparison + gaps |
| [`docs/PREPARATION_STRUCTURE.md`](docs/PREPARATION_STRUCTURE.md) | Peer review / pilot / evidence pack layout |
| [`docs/peer-review/`](docs/peer-review/) | Evaluator quickstart + rubric |
| [`docs/LAB_BUILDER.md`](docs/LAB_BUILDER.md) | Forge custom research labs |
| [`docs/ROLLOUT_FORECAST.md`](docs/ROLLOUT_FORECAST.md) | Staged rollout |

---

## Scope

**In:** Chimera fixed squad, 6-phase loops, sandbox + artifacts, tickets, GetAiLabLibrary provenance, self-host, file/SQLite only.

**Out (for this build):** Postgres, unrelated side projects, fake verification scripts. Real loops + real outputs = proof.

**Lab Forge:** Generate custom research divisions from the Chimera blueprint — [`docs/LAB_BUILDER.md`](docs/LAB_BUILDER.md)

```bash
python3 run_chimera.py --forge-lab      # wizard
python3 run_chimera.py --list-labs      # chimera + forged labs
```

**Next:** Distil Loop 29 case study; golden-loop eval harness; Docker profile per forged lab.

---

Copyright (c) 2025–2026 CryptO'Brien Pty Ltd. Rebuilt clean in `getailab_live`.