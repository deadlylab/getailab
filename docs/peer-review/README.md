# Peer Review Pack

**For:** Researchers and technical evaluators of the **GetAiLab lab builder**.  
**Updated:** 8 July 2026

## Start here

1. [`QUICKSTART_15MIN.md`](QUICKSTART_15MIN.md) — boot example lab, run a loop, read the report
2. [`HOW_TO_EVALUATE.md`](HOW_TO_EVALUATE.md) — what makes this different from chatbots
3. [`EVALUATION_RUBRIC.md`](EVALUATION_RUBRIC.md) — structured 1–5 scoring
4. [`FAQ.md`](FAQ.md) — privacy, models, credits, degraded mode
5. [`../BUILDER_REPO.md`](../BUILDER_REPO.md) — what ships on GitHub vs private workspace

## What you're evaluating

- **Engine:** dialectic loop runner, sandbox, Oracle synthesis, tickets, vault
- **Lab Forge:** `scripts/create_lab.py` — can you stand up *your* division?
- **Example lab:** 2 scientists — proof of flow, not a mature operational vault

## Current build facts

- **Example boot:** `./boot_example.sh` → Oracle :5124, Lab/Dashboard :5135
- **Loop model:** `minimax-m2.5:cloud` via Ollama (set in `.env`)
- **Health:** `./doctor.sh` or `python3 run_chimera.py --status`
- **Forge:** `python3 scripts/create_lab.py` for a custom squad

GetAiLab loop reports and vault bulk are **not** in the public repo — they are private R&D evidence.